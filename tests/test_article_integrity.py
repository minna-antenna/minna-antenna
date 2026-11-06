"""Check published content and navigation as the article collection grows."""
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest
from urllib.parse import quote, unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://minna-antenna.github.io/minna-antenna/'


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.ids, self.hrefs, self.meta, self.scripts = [], [], {}, []
        self.canonical = None
        self.h1_count = 0
        self.in_ld = False
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.hrefs.append(attrs['href'])
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'meta':
            self.meta[attrs.get('name', attrs.get('property', ''))] = attrs.get('content', '')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href')
        if tag == 'script' and attrs.get('type') == 'application/ld+json':
            self.in_ld = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_ld = False

    def handle_data(self, data):
        if self.in_ld:
            self.scripts.append(data)


class ArticleIntegrityTests(unittest.TestCase):
    def test_local_links_and_fragments_resolve(self):
        paths = [ROOT / p for p in ('index.html', 'about.html', 'privacy.html', 'contact.html')]
        paths += list((ROOT / 'articles').rglob('*.html'))
        pages = {p.resolve(): Page(p) for p in paths}
        for path, page in pages.items():
            with self.subTest(page=path.name):
                self.assertEqual(len(page.ids), len(set(page.ids)), 'Duplicate HTML id')
                for href in page.hrefs:
                    link = urlsplit(href)
                    if link.scheme or link.netloc:
                        continue
                    target = (path.parent / unquote(link.path)).resolve() if link.path else path
                    if target.is_dir():
                        target = target / 'index.html'
                    self.assertTrue(target.exists(), f'{path.name}: {href}')
                    if link.fragment:
                        destination = pages.get(target) or Page(target)
                        self.assertIn(unquote(link.fragment), destination.ids, f'{path.name}: {href}')

    def test_article_seo_metadata_and_structured_data(self):
        for path in (ROOT / 'articles').rglob('*.html'):
            with self.subTest(page=path.name):
                page = Page(path)
                canonical = BASE + quote(path.relative_to(ROOT).as_posix(), safe='/')
                self.assertEqual(page.h1_count, 1)
                self.assertTrue(page.meta.get('description'))
                self.assertEqual(page.canonical, canonical)
                self.assertEqual(page.meta.get('og:url'), canonical)
                ld = json.loads(''.join(page.scripts))
                self.assertEqual(ld['@type'], 'Article')
                self.assertTrue(ld.get('datePublished'))
                self.assertTrue(ld.get('dateModified'))

    def test_first_four_articles_are_registered_once_and_linked(self):
        names = ('bitcoin-halving.html', 'bitcoin-four-year-cycle.html', 'crypto-eth-sol-xrp-comparison.html', 'bitcoin-vs-stocks-long-term.html')
        index = Page(ROOT / 'index.html')
        urls = [x.text for x in ET.parse(ROOT / 'sitemap.xml').findall('.//{*}loc')]
        self.assertEqual(len(urls), len(set(urls)))
        for name in names:
            with self.subTest(page=name):
                path = ROOT / 'articles' / name
                self.assertTrue(path.exists())
                self.assertEqual(index.hrefs.count('./articles/' + name), 1)
                self.assertEqual(urls.count(BASE + 'articles/' + name), 1)
                page = Page(path)
                for other in names:
                    if other != name:
                        self.assertIn('./' + other, page.hrefs)


if __name__ == '__main__':
    unittest.main()
