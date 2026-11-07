"""Article11 finance, source, NISA and regression gates."""
import copy,gzip,hashlib,json,subprocess,sys,unittest,zipfile,io,unicodedata,xml.etree.ElementTree as ET
from unittest.mock import patch
from scripts import analyze_etf_funds as model,audit_etf_funds as independent
from scripts.check_external_links import Links
from test_article_integrity import Page,BASE
ROOT=model.ROOT;DATA=model.DATA
class EtfFundTests(unittest.TestCase):
    def test_independent_audit_all_calculations(self):self.assertEqual(independent.audit()['status'],'pass')
    def test_bad_returns_costs_and_double_counting_are_rejected(self):
        for mutate in (lambda r:r['metrics'][0].update(cagr=.3),lambda r:r['metrics'][1].update(mdd=-.01),lambda r:r['metrics'][0].update(trough='2025-04-10'),lambda r:r['costs'][0].update(final=r['costs'][0]['final']+1),lambda r:r['costs'][0].update(net_annual=.05),lambda r:r['accumulation'][0].update(final=1),lambda r:r['cashflows'][1].update(etf_reinvest=1090000)):
            r=model.calculate();mutate(r)
            with self.assertRaises(ValueError):independent.audit(r)
    def test_same_currency_period_and_nav_not_market(self):
        r=model.calculate();self.assertEqual(r['currency'],'JPY');self.assertTrue(r['nav_not_market_price']);self.assertEqual(len(r['common_dates']),1222)
        for x in r['metrics']:self.assertEqual((x['start'],x['end'],x['observations']),('2021-09-30','2026-09-30',1222))
        self.assertEqual(len(r['accumulation']),36);self.assertEqual(len(r['costs']),45);self.assertTrue(all(len(x)==61 for x in r['curves'].values()))
        self.assertTrue(all(x['partial']==(x['year']==2026) for x in r['annual']))
    def test_formula_and_cash_conservation(self):
        self.assertEqual(model.annuity(30000,0,20),7200000);self.assertAlmostEqual(1.10*.90-1,-.01)
        for x in model.cashflows():
            self.assertEqual(x['etf_reinvest'],x['fund_internal']);self.assertAlmostEqual(x['etf_cash_asset'],x['fund_sale_asset'],places=6);self.assertAlmostEqual(x['etf_cash_received'],x['fund_sale_received'],places=6)
        with self.assertRaises(ValueError):model.annuity(30000,-1,20)
        r=model.calculate()
        for y in (20,30):
            rows=[x for x in r['costs'] if x['monthly']==30000 and x['years']==y];self.assertEqual([x['final'] for x in rows],sorted([x['final'] for x in rows],reverse=True))
    def test_corrupt_input_and_unreviewed_distributions_stop(self):
        original=model.gzip.decompress
        def bad(b):return original(b)+b'\n2026\x94N11\x8c\x8e07\x93\xfa,42000,1,100,9\n'
        with patch.object(model.gzip,'decompress',side_effect=bad),self.assertRaises(ValueError):model.read()
        manifest=json.loads((DATA/'sources.json').read_text());manifest['input_sha256']['raw/slim.csv.gz']='0'*64;originalread=model.Path.read_text
        def read(p,*args,**kwargs):return json.dumps(manifest) if p==DATA/'sources.json' else originalread(p,*args,**kwargs)
        with patch.object(model.Path,'read_text',read),self.assertRaises(ValueError):model.read()
    def test_nisa_actual_target_lists(self):
        ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};manifest=json.loads((DATA/'sources.json').read_text())
        def rows(name):
            p=DATA/'raw'/(name+'.xlsx.gz');b=p.read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),manifest['input_sha256']['raw/'+p.name]);z=zipfile.ZipFile(io.BytesIO(gzip.decompress(b)));strings=[''.join(t.itertext()) for t in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)];out=[]
            for file in z.namelist():
                if not file.startswith('xl/worksheets/sheet') or not file.endswith('.xml'):continue
                for row in ET.fromstring(z.read(file)).findall('.//m:row',ns):
                    values=[]
                    for c in row.findall('m:c',ns):
                        v=c.find('m:v',ns);val=v.text if v is not None else '';values.append(unicodedata.normalize('NFKC',strings[int(val)] if c.get('t')=='s' and val else val))
                    out.append(values)
            return out
        slim=[x for x in rows('growth_unlisted') if '03311187' in x];etf=[x for x in rows('growth_listed') if '26330' in x];self.assertEqual(len(slim),1);self.assertEqual(len(etf),1);self.assertTrue(any('eMAXIS Slim' in v for v in slim[0]));self.assertTrue(any('為替ヘッジなし' in v for v in etf[0]));self.assertEqual(slim[0][-1],'対象');self.assertEqual(etf[0][-1],'非対象')
        text=(DATA/'nisa-tsumitate-list.txt').read_text();self.assertIn('eMAXIS Slim 米国株式（S&P500）',text);self.assertNotIn('NEXT FUNDS S&P 500',text)
        proof=json.loads((DATA/'nisa-evidence.json').read_text());self.assertTrue(proof['slim']['growth']);self.assertTrue(proof['etf']['growth']);self.assertFalse(proof['etf']['tsumitate'])
    def test_graphs_tables_and_downloadable_code_synchronized(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/analyze_etf_funds.py'),'--check'],check=True,capture_output=True);self.assertEqual(model.calculate(),json.loads((DATA/'results.json').read_text()));g=json.loads((DATA/'graph-audit.json').read_text());self.assertEqual(len(g['artifacts']),12);self.assertEqual(g['results_sha256'],model.sha((DATA/'results.json').read_bytes()))
        for a in g['artifacts']:
            b=(DATA/a['file']).read_bytes();self.assertEqual(model.sha(b),a['sha256'])
            if a['file'].endswith('.svg'):ET.fromstring(b)
    def test_external_evidence_and_limitations(self):
        links=Links();links.feed(model.ARTICLE.read_text());checked=json.loads((DATA/'link-checks.json').read_text());self.assertTrue(checked['all_reachable']);self.assertEqual(links.urls,{x['url'] for x in checked['links']});self.assertTrue(all(x['classification']=='reachable' for x in checked['links']))
        evidence=json.loads((DATA/'source-evidence.json').read_text());self.assertEqual(evidence['status'],'reviewed_for_declared_claims');self.assertEqual(links.urls,{x['url'] for x in evidence['sources']});self.assertTrue(all(x['verified_claim'] and len(x['sha256'])==64 for x in evidence['sources']))
        text=model.ARTICLE.read_text();self.assertIn('追跡誤差は未算出',text);self.assertIn('HTTP403',text);self.assertIn('2027年1月',text);self.assertIn('1,200万円',text)
    def test_previous_ten_articles_and_related_links_survive(self):
        page=Page(model.ARTICLE);name=model.ARTICLE.name;self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1);locs=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')];self.assertEqual(locs.count(BASE+'articles/'+name),1)
        old=[p for p in (ROOT/'articles').glob('*.html') if p!=model.ARTICLE];self.assertGreaterEqual(len(old),10)
        for p in old:self.assertEqual(locs.count(BASE+'articles/'+p.name),1)
        for name in ('bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html','gold-bitcoin-stocks-inflation.html','dividend-vs-index-investing.html'):
            self.assertIn('./'+name,page.hrefs);self.assertEqual(Page(ROOT/'articles'/name).hrefs.count('./'+model.ARTICLE.name),1)
if __name__=='__main__':unittest.main()
