"""Article 10 gates: economics, provenance, negative cases and publication integrity."""
import copy,hashlib,json,subprocess,sys,unittest,xml.etree.ElementTree as ET
from unittest.mock import patch
from scripts import analyze_dividends as model,audit_dividends as independent
from scripts.check_external_links import Links
from test_article_integrity import Page,BASE
ROOT=model.ROOT;DATA=model.DATA
class DividendsTests(unittest.TestCase):
    def test_independent_full_audit(self):self.assertEqual(independent.audit()['status'],'pass')
    def test_tampered_financial_results_are_rejected(self):
        r=model.calculate()
        for field in ('cagr','total_return','price_return','trailing_yield','annualized_volatility'):
            bad=copy.deepcopy(r);bad['periods'][0][field]+=.001
            with self.subTest(field=field),self.assertRaises(ValueError):independent.audit(bad)
        bad=copy.deepcopy(r);bad['periods'][0]['mdd']['trough']='2020-03-24'
        with self.assertRaises(ValueError):independent.audit(bad)
    def test_double_counting_and_annuity_mutations_are_rejected(self):
        for mutate in (lambda r:r['cashflows'][1].update(reinvested=1090000),lambda r:r['accumulation'][3].update(final=r['accumulation'][3]['final']+1),lambda r:r['income'][0].update(monthly_average=20000)):
            r=model.calculate();mutate(r)
            with self.assertRaises(ValueError):independent.audit(r)
    def test_principal_and_distribution_conservation(self):
        self.assertEqual(model.annuity(30000,0,20),7200000)
        for x in model.cashflows():
            self.assertAlmostEqual(x['distributed_asset'],x['withdrawal_asset'],places=6)
            self.assertAlmostEqual(x['distributed_cash'],x['withdrawal_cash'],places=6)
        zero=model.cashflows(total=0,distribution=0)[-1];self.assertEqual(zero['reinvested'],1000000)
        no_growth=model.cashflows(total=.03,distribution=.03)[-1];self.assertAlmostEqual(no_growth['distributed_asset'],1000000);self.assertAlmostEqual(no_growth['distributed_cash'],600000)
        with self.assertRaises(ValueError):model.cashflows(total=-1)
    def test_unreviewed_split_and_raw_checksum_stop_analysis(self):
        manifest=json.loads((DATA/'sources.json').read_text());manifest['input_sha256']['raw/VYM.json.gz']='0'*64
        original=model.Path.read_text
        def read(p,*a,**kw):return json.dumps(manifest) if p==DATA/'sources.json' else original(p,*a,**kw)
        with patch.object(model.Path,'read_text',read),self.assertRaises(ValueError):model.read()
    def test_unreviewed_split_event_stops_analysis(self):
        import gzip
        raw=json.loads(gzip.decompress((DATA/'raw/VYM.json.gz').read_bytes()))
        raw['chart']['result'][0]['events']['splits']={'unreviewed':{'splitRatio':'2:1'}}
        with patch.object(model.gzip,'decompress',return_value=json.dumps(raw).encode()),self.assertRaises(ValueError):model.read()

    def test_periods_and_distributions_have_common_conditions(self):
        r=model.calculate()
        self.assertEqual(len(r['periods']),4)
        for years,count in ((5,1255),(10,2513)):
            p=[x for x in r['periods'] if x['years']==years];self.assertEqual(p[0]['start'],p[1]['start']);self.assertEqual(p[0]['end'],p[1]['end']);self.assertTrue(all(x['observations']==count for x in p))
        self.assertEqual(r['currency'],'USD');self.assertTrue(all(x['partial']==(x['year']==2026) for x in r['annual']))
        self.assertTrue(all(x['max_relative_error']<1e-5 for x in r['distribution_checks']))
    def test_generated_tables_graphs_and_downloadable_code(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/analyze_dividends.py'),'--check'],check=True,capture_output=True)
        self.assertEqual(json.loads((DATA/'results.json').read_text()),model.calculate())
        graph=json.loads((DATA/'graph-audit.json').read_text());self.assertEqual(len(graph['artifacts']),14);self.assertEqual(graph['results_sha256'],model.sha((DATA/'results.json').read_bytes()))
        for a in graph['artifacts']:
            raw=(DATA/a['file']).read_bytes();self.assertEqual(a['sha256'],model.sha(raw))
            if a['file'].endswith('.svg'):ET.fromstring(raw)
    def test_source_reachability_and_reviewed_claims(self):
        links=Links();links.feed(model.ARTICLE.read_text());audit=json.loads((DATA/'link-checks.json').read_text());self.assertTrue(audit['all_reachable']);self.assertEqual(links.urls,{x['url'] for x in audit['links']})
        self.assertTrue(all(x['classification']=='reachable' for x in audit['links']))
        evidence=json.loads((DATA/'source-evidence.json').read_text());self.assertEqual(evidence['status'],'reviewed_for_declared_claims');self.assertEqual(links.urls,{x['url'] for x in evidence['sources']})
        self.assertTrue(all(x['verified_claim'] and len(x['sha256'])==64 for x in evidence['sources']))
    def test_old_nine_articles_and_reciprocal_related_links(self):
        p=Page(model.ARTICLE);name=model.ARTICLE.name;self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1)
        urls=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')];self.assertEqual(urls.count(BASE+'articles/'+name),1)
        old=[x for x in (ROOT/'articles').glob('*.html') if x!=model.ARTICLE];self.assertGreaterEqual(len(old),9)
        for x in old:self.assertEqual(urls.count(BASE+'articles/'+x.name),1)
        for name in ('bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html','gold-bitcoin-stocks-inflation.html'):
            self.assertIn('./'+name,p.hrefs);self.assertEqual(Page(ROOT/'articles'/name).hrefs.count('./'+model.ARTICLE.name),1)
        self.assertIn('株式数比例配分方式',model.ARTICLE.read_text());self.assertIn('外国税額控除',model.ARTICLE.read_text())
if __name__=='__main__':unittest.main()
