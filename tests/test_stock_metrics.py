"""Article13 financial definitions, independent calculations and site gates."""
import copy,gzip,json,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
from scripts import analyze_stock_metrics as model,audit_stock_metrics as independent
from scripts.check_external_links import Links
from test_article_integrity import Page,BASE
ROOT=model.ROOT;DATA=model.DATA
class StockMetricTests(unittest.TestCase):
    def test_full_independent_audit(self):self.assertEqual(independent.audit()['status'],'pass')
    def test_wrong_financial_results_are_rejected(self):
        r=model.calculate()
        for key in ('market_cap','per','pbr','roe_average','eps','bps','per_end'):
            bad=copy.deepcopy(r);bad['companies'][0][key]*=1.01
            with self.subTest(key=key),self.assertRaises(ValueError):independent.audit(bad)
        bad=copy.deepcopy(r);bad['companies'][1]['per']=18.6
        with self.assertRaises(ValueError):independent.audit(bad)
    def test_zero_loss_and_negative_equity_exceptions(self):
        for income in (0,-100):
            x=model.metrics(1000,100,0,100,income,1000,1000);self.assertIsNone(x['per']);self.assertLessEqual(x['eps'],0)
        for equity in (0,-1000):
            x=model.metrics(1000,100,0,100,100,equity,equity);self.assertIsNone(x['pbr']);self.assertIsNone(x['roe_average']);self.assertIsNone(x['roe_end'])
        with self.assertRaises(ValueError):model.metrics(0,100,0,100,100,1000,1000)
        with self.assertRaises(ValueError):model.metrics(1000,100,100,100,100,1000,1000)
    def test_share_count_and_roe_denominators_are_distinguished(self):
        x=model.metrics(1000,120,20,80,1000,10000,20000);self.assertEqual(x['shares'],100);self.assertNotEqual(x['per'],x['per_end']);self.assertNotEqual(x['roe_average'],x['roe_end']);self.assertAlmostEqual(x['pbr'],x['per_end']*x['roe_end'])
        self.assertNotAlmostEqual(x['pbr'],x['per']*x['roe_average'])
    def test_split_issuance_buyback_and_halved_profit(self):
        e=model.calculate()['examples'];a=e['base'];b=e['split'];self.assertEqual(a['market_cap'],b['market_cap']);self.assertEqual(a['per'],b['per']);self.assertEqual(a['pbr'],b['pbr']);self.assertEqual(a['eps']/2,b['eps']);self.assertEqual(e['profit_halved']['per_after'],2*e['profit_halved']['per_before']);self.assertLess(e['issue']['eps'],a['eps']);self.assertEqual(e['issue']['bps'],a['bps']);self.assertGreater(e['buyback']['eps'],a['eps']);self.assertAlmostEqual(e['issue_existing_owner_after'],1/120)
    def test_quote_currency_symbol_date_and_later_split_review(self):
        original=json.loads(gzip.decompress((DATA/'raw/price_7203.json.gz').read_bytes()))
        for change in ('currency','symbol','later_split'):
            r=copy.deepcopy(original);q=r['chart']['result'][0]
            if change=='currency':q['meta']['currency']='USD'
            elif change=='symbol':q['meta']['symbol']='OTHER.T'
            else:q.setdefault('events',{})['splits']={'bad':{'date':1785542400,'numerator':2,'denominator':1}}
            with patch.object(model.gzip,'decompress',return_value=json.dumps(r).encode()),self.assertRaises(ValueError):model.price('7203')
    def test_dates_hindsight_and_reported_precision(self):
        rows=model.load();self.assertEqual(len(rows),6);r=model.calculate();self.assertTrue(r['retrospective_not_point_in_time'])
        for c,x in zip(rows,r['companies']):
            self.assertEqual(c['price_date'],c['fiscal_end']);self.assertGreater(c['disclosed_date'],c['price_date']);self.assertIsNone(x['forecast_per']);self.assertLess(abs(x['eps_vs_reported']),.01);self.assertLess(abs(x['bps_vs_reported']),.01)
        self.assertLess(next(x['profit'] for x in r['companies'] if x['code']=='6758'),0)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);bad={'companies':copy.deepcopy(rows)};bad['companies'][0]['price_date']='2026-11-06';(p/'companies.json').write_text(json.dumps(bad));m={'input_sha256':{'companies.json':model.sha((p/'companies.json').read_bytes())}};(p/'sources.json').write_text(json.dumps(m))
            with patch.object(model,'DATA',p),self.assertRaises(ValueError):model.load()
    def test_generated_tables_code_and_graphs(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/analyze_stock_metrics.py'),'--check'],check=True,capture_output=True);self.assertEqual(model.calculate(),json.loads((DATA/'results.json').read_text()));g=json.loads((DATA/'graph-audit.json').read_text());self.assertEqual(len(g['artifacts']),10);self.assertEqual(g['results_sha256'],model.sha((DATA/'results.json').read_bytes()))
        for x in g['artifacts']:
            b=(DATA/x['file']).read_bytes();self.assertEqual(x['sha256'],model.sha(b))
            if x['file'].endswith('.svg'):ET.fromstring(b)
    def test_external_evidence_and_financial_ledger(self):
        links=Links();links.feed(model.ARTICLE.read_text());checked=json.loads((DATA/'link-checks.json').read_text());self.assertTrue(checked['all_reachable']);self.assertEqual(links.urls,{x['url'] for x in checked['links']});self.assertTrue(all(x['classification']=='reachable' for x in checked['links']));e=json.loads((DATA/'source-evidence.json').read_text());self.assertEqual(e['status'],'reviewed_for_declared_claims');self.assertEqual(links.urls,{x['url'] for x in e['sources']});self.assertTrue(all(x['verified_claim'] and len(x['sha256'])==64 for x in e['sources']));facts=json.loads((DATA/'financial-evidence.json').read_text());self.assertEqual(facts['status'],'issuer_facts_reviewed');self.assertEqual(len(facts['companies']),6)
    def test_twelve_previous_articles_and_related_links_survive(self):
        name=model.ARTICLE.name;p=Page(model.ARTICLE);self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1);urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')];self.assertEqual(urls.count(BASE+'articles/'+name),1);old=[x for x in (ROOT/'articles').glob('*.html') if x!=model.ARTICLE];self.assertGreaterEqual(len(old),12)
        for x in old:self.assertEqual(urls.count(BASE+'articles/'+x.name),1)
        for name in ('bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html','dividend-vs-index-investing.html','etf-vs-mutual-funds.html'):
            self.assertIn('./'+name,p.hrefs);self.assertEqual(Page(ROOT/'articles'/name).hrefs.count('./'+model.ARTICLE.name),1)
if __name__=='__main__':unittest.main()
