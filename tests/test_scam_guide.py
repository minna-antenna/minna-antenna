"""Article12: defensive-source, contact, UI safety and site regression gates."""
import copy,hashlib,json,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
from unittest.mock import patch
from urllib.parse import urlsplit
from scripts import build_scam_guide as guide
from scripts.check_external_links import Links
from test_article_integrity import Page,BASE
ROOT=guide.ROOT;DATA=guide.DATA
class Controls(HTMLParser):
    def __init__(self,text):super().__init__();self.inputs=[];self.tags=[];self.scripts=[];self.events=[];self.feed(text)
    def handle_starttag(self,t,a):
        a=dict(a);self.tags.append(t)
        if t=='input':self.inputs.append(a)
        if t=='script':self.scripts.append(a)
        self.events +=[k for k in a if k.startswith('on')]
class ScamGuideTests(unittest.TestCase):
    def test_editorial_scope_and_required_situations(self):
        r,urls=guide.load();self.assertEqual(len(r['types']),14);self.assertEqual(len(r['signals']),12);self.assertEqual([x['id'] for x in r['firstaid']],list('ABCDEFGH'));self.assertFalse(r['statistics_used']);self.assertIn('特定の実事件',r['examples'])
        for x in r['types']:
            self.assertEqual(set(x),{'id','name','contact','pitch','signal','mechanism','prevent','response','source'});self.assertIn(x['source'],urls)
    def test_missing_source_duplicate_items_or_unreviewed_stats_fail(self):
        original=json.loads((DATA/'guide.json').read_text());sources=(DATA/'sources.json').read_text()
        for mutate in (lambda r:r.update(statistics_used=True),lambda r:r['signals'][1].update(id=r['signals'][0]['id']),lambda r:r['types'][0].update(source='unverified'),lambda r:r.update(firstaid=r['firstaid'][:-1])):
            r=copy.deepcopy(original);mutate(r)
            with tempfile.TemporaryDirectory() as folder:
                p=Path(folder);(p/'guide.json').write_text(json.dumps(r));(p/'sources.json').write_text(sources)
                with patch.object(guide,'DATA',p),self.assertRaises(ValueError):guide.load()
    def test_generated_tables_and_content_hashes(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/build_scam_guide.py'),'--check'],check=True,capture_output=True)
        r=json.loads((DATA/'content-audit.json').read_text());self.assertFalse(r['reader_data_transmitted']);self.assertFalse(r['safety_score']);self.assertEqual(r['guide_sha256'],guide.sha((DATA/'guide.json').read_bytes()));self.assertEqual(r['checklist_js_sha256'],guide.sha((DATA/'checklist.js').read_bytes()))
        a=json.loads((DATA/'diagram-audit.json').read_text());self.assertEqual(a['guide_sha256'],r['guide_sha256']);self.assertEqual(len(a['artifacts']),2)
        for f in a['artifacts']:
            b=(DATA/f['file']).read_bytes();self.assertEqual(f['sha256'],guide.sha(b))
            if f['file'].endswith('.svg'):ET.fromstring(b)
    def test_no_dangerous_inputs_forms_or_scripts(self):
        p=Controls(guide.ARTICLE.read_text());self.assertEqual(len(p.inputs),12);self.assertTrue(all(x.get('type')=='checkbox' for x in p.inputs));self.assertFalse(set(p.tags)&{'form','textarea','iframe','object','embed'});self.assertFalse(p.events)
        scripts=[x.get('src') for x in p.scripts if x.get('src')];self.assertCountEqual(scripts,['https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8155299200535467','./data/scam-prevention/checklist.js'])
        js=(DATA/'checklist.js').read_text()
        for token in ['fetch(', 'XMLHttpRequest','WebSocket','sendBeacon','localStorage','sessionStorage','document.cookie','window.ethereum','WalletConnect','eval(', 'innerHTML','window.location']:
            self.assertNotIn(token,js)
        self.assertIn('未選択でも安全とは判断できません',js);self.assertIn('詐欺を確定するものではありません',js)
    def test_contacts_have_scope_hours_and_distinct_official_numbers(self):
        r,_=guide.load();contacts=r['contacts'];self.assertEqual(len(contacts),6);allphones=' '.join(x['phone'] for x in contacts)
        for n in ['#9110','110','188','0570-050588','03-6206-6066','0570-016811','03-5251-6811']:self.assertIn(n,allphones)
        for x in contacts:self.assertTrue(x['hours']);self.assertTrue(x['role'])
        evidence=json.loads((DATA/'source-evidence.json').read_text());self.assertEqual({x['number_digits'] for x in evidence['contact_number_checks']},{'0570050588','0362066066','0570016811','0352516811','9110','110','188'});self.assertTrue(all(x['status']=='matched_fetched_official_text' for x in evidence['contact_number_checks']))
    def test_official_source_coverage_and_failed_links_not_waived(self):
        urls=Links();urls.feed(guide.ARTICLE.read_text());checked=json.loads((DATA/'link-checks.json').read_text());self.assertTrue(checked['all_reachable']);self.assertEqual(len(checked['links']),20);self.assertEqual(urls.urls,{x['url'] for x in checked['links']});self.assertTrue(all(x['classification']=='reachable' for x in checked['links']))
        evidence=json.loads((DATA/'source-evidence.json').read_text());self.assertEqual(evidence['status'],'reviewed_for_declared_claims');self.assertEqual(urls.urls,{x['url'] for x in evidence['sources']});self.assertTrue(all(x['verified_claim'] and len(x['sha256'])==64 for x in evidence['sources']))
        allowed={'www.npa.go.jp','www.fsa.go.jp','www.caa.go.jp','www.kokusen.go.jp','www.ipa.go.jp','ethereum.org','support.kraken.com','support.metamask.io','niben.jp','www.pref.aichi.jp','www.investor.gov'};self.assertTrue(all(urlsplit(u).hostname in allowed for u in urls.urls))
        m=json.loads((DATA/'sources.json').read_text());self.assertEqual({x['status'] for x in m['excluded_and_replaced']},{403,404})
    def test_critical_safety_distinctions_are_visible(self):
        text=guide.ARTICLE.read_text()
        for clause in ['登録は個別の投資先の安全性や利益','接続を解除しても','同じシードで口座を増やすだけでは','回収は保証できません','被害は、不注意な人だけ','時間を188全体の受付時間と混同','2026年9月30日','秘密鍵やシードフレーズを添付する必要はありません']:
            self.assertIn(clause,text)
        self.assertTrue(all('https://' not in x['pitch'] for x in guide.load()[0]['types']))
    def test_previous_eleven_articles_and_reciprocal_links(self):
        page=Page(guide.ARTICLE);name=guide.ARTICLE.name;self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1);locs=[x.text for x in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')];self.assertEqual(locs.count(BASE+'articles/'+name),1);old=[p for p in (ROOT/'articles').glob('*.html') if p!=guide.ARTICLE];self.assertGreaterEqual(len(old),11)
        for p in old:self.assertEqual(locs.count(BASE+'articles/'+p.name),1)
        for name in ('crypto-eth-sol-xrp-comparison.html','bitcoin-vs-stocks-long-term.html','crypto-tax-japan-guide.html','bitcoin-crash-history.html','gold-bitcoin-stocks-inflation.html'):
            self.assertIn('./'+name,page.hrefs);self.assertEqual(Page(ROOT/'articles'/name).hrefs.count('./'+guide.ARTICLE.name),1)
if __name__=='__main__':unittest.main()
