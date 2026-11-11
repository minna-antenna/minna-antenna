"""Verify the requested connection loader without adding ad units or settings."""
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_site
SRC='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8155299200535467'
CODE=f'<script async src="{SRC}" crossorigin="anonymous"></script>'

class Scripts(HTMLParser):
    def __init__(self,source):
        super().__init__();self.in_head=False;self.loaders=[];self.ad_units=[];self.feed(source)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='head':self.in_head=True
        if tag=='script' and 'adsbygoogle.js' in a.get('src',''):self.loaders.append((a,self.in_head))
        if tag=='ins':self.ad_units.append(a)
    def handle_endtag(self,tag):
        if tag=='head':self.in_head=False

class VerificationTests(unittest.TestCase):
    def assert_code(self,source):
        doc=Scripts(source);self.assertEqual(len(doc.loaders),1)
        attrs,in_head=doc.loaders[0];self.assertTrue(in_head);self.assertEqual(attrs['src'],SRC)
        self.assertIn('async',attrs);self.assertEqual(attrs['crossorigin'],'anonymous')
        self.assertEqual(doc.ad_units,[])
        self.assertNotIn('enable_page_level_ads',source)
        self.assertNotIn('adsbygoogle.push',source)
        self.assertNotIn('data-ad-slot',source)

    def test_all_content_pages_include_exact_script_once(self):
        pages=[ROOT/name for name in ('index.html','about.html','privacy.html','contact.html')]+list((ROOT/'articles').rglob('*.html'))
        for p in pages:
            with self.subTest(page=p.name):self.assert_code(p.read_text())
        self.assertNotIn('adsbygoogle',(ROOT/'googleb899a57e1737e8bb.html').read_text())

    def test_duplicate_or_wrong_client_loader_is_normalized_inside_head(self):
        wrong=CODE.replace('8155299200535467','0000000000000000').replace('https://','//')
        source='<html><head><title>Keep</title>'+CODE+'</head><body>'+wrong+CODE+'<h1>Keep body</h1></body></html>'
        updated=build_site.ensure_adsense_code(source)
        self.assert_code(updated)
        self.assertIn('<h1>Keep body</h1>',updated)
        self.assertEqual(build_site.ensure_adsense_code(updated),updated)

    def test_new_article_gets_code_and_rebuild_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'articles',root/'articles')
            for name in ('index.html','about.html','privacy.html','contact.html'):shutil.copy(ROOT/name,root/name)
            article=root/'articles/new.html'
            article.write_text('<html><head><meta name="description" content="New"><meta property="article:published_time" content="2026-11-11"></head><body><h1>New</h1></body></html>')
            # Also simulate a missing loader on a fixed page.
            fixed=root/'contact.html';fixed.write_text(fixed.read_text().replace(CODE,''))
            build_site.build(root)
            self.assert_code(article.read_text());self.assert_code(fixed.read_text())
            first={p:p.read_bytes() for p in root.rglob('*.html')}
            build_site.build(root)
            self.assertEqual(first,{p:p.read_bytes() for p in root.rglob('*.html')})

    def test_invalid_head_does_not_partially_rewrite_site(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'articles',root/'articles');shutil.copy(ROOT/'index.html',root/'index.html')
            index=root/'index.html';index.write_text(index.read_text().replace(CODE,''));before=index.read_bytes()
            (root/'articles/new.html').write_text('<h1>New</h1><meta name="description" content="New"><meta property="article:published_time" content="2026-11-11">')
            with self.assertRaises(ValueError):build_site.build(root)
            self.assertEqual(before,index.read_bytes())
            self.assertFalse((root/'sitemap.xml').exists())

    def test_actual_pages_artifact_has_code_and_keeps_rss_unpublished(self):
        workflow=(ROOT/'.github/workflows/pages.yml').read_text()
        block=re.search(r'      - name: Stage public files only\n        run: \|\n(.*?)(?=      - uses:)',workflow,re.S)[1]
        command='\n'.join(line[10:] for line in block.splitlines())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ('index.html','about.html','privacy.html','contact.html','sitemap.xml','robots.txt','googleb899a57e1737e8bb.html'):shutil.copy(ROOT/name,root/name)
            shutil.copytree(ROOT/'articles',root/'articles')
            subprocess.run(['bash','-eu','-c',command],cwd=root,check=True)
            pages=[p for p in (root/'_site').rglob('*.html') if p.name!='googleb899a57e1737e8bb.html']
            self.assertEqual(len(pages),17)
            for p in pages:self.assert_code(p.read_text())
            self.assertFalse((root/'_site/data/news.json').exists())
