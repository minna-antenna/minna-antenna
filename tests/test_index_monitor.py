"""Offline protocol/diagnostic/security tests; never claims a real Google connection."""
import csv
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import monitor_indexing as m

A = m.BASE + 'articles/example.html'
B = m.BASE + 'articles/new-article.html'
ENV = dict(GSC_CLIENT_ID='test-client', GSC_CLIENT_SECRET='test-secret', GSC_REFRESH_TOKEN='test-refresh')


def xml(*urls):
    return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + u + '</loc></url>' for u in urls) + '</urlset>').encode()


def inspection(verdict='PASS', **extra):
    return {'inspectionResult': {'indexStatusResult': dict(verdict=verdict, coverageState='Google reason', lastCrawlTime='2026-11-07T00:00:00Z', **extra)}}


class IndexMonitorTests(unittest.TestCase):
    def test_discovery_deduplicates_filters_and_adds_new_articles(self):
        raw = xml(A, A, B, m.BASE, 'https://evil.example/articles/a.html', A + '?x=1', A + '#a', m.BASE + 'articles/../a.html', m.BASE + 'articles/%2e%2e/a.html')
        self.assertEqual(m.article_urls(raw), [A, B])

    def test_empty_invalid_and_unsafe_xml_fail_closed(self):
        for raw in (b'bad xml', xml(m.BASE), b'<!DOCTYPE x><urlset/>', b'<sitemapindex/>'):
            with self.subTest(raw=raw), self.assertRaises(m.MonitorError):
                m.article_urls(raw)

    def test_verdicts_not_coverage_text_determine_status(self):
        for verdict, expected in [('PASS', 'indexed'), ('FAIL', 'not_indexed'), ('NEUTRAL', 'not_indexed'), ('PARTIAL', 'unverifiable'), ('VERDICT_UNSPECIFIED', 'unverifiable')]:
            with self.subTest(verdict=verdict):
                result = m.classify(A, m.BASE, inspection(verdict))
                self.assertEqual(result['status'], expected)
                self.assertEqual(result['reason'], 'Google reason')
                self.assertEqual(result['last_crawl_time'], '2026-11-07T00:00:00Z')

    def test_page_fetch_failure_not_confused_with_api_error(self):
        result = m.classify(A, m.BASE, inspection('NEUTRAL', pageFetchState='NOT_FOUND'))
        self.assertEqual(result['status'], 'not_indexed')
        self.assertEqual(result['page_fetch_state'], 'NOT_FOUND')

    def test_missing_result_is_not_registered(self):
        for response in ({}, {'inspectionResult': None}, {'inspectionResult': {'indexStatusResult': None}}):
            self.assertEqual(m.classify(A, m.BASE, response)['status'], 'unverifiable')

    def test_untrusted_inspection_links_not_used(self):
        response = inspection()
        response['inspectionResult']['inspectionResultLink'] = 'https://evil.example/login'
        self.assertEqual(m.classify(A, m.BASE, response)['inspection_link'], m.manual_link(m.BASE))

    @patch.object(m, 'request', return_value=xml(A, B))
    def test_missing_auth_reports_all_urls_unknown_and_nonzero(self, call):
        report, code = m.monitor({})
        self.assertEqual(code, 2)
        self.assertEqual(report['authentication'], 'not_configured')
        self.assertEqual([r['status'] for r in report['articles']], ['unverifiable'] * 2)
        self.assertEqual(call.call_count, 1)  # No unauthenticated Google request.

    @patch.object(m, 'request', side_effect=m.MonitorError('http_error', 503))
    def test_sitemap_failure_not_empty_success(self, call):
        report, code = m.monitor({})
        self.assertEqual(code, 2)
        self.assertEqual(report['sitemap']['http_status'], 503)
        self.assertEqual(report['articles'], [])

    @patch.object(m, 'request', return_value=xml(A, B))
    @patch.object(m, 'MAX_URLS', 1)
    def test_quota_safety_limit_never_silently_samples(self, call):
        report, code = m.monitor(ENV)
        self.assertEqual(code, 2)
        self.assertEqual(len(report['articles']), 2)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(report['error'], 'daily_safety_limit_exceeded')

    def test_success_includes_google_sitemap_and_preserves_canonicals(self):
        with patch.object(m, 'request', side_effect=[xml(A, B), {'access_token': 'test-access', 'scope': m.SCOPE}, {'path': m.SITEMAP, 'lastDownloaded': '2026-11-07T00:00:00Z', 'errors': '0'}, inspection('PASS', googleCanonical=A), inspection('NEUTRAL')]) as call:
            report, code = m.monitor(ENV, sleep=lambda _: None)
        self.assertEqual(code, 0)
        self.assertEqual(report['articles'][0]['google_canonical'], A)
        self.assertEqual(report['google_sitemap']['status'], 'reported')
        self.assertEqual(report['articles'][1]['status'], 'not_indexed')
        self.assertEqual(call.call_args_list[-1].kwargs['payload']['siteUrl'], m.BASE)
        self.assertNotIn('test-access', json.dumps(report))
        self.assertNotIn('test-refresh', json.dumps(report))

    def test_sitemap_google_errors_and_pending_are_visible_failures(self):
        for response in ({'path': m.SITEMAP, 'errors': '2'}, {'path': m.SITEMAP, 'isPending': True}, {'path': 'unexpected'}):
            with self.subTest(response=response), patch.object(m, 'request', side_effect=[xml(A), {'access_token': 'token'}, response, inspection()]):
                report, code = m.monitor(ENV)
                self.assertEqual(code, 2)
                self.assertEqual(report['articles'][0]['status'], 'indexed')

    def test_api_auth_permission_quota_stops_remaining_requests(self):
        for status in (401, 403, 429):
            with self.subTest(status=status), patch.object(m, 'request', side_effect=[xml(A, B), {'access_token': 'token'}, {'path': m.SITEMAP}, m.MonitorError('http_error', status)]) as call:
                report, code = m.monitor(ENV, sleep=lambda _: None)
                self.assertEqual(code, 2)
                self.assertEqual(call.call_count, 4)
                self.assertEqual([r['status'] for r in report['articles']], ['unverifiable'] * 2)
                self.assertEqual(report['articles'][0]['http_status'], status)

    def test_transient_api_error_classified_and_next_article_still_checked(self):
        with patch.object(m, 'request', side_effect=[xml(A, B), {'access_token': 'token'}, {'path': m.SITEMAP}, m.MonitorError('http_error', 503), inspection()]):
            report, code = m.monitor(ENV, sleep=lambda _: None)
        self.assertEqual(code, 2)
        self.assertEqual([r['status'] for r in report['articles']], ['fetch_error', 'indexed'])

    def test_revoked_refresh_token_is_not_reported_as_connected(self):
        with patch.object(m, 'request', side_effect=[xml(A), m.MonitorError('http_error', 400)]):
            report, code = m.monitor(ENV)
        self.assertEqual(code, 2)
        self.assertEqual(report['authentication'], 'error')
        self.assertEqual(report['articles'][0]['status'], 'unverifiable')

    def test_wrong_scope_fails(self):
        with patch.object(m, 'request', return_value={'access_token': 'token', 'scope': 'openid'}), self.assertRaises(m.MonitorError):
            m.credentials(ENV)

    def test_wrong_property_rejected_before_network(self):
        with patch.object(m, 'request') as call:
            report, code = m.monitor({'GSC_SITE_URL': 'https://other.example/'})
        self.assertEqual(code, 2)
        self.assertEqual(report['error'], 'unsupported_property')
        call.assert_not_called()

    def test_csv_json_summary_saved_with_csv_formula_defense(self):
        result = m.row(A, m.BASE, 'not_indexed', '=HYPERLINK("bad")', last_crawl_time='2026-11-07')
        report = dict(checked_at='2026-11-07', authentication='token_acquired', sitemap={}, google_sitemap={}, articles=[result])
        with tempfile.TemporaryDirectory() as d:
            summary_path = Path(d) / 'step.md'
            m.write_report(report, d, summary_path)
            stored = json.loads((Path(d) / 'index-status.json').read_text())
            self.assertEqual(stored['counts']['not_indexed'], 1)
            with (Path(d) / 'index-status.csv').open(encoding='utf-8-sig') as f:
                csv_row = next(csv.DictReader(f))
            self.assertTrue(csv_row['reason'].startswith("'="))
            self.assertIn(A, summary_path.read_text())
            self.assertIn('未登録：手動検査', summary_path.read_text())
            self.assertNotIn('GSC_CLIENT_SECRET', summary_path.read_text())

    def test_network_failure_retry_and_no_raw_secret_error_body(self):
        private = b'{"error_description":"test-refresh-secret"}'
        error = HTTPError(m.TOKEN, 400, 'bad', {}, BytesIO(private))
        with patch.object(m, 'build_opener') as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(m.MonitorError) as caught:
                m.request(m.TOKEN, form={'refresh_token': 'test-refresh-secret'})
            self.assertNotIn('test-refresh-secret', str(caught.exception))
            self.assertEqual(caught.exception.status, 400)

    def test_429_respects_retry_after_and_retry_bound(self):
        error = HTTPError(m.API, 429, 'quota', {'Retry-After': '3'}, BytesIO(b''))
        with patch.object(m, 'build_opener') as opener, patch.object(m.time, 'sleep') as sleep:
            opener.return_value.open.side_effect = error
            with self.assertRaises(m.MonitorError):
                m.request(m.API)
            self.assertEqual(opener.return_value.open.call_count, 3)
            self.assertEqual(sleep.call_args_list[0].args, (3,))

    def test_redirects_never_forward_credentials(self):
        self.assertIsNone(m.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example/'))

    def test_empty_response_json_rejected(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'[]'
        with patch.object(m, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(m.MonitorError):
                m.request(m.API)

    def test_malformed_google_fields_are_unknown_not_crashes(self):
        for extra in ({'verdict': []}, {'coverageState': {}}, {'lastCrawlTime': 3}):
            response = inspection()
            response['inspectionResult']['indexStatusResult'].update(extra)
            self.assertEqual(m.classify(A, m.BASE, response)['status'], 'unverifiable')
        for value in ('bad', {}):
            with patch.object(m, 'request', side_effect=[xml(A), {'access_token': 'token'}, {'path': m.SITEMAP, 'errors': value}, inspection()]):
                report, code = m.monitor(ENV)
                self.assertEqual(code, 2)

    def test_workflow_is_readonly_secrets_main_only_and_artifacts_always(self):
        text = (Path(__file__).resolve().parents[1] / '.github/workflows/index-monitor.yml').read_text()
        self.assertIn('contents: read', text)
        self.assertNotIn('contents: write', text)
        self.assertNotIn('pull_request_target', text)
        self.assertNotIn('pull_request:', text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn('if: always()', text)
        self.assertIn("cron: '17 23 * * *'", text)
        self.assertIn('persist-credentials: false', text)
        self.assertNotIn('git push', text)
