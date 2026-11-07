"""Article 9 quality gates: independent economics, provenance and site regression."""
import hashlib,json,subprocess,sys,unittest,tempfile,shutil
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
from scripts import analyze_inflation as model,audit_inflation as independent
from scripts.check_external_links import Links
from test_article_integrity import Page,BASE
ROOT=model.ROOT;DATA=model.DATA

class InflationTests(unittest.TestCase):
    def test_independent_raw_data_currency_cagr_real_returns_and_drawdown(self):
        result=independent.audit();self.assertEqual(result,json.loads((DATA/'calculation-audit.json').read_text()))
        self.assertEqual(result['common_daily_rows'],2485);self.assertEqual(result['monthly_rows'],121);self.assertEqual(result['cpi_primary_months'],133)
        self.assertEqual(result['verified_dividends'],{'GLD':0,'SPY':40})

    def test_audit_rejects_invented_cagr_real_value_and_currency_conversion(self):
        path=DATA/'results.json';read=Path.read_text
        for target,key,value in [('usd_real','cagr',.01),('jpy_nominal','total_return',.01),('jpy_real','total_return',.01)]:
            altered=json.loads(read(path));altered['periods'][0]['metrics'][target][key]=value
            def changed(p,*a,**k):return json.dumps(altered) if p==path else read(p,*a,**k)
            with patch.object(Path,'read_text',changed):
                with self.assertRaises(AssertionError):independent.audit()

    def test_cpi_gap_is_not_interpolated_and_period_endpoints_are_observed(self):
        monthly,daily=model.load();i=next(i for i,r in enumerate(monthly) if r['month']=='2025-10');self.assertEqual(monthly[i]['us_cpi'],'')
        result=model.calculate()
        for asset in model.ASSETS:
            self.assertIsNone(result['chart']['wealth'][asset]['usd_real'][i]);self.assertIsNotNone(result['chart']['wealth'][asset]['jpy_real'][i])
        for p in result['periods']:
            self.assertEqual(p['start'],'2016-09-30' if p['years']==10 else '2021-09-30');self.assertEqual(p['end'],'2026-09-30')
        self.assertIsNotNone(result['annual'][-1]['assets']['spy']['usd_real'])

    def test_calculation_uses_ratio_not_return_minus_inflation(self):
        rows=[dict(p='100',usd_jpy='100',us_cpi='100',jp_cpi='100'),dict(p='105',usd_jpy='110',us_cpi='103',jp_cpi='102')]
        result=model.paths(rows,'p');self.assertAlmostEqual(result['usd_real'][-1]-1,1.05/1.03-1)
        self.assertAlmostEqual(result['jpy_real'][-1],1.05*1.1/1.02)
        self.assertNotAlmostEqual(result['usd_real'][-1]-1,.05-.03)
        self.assertAlmostEqual(1000000/1.03,970873.786407767)
        self.assertEqual(model.mdd(['a','b','c'],[100,50,200])['drawdown'],-.5)
        self.assertEqual(model.mdd(['a','b','c'],[100,50,200])['trough_date'],'b')

    def test_corrupt_inputs_or_missing_calendar_period_stop_release(self):
        path=DATA/'monthly.csv';read=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
            with self.assertRaises(ValueError):model.load()
        # Even a recomputed checksum cannot make a missing month acceptable.
        textread=Path.read_text;manifest=DATA/'sources.json';bad=b'\n'.join(read(path).splitlines()[:-1])+b'\n';m=json.loads(textread(manifest));m['input_sha256']['monthly.csv']=hashlib.sha256(bad).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            temporary=Path(directory)
            for name in ['daily.csv','cpi.csv']:shutil.copyfile(DATA/name,temporary/name)
            (temporary/'monthly.csv').write_bytes(bad)
            (temporary/'sources.json').write_text(json.dumps(m))
            with patch.object(model,'DATA',temporary):
                with self.assertRaises(ValueError):model.load()

    def test_regime_is_ex_post_full_year_and_partial_2026_is_separate(self):
        result=model.calculate();self.assertEqual(len(result['annual']),10)
        self.assertFalse(result['annual'][-1]['full_calendar_year']);self.assertIsNone(result['annual'][-1]['us_high']);self.assertIsNone(result['annual'][-1]['jp_high'])
        for r in result['annual'][:-1]:
            self.assertEqual(r['us_high'],r['us_inflation']>=.04);self.assertEqual(r['jp_high'],r['jp_inflation']>=.02)
        y=next(r for r in result['annual'] if r['year']==2022)
        self.assertTrue(all(v['usd_real']<0 for v in y['assets'].values()));self.assertGreater(y['assets']['gld']['jpy_real'],0)

    def test_generated_tables_graphs_and_code_are_synchronized(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/analyze_inflation.py'),'--check'],check=True,capture_output=True)
        result=json.loads((DATA/'results.json').read_text());self.assertEqual(result,model.calculate())
        graph=json.loads((DATA/'graph-audit.json').read_text());self.assertEqual(len(graph['artifacts']),12)
        self.assertEqual(graph['results_sha256'],hashlib.sha256((DATA/'results.json').read_bytes()).hexdigest())
        for artifact in graph['artifacts']:
            raw=(DATA/artifact['file']).read_bytes();self.assertEqual(artifact['sha256'],hashlib.sha256(raw).hexdigest())
            if artifact['file'].endswith('.svg'):ET.fromstring(raw)

    def test_external_evidence_covers_article_without_restricted_or_missing_urls(self):
        links=Links();links.feed(model.ARTICLE.read_text());checked=json.loads((DATA/'link-checks.json').read_text());self.assertTrue(checked['all_reachable'])
        self.assertEqual(links.urls,{r['url'] for r in checked['links']});self.assertTrue(all(r['classification']=='reachable' for r in checked['links']))
        evidence=json.loads((DATA/'source-evidence.json').read_text());self.assertEqual(evidence['status'],'reviewed_for_declared_claims');self.assertEqual(links.urls,{r['url'] for r in evidence['sources']})
        for r in evidence['sources']:self.assertTrue(r['retrieved_at_utc'][:10] in ['2026-11-06','2026-11-07']);self.assertEqual(len(r['sha256']),64);self.assertTrue(r['verified_claim'])

    def test_article_index_sitemap_and_all_eight_previous_articles_survive(self):
        name='gold-bitcoin-stocks-inflation.html';p=Page(model.ARTICLE)
        self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1)
        urls=[r.text for r in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')];self.assertEqual(urls.count(BASE+'articles/'+name),1)
        self.assertGreaterEqual(len(list((ROOT/'articles').glob('*.html'))),9)
        for old in ['bitcoin-halving.html','bitcoin-four-year-cycle.html','crypto-eth-sol-xrp-comparison.html','bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html','crypto-tax-japan-guide.html','bitcoin-crash-history.html']:self.assertIn(BASE+'articles/'+old,urls)
        for old in ['bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html','crypto-tax-japan-guide.html','bitcoin-crash-history.html']:
            self.assertIn('./'+old,p.hrefs);self.assertEqual(Page(ROOT/'articles'/old).hrefs.count('./'+name),1)
        self.assertEqual(p.meta['robots'],'index,follow');self.assertIn('2025年10月',model.ARTICLE.read_text())
