"""Canonical domain, build output and deployment configuration regressions."""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_site
import monitor_indexing as monitor

class DomainMigrationTests(unittest.TestCase):
    def test_published_pages_and_sitemap_use_canonical_domain(self):
        paths=[ROOT/p for p in ('index.html','about.html','privacy.html','contact.html')]+list((ROOT/'articles').glob('*.html'))
        for p in paths:
            with self.subTest(page=p.name):
                text=p.read_text()
                self.assertNotIn('minna-antenna.github.io',text)
                self.assertNotIn('/minna-antenna/',text)
                path='' if p.name=='index.html' else p.relative_to(ROOT).as_posix()
                self.assertIn('href="https://topic-kichi.com/'+path+'"',text)
        locations=[n.text for n in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')]
        self.assertEqual(set(locations),{'https://topic-kichi.com/'+('' if p.name=='index.html' else p.relative_to(ROOT).as_posix()) for p in paths})
        self.assertEqual(len(locations),len(set(locations)))
        self.assertEqual(build_site.BASE,'https://topic-kichi.com/')
        robots=(ROOT/'robots.txt').read_text()
        self.assertIn('Allow: /\n',robots)
        self.assertIn('Sitemap: https://topic-kichi.com/sitemap.xml',robots)

    def test_inspection_monitor_never_selects_legacy_or_cross_domain_articles(self):
        def xml(url):return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+url+'</loc></url></urlset>').encode()
        self.assertEqual(monitor.article_urls(xml('https://topic-kichi.com/articles/test.html')),['https://topic-kichi.com/articles/test.html'])
        for url in ('https://minna-antenna.github.io/minna-antenna/articles/test.html','https://topic-kichi.com.evil.example/articles/test.html'):
            with self.assertRaises(monitor.MonitorError):monitor.article_urls(xml(url))
        report,code=monitor.monitor({'GSC_SITE_URL':'https://minna-antenna.github.io/minna-antenna/'})
        self.assertEqual(code,2)
        self.assertEqual(report['error'],'unsupported_property')

    def test_deployment_guard_checks_existing_domain_without_mutation(self):
        text=(ROOT/'.github/workflows/pages.yml').read_text()
        block=re.search(r'      - name: Require GitHub Actions and the configured custom domain\n        env:.*?        run: \|\n(.*?)(?=      - uses:)',text,re.S)[1]
        command='\n'.join(line[10:] for line in block.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'gh'
            p.write_text('#!/usr/bin/env python3\nimport os,sys\nprint(os.environ["TEST_BUILD_TYPE"] if ".build_type" in sys.argv else os.environ["TEST_DOMAIN"])\n')
            p.chmod(0o755)
            for source,domain,ok in [('workflow','topic-kichi.com',True),('workflow','other.example',False),('legacy','topic-kichi.com',False)]:
                env=dict(os.environ,PATH=directory+os.pathsep+os.environ['PATH'],GITHUB_REPOSITORY='minna-antenna/minna-antenna',TEST_BUILD_TYPE=source,TEST_DOMAIN=domain)
                result=subprocess.run(['bash','-eu','-c',command],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode==0,ok,result.stdout)
        self.assertNotIn('gh api --method',command)
