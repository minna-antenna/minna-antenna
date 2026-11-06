#!/usr/bin/env python3
"""Build the static article index and sitemap; Python standard library only."""
import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote
import xml.etree.ElementTree as ET

BASE = 'https://minna-antenna.github.io/minna-antenna/'
START, END = '<!-- ARTICLES:START -->', '<!-- ARTICLES:END -->'


class Metadata(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.meta, self.blocks = {}, {'h1': [], 'title': [], 'script': []}
        self.active = None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('name', attrs.get('property', ''))] = attrs.get('content', '')
        if tag in self.blocks and (tag != 'script' or attrs.get('type') == 'application/ld+json'):
            self.active = tag
        if tag == 'br' and self.active:
            self.blocks[self.active].append(' ')

    def handle_endtag(self, tag):
        if tag == self.active:
            self.active = None

    def handle_data(self, data):
        if self.active:
            self.blocks[self.active].append(data)


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def article_metadata(path, root):
    source = path.read_text(encoding='utf-8')
    doc = Metadata(source)
    title = re.sub(r'\s+', ' ', ''.join(doc.blocks['h1'] or doc.blocks['title'])).strip()
    description = doc.meta.get('description', '').strip()
    if not title or not description:
        raise ValueError(f'{path}: h1/title と meta description が必要です')
    published = doc.meta.get('article:published_time', '')
    modified = doc.meta.get('article:modified_time', '')
    # Support the existing Article JSON-LD and visible Japanese publication dates.
    try:
        ld = json.loads(''.join(doc.blocks['script']))
        if isinstance(ld, dict):
            published = published or ld.get('datePublished', '')
            modified = modified or ld.get('dateModified', '')
    except (ValueError, TypeError):
        pass
    if not published:
        match = re.search(r'公開[：:]\s*(\d{4})年(\d{1,2})月(\d{1,2})日', source)
        if match:
            published = '-'.join([match[1], match[2].zfill(2), match[3].zfill(2)])
    if not published:
        raise ValueError(f'{path}: article:published_time に公開日を指定してください')
    published = dt.date.fromisoformat(published[:10]).isoformat()
    if modified:
        modified = dt.date.fromisoformat(modified[:10]).isoformat()
    else:
        # Git timestamps, unlike checkout mtimes, remain stable on each runner.
        result = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', str(path.relative_to(root))], cwd=root, capture_output=True, text=True)
        modified = max(published, result.stdout.strip() or published)
    if modified < published:
        raise ValueError(f'{path}: 更新日は公開日以降にしてください')
    relative = path.relative_to(root).as_posix()
    return dict(title=title, description=description, published=published,
                modified=modified, path=relative, url=BASE + quote(relative, safe='/'))


def build(root):
    root = Path(root).resolve()
    articles = [article_metadata(p, root) for p in sorted((root / 'articles').rglob('*.html'))]
    if not articles:
        raise ValueError('記事が0件です。既存の生成物を維持します')
    articles.sort(key=lambda x: (x['published'], x['path']), reverse=True)
    index = (root / 'index.html').read_text(encoding='utf-8')
    if index.count(START) != 1 or index.count(END) != 1 or index.index(START) > index.index(END):
        raise ValueError('記事一覧の生成マーカーが不正です')
    entries = []
    for article in articles:
        e = {k: html.escape(v, quote=True) for k, v in article.items()}
        entries.append(f'<article class="article-entry"><h3><a href="./{quote(article["path"], safe="/")}">{e["title"]} →</a></h3><p class="muted"><time datetime="{e["published"]}">{e["published"]}</time>公開</p><p>{e["description"]}</p></article>')
    index = index[:index.index(START) + len(START)] + '\n' + '\n'.join(entries) + '\n' + index[index.index(END):]
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', ns)
    sitemap = ET.Element(f'{{{ns}}}urlset')
    pages = [dict(url=BASE)] + [dict(url=BASE + p) for p in ('about.html', 'privacy.html', 'contact.html')] + articles
    for page in pages:
        url = ET.SubElement(sitemap, f'{{{ns}}}url')
        ET.SubElement(url, f'{{{ns}}}loc').text = page['url']
        if page.get('modified'):
            ET.SubElement(url, f'{{{ns}}}lastmod').text = page['modified']
    ET.indent(sitemap, space='  ')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(sitemap, encoding='unicode') + '\n'
    # Finish validation before replacing any generated file.
    atomic_write(root / 'index.html', index)
    atomic_write(root / 'sitemap.xml', xml)
    print(f'Built {len(articles)} articles, {len(pages)} sitemap URLs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        build(args.root)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Build failed: {error}\n')
