"""Distinguish unavailable verification from a proven deleted URL, without network."""
from urllib.error import HTTPError,URLError
import unittest
import json
from pathlib import Path
from scripts.check_external_links import classify,check,body_problem


class Response:
    status=200
    headers={'Content-Type':'application/pdf'}
    url='https://official.example/new.pdf'
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return b'%PDF-1.7\nverified test fixture'


class ExternalLinkTests(unittest.TestCase):
    def test_status_classes_do_not_confuse_restriction_and_deletion(self):
        self.assertEqual(classify(404),'broken')
        self.assertEqual(classify(410),'broken')
        self.assertEqual(classify(403),'access_restricted')
        self.assertEqual(classify(429),'transient_unverified')
        self.assertEqual(classify(503),'transient_unverified')
        self.assertEqual(classify(error=TimeoutError()),'network_unverified')
        self.assertEqual(body_problem('https://official.example/a.pdf',b'<html>denied</html>','text/html'),'expected_pdf_not_received')
        self.assertEqual(body_problem('https://official.example/',b'<title>Access Denied</title>','text/html'),'soft_access_restriction')

    def test_transient_retry_redirect_and_restriction_behavior(self):
        count=[]
        def eventually(request,timeout):
            count.append(1)
            if len(count)==1:raise HTTPError(request.full_url,503,'Unavailable',{},None)
            return Response()
        result=check('https://official.example/old.pdf',opener=eventually,sleeper=lambda _:None)
        self.assertEqual(result['classification'],'reachable')
        self.assertTrue(result['redirected'])
        self.assertEqual([a['status'] for a in result['attempts']],[503,200])
        def restricted(request,timeout):raise HTTPError(request.full_url,403,'Forbidden',{},None)
        result=check('https://official.example/a.pdf',opener=restricted,sleeper=lambda _:None)
        self.assertEqual(result['classification'],'access_restricted')
        self.assertEqual(len(result['attempts']),1)

    def test_exhausted_network_retries_remain_unverified(self):
        def unavailable(request,timeout):raise URLError(TimeoutError())
        result=check('https://official.example/a.pdf',opener=unavailable,sleeper=lambda _:None)
        self.assertEqual(result['classification'],'network_unverified')
        self.assertEqual(len(result['attempts']),3)
        self.assertIsNone(result['status'])

    def test_japanese_soft_404_with_http_200_and_shift_jis_is_not_accepted(self):
        class Missing(Response):
            headers={'Content-Type':'text/html; charset=Shift_JIS'}
            url='https://official.example/missing.htm'
            def read(self):
                return '<html><title>指定されたページを表示できませんでした</title></html>'.encode('cp932')
        result=check('https://official.example/missing.htm',opener=lambda *args,**kwargs:Missing(),sleeper=lambda _:None)
        self.assertEqual(result['status'],200)
        self.assertEqual(result['classification'],'soft_404')
        self.assertEqual(result['content_problem'],'soft_not_found_page')

    def test_saved_article_source_audit_covers_current_links_without_unverified_results(self):
        from scripts.check_external_links import Links,ROOT
        page=ROOT/'articles/crypto-tax-japan-guide.html'
        links=Links();links.feed(page.read_text())
        result=json.loads((ROOT/'articles/data/crypto-tax/link-checks.json').read_text())
        self.assertEqual(links.urls,{r['url'] for r in result['links']})
        self.assertTrue(result['all_reachable'])
        for row in result['links']:
            self.assertEqual(row['classification'],'reachable',row['url'])
            self.assertTrue(row['sha256'])
            self.assertTrue(row['checked_at_utc'])
