import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import diagnose_indexing as d
import monitor_indexing as g


class DiagnosisTests(unittest.TestCase):
    def run_audit(self, missing=False, api_error=False, broken=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'articles').mkdir()
            (root/'articles/a.html').write_text('article')
            url = g.BASE+'articles/a.html'
            xml = '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+('' if missing else '<url><loc>'+url+'</loc></url>')+'</urlset>'
            (root/'sitemap.xml').write_text(xml)
            def fetch(target):
                text = xml if target == g.SITEMAP else ('<a href="'+url+'">article</a>' if target == g.BASE else '<title>A</title><meta name="description" content="B"><link rel="canonical" href="'+url+'"><a href="../missing.html">bad</a>' if target == url else '')
                status = 404 if target.endswith('/robots.txt') or (broken and target.endswith('missing.html')) else 200
                return dict(status=status, final_url=target, error='', text=text, headers={})
            credentials = patch.object(g, 'credentials', return_value='token') if api_error else patch.object(g, 'credentials', side_effect=g.MonitorError('authentication_not_configured'))
            with patch.object(d, 'fetch', side_effect=fetch), credentials, patch.object(g, 'request', side_effect=g.MonitorError('http_error', 403)), patch.object(d.time, 'sleep'), patch.dict(d.os.environ, {}, clear=True):
                return d.diagnose(root)

    def test_missing_sitemap_article_is_still_audited(self):
        report = self.run_audit(missing=True)
        self.assertEqual(len(report['articles']), 1)
        self.assertFalse(report['articles'][0]['in_sitemap'])
        self.assertEqual(len(report['sitemap']['missing']), 1)
        self.assertEqual(report['articles'][0]['status'], '要確認')

    def test_root_robots_404_allows_crawl_but_does_not_prove_indexing(self):
        row = self.run_audit()['articles'][0]
        self.assertTrue(row['robots_allowed'])
        self.assertEqual(row['status'], '要確認')
        self.assertEqual(len(row['inbound_sources']), 1)

    def test_api_failure_and_broken_link_are_visible(self):
        row = self.run_audit(api_error=True, broken=True)['articles'][0]
        self.assertEqual(row['status'], '取得不可')
        self.assertIn('内部リンク先の取得失敗', row['issues'])
        self.assertEqual(row['google']['http_status'], 403)

    def test_rejects_invalid_sitemap(self):
        for xml in ('bad', '<urlset/>', '<!DOCTYPE x><urlset/>'):
            with self.assertRaises((ValueError, d.ET.ParseError)):
                d.sitemap_urls(xml)

    def test_csv_html_and_url_list_are_written(self):
        report = self.run_audit()
        report['articles'][0]['title'] = ['<script>alert(1)</script>']
        with tempfile.TemporaryDirectory() as folder:
            d.write(report, Path(folder))
            source = (Path(folder)/'diagnosis.html').read_text()
            self.assertNotIn('<script>', source)
            self.assertIn('&lt;script&gt;', source)
            self.assertEqual(json.loads((Path(folder)/'diagnosis.json').read_text())['expected_count'], 1)
            self.assertTrue((Path(folder)/'diagnosis.csv').read_bytes().startswith(b'\xef\xbb\xbf'))
            self.assertEqual(len((Path(folder)/'urls.txt').read_text().splitlines()), 1)
