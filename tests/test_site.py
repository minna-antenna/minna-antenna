import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_site
import update_news


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'articles', self.root / 'articles')
        shutil.copy(ROOT / 'index.html', self.root / 'index.html')

    def test_new_article_escaped_nested_and_idempotent(self):
        path = self.root / 'articles' / '基礎' / 'new.html'
        path.parent.mkdir()
        path.write_text('<html><head><meta name="description" content="説明 &amp; 内容"><meta property="article:published_time" content="2026-11-06"></head><body><h1>A &amp; B &lt;test&gt;</h1></body></html>')
        build_site.build(self.root)
        first = (self.root / 'index.html').read_bytes()
        self.assertIn(b'A &amp; B &lt;test&gt;', first)
        self.assertIn(b'articles/%E5%9F%BA%E7%A4%8E/new.html', first)
        urls = ET.parse(self.root / 'sitemap.xml').findall('.//{*}loc')
        self.assertEqual(len(urls), 4 + len(list((self.root / 'articles').rglob('*.html'))))
        self.assertIn(build_site.BASE + 'articles/%E5%9F%BA%E7%A4%8E/new.html', [u.text for u in urls])
        build_site.build(self.root)
        self.assertEqual(first, (self.root / 'index.html').read_bytes())

    def test_existing_articles_and_reciprocal_links_survive_build(self):
        names = ('bitcoin-halving.html', 'bitcoin-four-year-cycle.html')
        before = {name: (self.root / 'articles' / name).read_bytes() for name in names}
        build_site.build(self.root)
        index = (self.root / 'index.html').read_text()
        urls = [u.text for u in ET.parse(self.root / 'sitemap.xml').findall('.//{*}loc')]
        for name, other in (names, tuple(reversed(names))):
            content = (self.root / 'articles' / name).read_bytes()
            self.assertEqual(content, before[name])
            self.assertIn(f'href="./{other}"', content.decode())
            self.assertIn(f'href="./articles/{name}"', index)
            self.assertIn(build_site.BASE + 'articles/' + name, urls)

    def test_invalid_article_does_not_change_generated_files(self):
        before = (self.root / 'index.html').read_bytes()
        (self.root / 'articles' / 'bad.html').write_text('<h1>Invalid</h1>')
        with self.assertRaises(ValueError):
            build_site.build(self.root)
        self.assertEqual(before, (self.root / 'index.html').read_bytes())

    def test_marker_error(self):
        (self.root / 'index.html').write_text('<html></html>')
        with self.assertRaises(ValueError):
            build_site.build(self.root)


class NewsTests(unittest.TestCase):
    def test_parse_filter_and_deduplication(self):
        now = dt.datetime(2026, 11, 6, tzinfo=dt.timezone.utc)
        raw = b'<rss><channel><item><title>Example</title><link>https://example.com/a</link><pubDate>Thu, 05 Nov 2026 23:00:00 GMT</pubDate></item><item><title>Bad URL</title><link>javascript:alert(1)</link><pubDate>Thu, 05 Nov 2026 23:00:00 GMT</pubDate></item></channel></rss>'
        items = update_news.parse_rss(raw, 'NHK', 'news', now)
        self.assertEqual(len(items), 1)
        self.assertEqual(len(update_news.build(items + items, now)), 1)
        self.assertEqual(update_news.parse_rss(raw, 'NHK', 'news', now + dt.timedelta(days=4)), [])

    def test_failure_empty_and_partial_keep_previous(self):
        for mode in ('broken', 'empty', 'partial'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / 'news.json'
                old = dict(title='Previous', url='https://example.com/old', feed='NHK総合', source='NHK', category='ニュース', published_at='2026-11-01T00:00:00Z')
                output.write_text(json.dumps(dict(generated_at='previous-time', articles=[old])))
                (root / '0.xml').write_text('invalid' if mode != 'empty' else '<rss><channel/></rss>')
                if mode == 'partial':
                    date = dt.datetime.now(dt.timezone.utc).isoformat()
                    (root / '1.xml').write_text(f'<rss><channel><item><title>New</title><link>https://example.com/new</link><pubDate>{date}</pubDate></item></channel></rss>')
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/update_news.py'), '--fixtures', directory, '--output', str(output)], capture_output=True)
                data = json.loads(output.read_text())
                self.assertIn(old, data['articles'])
                self.assertEqual(result.returncode, 0 if mode == 'partial' else 1)
                if mode != 'partial':
                    self.assertEqual(data['generated_at'], 'previous-time')
                else:
                    self.assertEqual(data['status'], 'partial')
                    self.assertEqual(len(data['articles']), 2)


if __name__ == '__main__':
    unittest.main()
