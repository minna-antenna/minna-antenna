"""Article 8 release gates: real provenance, independent extrema and regression."""
import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
from scripts import analyze_bitcoin_crashes as model,audit_bitcoin_crashes as independent
from scripts.check_external_links import Links
from test_article_integrity import Page,BASE
ROOT=model.ROOT;DATA=model.DATA

class BitcoinCrashTests(unittest.TestCase):
    def test_frozen_prices_and_independent_extrema_dates_and_recovery(self):
        result=independent.audit()
        self.assertEqual(result,json.loads((DATA/'calculation-audit.json').read_text()))
        self.assertEqual(result['raw_rows_verified'],5057)
        self.assertEqual(result['valid_trading_rows'],5054)
        self.assertEqual(result['point_requeries'],15)
        self.assertEqual(result['hourly_close_crosschecks'],3)

    def test_publication_rejects_changed_drawdown_date_recovery_and_yen_amount(self):
        path=DATA/'results.json';original=Path.read_text
        for field,value in [('peak_date','2013-12-03'),('recovery_date','2017-02-24'),('drawdown_pct','-1'),('model_trough_jpy',999999)]:
            altered=json.loads(original(path));altered['events'][0][field]=value
            def read(p,*args,**kwargs):return json.dumps(altered) if p==path else original(p,*args,**kwargs)
            with patch.object(Path,'read_text',read):
                with self.assertRaises(AssertionError):independent.audit()

    def test_checksum_and_missing_or_reordered_date_stop_analysis(self):
        source=DATA/'observations.csv';original=Path.read_bytes
        with patch.object(Path,'read_bytes',lambda p:original(p)+b'\n' if p==source else original(p)):
            with self.assertRaises(ValueError):model.load()
        original_text=Path.read_text;manifest_path=DATA/'sources.json'
        damaged=b'\n'.join(original(source).splitlines()[:-1])+b'\n'
        changed_manifest=json.loads(original_text(manifest_path));changed_manifest['input_sha256']=hashlib.sha256(damaged).hexdigest()
        with patch.object(Path,'read_bytes',lambda p:damaged if p==source else original(p)),patch.object(Path,'read_text',lambda p,*a,**k:json.dumps(changed_manifest) if p==manifest_path else original_text(p,*a,**k)):
            with self.assertRaises(ValueError):model.load()
        rows=model.load();self.assertEqual(len(rows),5057)
        result=model.calculate(rows);self.assertEqual(result['excluded_zero_volume_dates'],['2015-01-06','2015-01-07','2015-01-08'])
        for e in result['events']:
            self.assertNotIn(e['peak_date'],result['excluded_zero_volume_dates']);self.assertNotIn(e['trough_date'],result['excluded_zero_volume_dates'])

    def test_local_window_and_first_equal_recovery_without_cherry_picking(self):
        rows=[dict(date=f'2020-01-0{i+1}',close=str(v),volume='1') for i,v in enumerate([100,40,99,100,150])]
        e=model.episode(rows,'fixture','2020-01-01','2020-01-02')
        self.assertEqual(e['drawdown_pct'],'-60.0')
        self.assertEqual(e['peak_date'],'2020-01-01');self.assertEqual(e['trough_date'],'2020-01-02')
        self.assertEqual(e['recovery_date'],'2020-01-04');self.assertEqual(e['peak_to_recovery_days'],3)
        self.assertEqual(e['trough_to_recovery_days'],2);self.assertEqual(e['model_trough_jpy'],400000)
        rows[1]['volume']='0'
        with self.assertRaises(ValueError):model.episode(rows,'fixture','2020-01-01','2020-01-02')

    def test_ties_and_unrecovered_are_not_reported_as_completed_recovery(self):
        rows=[dict(date=f'2020-01-0{i+1}',close=str(v),volume='1') for i,v in enumerate([100,100,50,50,70])]
        e=model.episode(rows,'fixture','2020-01-01','2020-01-05')
        self.assertEqual(e['peak_date'],'2020-01-01');self.assertEqual(e['trough_date'],'2020-01-03')
        self.assertIsNone(e['recovery_date']);self.assertIsNone(e['peak_to_recovery_days']);self.assertEqual(e['unrecovered_days'],4)
        real=model.calculate()['events'][-1];self.assertIsNone(real['recovery_date']);self.assertEqual(real['unrecovered_days'],395)

    def test_article_tables_code_csv_and_chart_inputs_reproduce(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/analyze_bitcoin_crashes.py'),'--check'],check=True,capture_output=True)
        data=json.loads((DATA/'chart-data.json').read_text());rows=model.load()
        self.assertEqual(data,model.chart_data(rows,model.calculate(rows)))
        self.assertEqual(sum(v is None for _,v in data['long_price']),3)
        manifest=json.loads((DATA/'graph-audit.json').read_text())
        self.assertEqual(hashlib.sha256((DATA/'chart-data.json').read_bytes()).hexdigest(),manifest['chart_data_sha256'])
        self.assertEqual(len(manifest['artifacts']),10)
        for artifact in manifest['artifacts']:
            raw=(DATA/artifact['file']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),artifact['sha256'])
            if artifact['file'].endswith('.svg'):ET.fromstring(raw)
        for name in ['long-price','drawdowns','recovery-days','million-yen','halving-timeline']:
            self.assertIn(f'./data/bitcoin-crash/{name}.svg',model.ARTICLE.read_text())

    def test_explanatory_price_claims_and_recovery_alt_text_match_data(self):
        text=model.ARTICLE.read_text();result=model.calculate()
        for section,event in zip(['early','bubble','covid','credit','recent'],result['events']):
            start=text.index('id="'+section+'"');end=text.index('<h2',start+1);part=text[start:end]
            for field in ['peak_usd','trough_usd']:
                self.assertIn(f"{model.D(event[field]):,.2f}ドル",part)
            for field in ['peak_date','trough_date']:
                _,month,day=map(int,event[field].split('-'));self.assertIn(f'{month}月{day}日',part)
        self.assertIn(f"{model.D(result['last_close_usd']):,.2f}ドル",text)
        for event in result['events']:
            if event['recovery_date']:self.assertIn(str(event['peak_to_recovery_days'])+'日',text)

    def test_external_sources_are_verified_and_cover_current_article(self):
        links=Links();links.feed(model.ARTICLE.read_text());checks=json.loads((DATA/'link-checks.json').read_text())
        self.assertEqual(links.urls,{r['url'] for r in checks['links']});self.assertTrue(checks['all_reachable'])
        self.assertTrue(all(r['classification']=='reachable' for r in checks['links']))
        evidence=json.loads((DATA/'source-evidence.json').read_text())
        self.assertEqual(links.urls,{s['url'] for s in evidence['sources']})
        self.assertEqual(evidence['status'],'reviewed_for_declared_claims')
        self.assertEqual(evidence['halving_dates'],model.calculate()['halvings'])
        for source in evidence['sources']:
            self.assertEqual(len(source['sha256']),64);self.assertTrue(source['retrieved_at_utc'].startswith('2026-11-06'));self.assertTrue(source['verified_claim'])

    def test_index_sitemap_retention_and_reciprocal_links(self):
        name='bitcoin-crash-history.html';p=Page(model.ARTICLE)
        self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1)
        urls=[n.text for n in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')]
        self.assertEqual(urls.count(BASE+'articles/'+name),1)
        self.assertGreaterEqual(len(list((ROOT/'articles').glob('*.html'))),8)
        for old in ['bitcoin-halving.html','bitcoin-four-year-cycle.html','crypto-eth-sol-xrp-comparison.html','bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html','crypto-tax-japan-guide.html']:
            self.assertIn(BASE+'articles/'+old,urls)
        for old in ['bitcoin-halving.html','bitcoin-four-year-cycle.html','crypto-eth-sol-xrp-comparison.html','bitcoin-vs-stocks-long-term.html','crypto-tax-japan-guide.html']:
            self.assertIn('./'+old,p.hrefs);self.assertEqual(Page(ROOT/'articles'/old).hrefs.count('./'+name),1)
        self.assertEqual(p.meta['robots'],'index,follow')
        self.assertIn('Bitstamp',model.ARTICLE.read_text());self.assertIn('未回復',model.ARTICLE.read_text());self.assertIn('為替固定',model.ARTICLE.read_text())
