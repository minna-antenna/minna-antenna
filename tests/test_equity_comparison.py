"""Article 6 numeric audit, source integrity and publication registration."""
import json
import subprocess
import sys
import unittest
from unittest.mock import patch
import tempfile
import shutil
import gzip
from scripts.fetch_equity_comparison import prepare
from scripts.analyze_equity_comparison import ROOT, DATA, analyze, load_data
from scripts.audit_equity_comparison import run_audit
from test_article_integrity import Page, BASE
import xml.etree.ElementTree as ET


class EquityComparisonTests(unittest.TestCase):
    def test_independent_raw_decimal_and_official_audit(self):
        result=run_audit()
        self.assertEqual(result['status'],'passed')
        self.assertGreaterEqual(result['numeric_checks'],80)

    def test_results_tables_and_downloadable_code_reproduce(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/analyze_equity_comparison.py'),'--check'],check=True,capture_output=True,text=True)

    def test_windows_monthly_timing_and_simulation_are_explicit(self):
        result,rows,primary=analyze()
        self.assertEqual(result['windows']['5']['start'],'2021-09-30')
        self.assertEqual(result['windows']['10']['start'],'2016-09-30')
        self.assertEqual(result['end'],'2026-09-30')
        for key in ['spy','acwi']:
            self.assertEqual(result['historical_monthly'][key]['contributions'],120)
            self.assertEqual(result['historical_monthly'][key]['first_date'],'2016-10-31')
            self.assertEqual(result['windows']['5']['assets'][key]['monthly_returns_count'],60)
            self.assertEqual(result['windows']['10']['assets'][key]['monthly_returns_count'],120)
        self.assertEqual(len(result['hypothetical']),12)
        for row in result['hypothetical']:
            if row['annual_percent']==0:self.assertEqual(row['final_yen'],row['principal_yen'])

    def test_corrupt_input_hash_stops_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            from pathlib import Path
            target=Path(directory)
            shutil.copy(DATA/'sources.json',target/'sources.json')
            (target/'observations.csv').write_bytes((DATA/'observations.csv').read_bytes()+b'\n')
            with patch('scripts.analyze_equity_comparison.DATA',target):
                with self.assertRaises(ValueError):load_data()

    def test_unverified_split_or_missing_history_is_rejected(self):
        raw={name:gzip.decompress((DATA/'raw'/(name+'.gz')).read_bytes()) for name in ['SPY','ACWI','FED_JPY']}
        response=json.loads(raw['SPY'])
        response['chart']['result'][0]['events']['splits']={'test':{'numerator':2,'denominator':1}}
        broken=dict(raw,SPY=json.dumps(response).encode())
        with self.assertRaises(ValueError):prepare(broken)
        broken=dict(raw,SPY=b'{"chart":{"error":null,"result":[]}}')
        with self.assertRaises(ValueError):prepare(broken)

    def test_article6_once_and_reciprocal_nisa_links(self):
        name='sp500-vs-all-country.html'
        self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1)
        urls=[n.text for n in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')]
        self.assertEqual(urls.count(BASE+'articles/'+name),1)
        page=Page(ROOT/'articles'/name)
        for old in ['new-nisa-beginners-guide.html','bitcoin-vs-stocks-long-term.html']:
            self.assertIn('./'+old,page.hrefs)
            self.assertEqual(Page(ROOT/'articles'/old).hrefs.count('./'+name),1)
        self.assertGreaterEqual(len(list((ROOT/'articles').glob('*.html'))),6)
