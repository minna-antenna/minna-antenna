"""Read-only Search Console monitor; standard library, no indexing submission."""
import argparse
import csv
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET

BASE = 'https://topic-kichi.com/'
SITEMAP = BASE + 'sitemap.xml'
SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
API = 'https://searchconsole.googleapis.com/v1/urlInspection/index:inspect'
TOKEN = 'https://oauth2.googleapis.com/token'
MAX_URLS = 200  # Stop visibly rather than silently sampling; below 2,000/site/day.
FIELDS = ['url', 'status', 'reason', 'verdict', 'last_crawl_time', 'page_fetch_state',
          'indexing_state', 'robots_txt_state', 'google_canonical', 'user_canonical',
          'inspection_link', 'http_status', 'error_code']
LABELS = {'indexed': '登録済み', 'not_indexed': '未登録',
          'fetch_error': '取得エラー', 'unverifiable': '確認不能'}


class MonitorError(Exception):
    def __init__(self, code, status=None):
        super().__init__(code)
        self.code, self.status = code, status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward OAuth credentials or bearer tokens to redirects.


def request(url, *, form=None, payload=None, token=None, json_result=True):
    data = None
    headers = {'User-Agent': 'TopicBase-IndexMonitor/1.0', 'Accept': 'application/json'}
    if form is not None:
        data = urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    for attempt in range(3):
        try:
            with build_opener(NoRedirect()).open(Request(url, data=data, headers=headers), timeout=30) as response:
                raw = response.read(5_000_001)
                if len(raw) > 5_000_000:
                    raise MonitorError('response_too_large')
                if not json_result:
                    return raw
                try:
                    result = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise MonitorError('invalid_json') from None
                if not isinstance(result, dict):
                    raise MonitorError('invalid_json_shape')
                return result
        except HTTPError as exc:
            status = exc.code
            # Do not output response bodies: OAuth errors may contain sensitive data.
            retry = status == 429 or 500 <= status < 600
            delay = exc.headers.get('Retry-After', '')
            seconds = int(delay) if delay.isdigit() else 2 ** attempt
            if retry and attempt < 2 and seconds <= 60:
                time.sleep(seconds)
                continue
            raise MonitorError('http_error', status) from None
        except (URLError, TimeoutError, OSError):
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise MonitorError('network_error') from None


def article_urls(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise MonitorError('unsafe_xml')
    try:
        tree = ET.fromstring(raw)
    except ET.ParseError:
        raise MonitorError('invalid_sitemap_xml') from None
    if tree.tag != '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset':
        raise MonitorError('unsupported_sitemap_type')
    urls = set()
    for loc in tree.findall('{*}url/{*}loc'):
        url = (loc.text or '').strip()
        parsed = urlsplit(url)
        if (url.startswith(BASE + 'articles/') and parsed.scheme == 'https'
                and parsed.netloc == urlsplit(BASE).netloc
                and parsed.path.endswith('.html') and not parsed.query and not parsed.fragment
                and not re.search(r'(^|/)(\.|\.\.)(/|$)', parsed.path)
                and not re.search(r'%2e|%2f|%5c', parsed.path, re.I)):
            urls.add(url)
    if not urls:
        raise MonitorError('no_article_urls')
    return sorted(urls)


def manual_link(site):
    # No undocumented URL-to-inspect parameter: paste the listed article URL in the UI.
    return 'https://search.google.com/search-console?resource_id=' + quote(site, safe='')


def row(url, site, status='unverifiable', reason='', **values):
    result = dict.fromkeys(FIELDS, '')
    result.update(url=url, status=status, reason=reason, inspection_link=manual_link(site))
    result.update(values)
    return result


def classify(url, site, response):
    inspection = response.get('inspectionResult')
    if not isinstance(inspection, dict) or not isinstance(inspection.get('indexStatusResult'), dict):
        return row(url, site, reason='missing_index_status', error_code='missing_index_status')
    item = inspection['indexStatusResult']
    if any(not isinstance(item.get(k, ''), str) for k in ('verdict', 'coverageState', 'lastCrawlTime', 'pageFetchState', 'indexingState', 'robotsTxtState', 'googleCanonical', 'userCanonical')):
        return row(url, site, reason='invalid_index_status_shape', error_code='invalid_index_status_shape')
    verdict = item.get('verdict', '')
    status = {'PASS': 'indexed', 'FAIL': 'not_indexed', 'NEUTRAL': 'not_indexed'}.get(verdict, 'unverifiable')
    result = row(url, site, status, item.get('coverageState', ''), verdict=verdict,
                 last_crawl_time=item.get('lastCrawlTime', ''), page_fetch_state=item.get('pageFetchState', ''),
                 indexing_state=item.get('indexingState', ''), robots_txt_state=item.get('robotsTxtState', ''),
                 google_canonical=item.get('googleCanonical', ''), user_canonical=item.get('userCanonical', ''))
    link = inspection.get('inspectionResultLink', '')
    parsed = urlsplit(link) if isinstance(link, str) else urlsplit('')
    if parsed.scheme == 'https' and parsed.netloc == 'search.google.com':
        result['inspection_link'] = link.replace('(', '%28').replace(')', '%29')
    return result


def credentials(env):
    keys = ('GSC_CLIENT_ID', 'GSC_CLIENT_SECRET', 'GSC_REFRESH_TOKEN')
    if not all(env.get(k, '').strip() for k in keys):
        raise MonitorError('authentication_not_configured')
    response = request(TOKEN, form=dict(client_id=env[keys[0]], client_secret=env[keys[1]],
                                       refresh_token=env[keys[2]], grant_type='refresh_token'))
    token = response.get('access_token')
    if not isinstance(token, str) or not token or '\n' in token or '\r' in token:
        raise MonitorError('missing_access_token')
    scopes = response.get('scope')
    if scopes is not None and (not isinstance(scopes, str) or (SCOPE not in scopes.split() and 'https://www.googleapis.com/auth/webmasters' not in scopes.split())):
        raise MonitorError('missing_readonly_scope')
    return token  # Never persist token or raw OAuth responses.


def monitor(env=None, sleep=time.sleep):
    env = os.environ if env is None else env
    site = env.get('GSC_SITE_URL') or BASE
    report = dict(checked_at=dt.datetime.now(dt.timezone.utc).isoformat(), site_url=site,
                  sitemap_url=SITEMAP, authentication='not_attempted', sitemap={}, google_sitemap={}, articles=[])
    if site not in (BASE, 'sc-domain:topic-kichi.com'):
        report['error'] = 'unsupported_property'
        return report, 2
    try:
        urls = article_urls(request(SITEMAP, json_result=False))
        report['sitemap'] = dict(status='ok', article_count=len(urls), http_status=200)
    except MonitorError as exc:
        report['sitemap'] = dict(status='error', error_code=exc.code, http_status=exc.status)
        return report, 2
    if len(urls) > MAX_URLS:
        report['error'] = 'daily_safety_limit_exceeded'
        report['articles'] = [row(u, site, reason='daily_safety_limit_exceeded') for u in urls]
        return report, 2
    try:
        token = credentials(env)
    except MonitorError as exc:
        report['authentication'] = 'not_configured' if exc.code == 'authentication_not_configured' else 'error'
        report['auth_error'] = dict(error_code=exc.code, http_status=exc.status)
        report['google_sitemap'] = dict(status='unverifiable', error_code='authentication_unavailable')
        report['articles'] = [row(u, site, reason='authentication_unavailable', error_code=exc.code) for u in urls]
        return report, 2
    report['authentication'] = 'token_acquired'  # Property access not established yet.
    endpoint = 'https://www.googleapis.com/webmasters/v3/sites/' + quote(site, safe='') + '/sitemaps/' + quote(SITEMAP, safe='')
    failed = False
    try:
        response = request(endpoint, token=token)
        if response.get('path') != SITEMAP:
            raise MonitorError('unexpected_sitemap_response')
        error_value = response.get('errors', 0)
        if not isinstance(error_value, (str, int)) or isinstance(error_value, bool):
            raise MonitorError('invalid_sitemap_errors')
        try:
            errors = int(error_value)
        except (ValueError, TypeError):
            raise MonitorError('invalid_sitemap_errors') from None
        if errors < 0:
            raise MonitorError('invalid_sitemap_errors')
        if not isinstance(response.get('isPending', False), bool):
            raise MonitorError('invalid_sitemap_pending')
        report['google_sitemap'] = {k: response.get(k) for k in
                                    ('path', 'lastSubmitted', 'lastDownloaded', 'isPending', 'errors', 'warnings', 'contents')}
        report['google_sitemap']['status'] = 'reported'
        # Google pending/error is distinct from our HTTP retrieval succeeding.
        if response.get('isPending') or errors > 0:
            failed = True
    except MonitorError as exc:
        report['google_sitemap'] = dict(status='error', http_status=exc.status, error_code=exc.code)
        failed = True
    blocked = None
    for i, url in enumerate(urls):
        if blocked:
            report['articles'].append(row(url, site, reason='run_stopped_after_api_error', error_code=blocked))
            continue
        if i:
            sleep(.25)
        try:
            response = request(API, token=token, payload=dict(inspectionUrl=url, siteUrl=site, languageCode='ja-JP'))
            result = classify(url, site, response)
            report['articles'].append(result)
            if result['status'] == 'unverifiable':
                failed = True
        except MonitorError as exc:
            status = 'unverifiable' if exc.status in (401, 403, 429) else 'fetch_error'
            report['articles'].append(row(url, site, status, 'api_request_failed', http_status=exc.status, error_code=exc.code))
            failed = True
            if exc.status in (401, 403, 429):
                blocked = 'authorization_or_quota_error'
    return report, 2 if failed else 0


def csv_safe(value):
    text = str(value or '')
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def write_report(report, output, summary_path=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = report['articles']
    report['counts'] = {key: sum(r['status'] == key for r in rows) for key in LABELS}
    (output / 'index-status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (output / 'index-status.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, FIELDS)
        writer.writeheader()
        writer.writerows({k: csv_safe(r[k]) for k in FIELDS} for r in rows)
    def safe(value):
        return html.escape(str(value or '')).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Googleインデックス監視', '', f"確認日時（UTC）: {report['checked_at']}",
             f"認証: {report['authentication']} / 診断: {safe(report.get('auth_error', {}))}", f"サイトマップHTTP取得: {safe(report['sitemap'])}",
             f"Google側サイトマップ報告: {safe(report['google_sitemap'])}", '',
             ' / '.join(f'{LABELS[k]}: {v}' for k, v in report['counts'].items()), '',
             'APIはGoogle保有情報の照会のみ。ライブ検査・登録申請・Indexing APIは実行しません。', '',
             '| 記事URL（手動検査時にコピー） | 状態 | Googleの理由／診断 | 最終クロール | 検査画面 |',
             '|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {safe(r['url'])} | {LABELS[r['status']]} | {safe(r['reason'] or r['error_code'])} | {safe(r['last_crawl_time'])} | [Search Console]({r['inspection_link']}) |")
    lines += ['', '## 未登録：手動検査・登録申請候補', '',
              '下記URLをSearch Console上部のURL検査欄に貼り付け、権限・理由を確認して手動で申請してください。']
    lines += ['- ' + r['url'] for r in rows if r['status'] == 'not_indexed'] or ['- 今回の未登録判定なし。確認不能は登録済みを意味しません。']
    if report.get('error'):
        lines += ['', '実行診断: ' + safe(report['error'])]
    summary = '\n'.join(lines) + '\n'
    (output / 'summary.md').write_text(summary, encoding='utf-8')
    if summary_path:
        with Path(summary_path).open('a', encoding='utf-8') as f:
            f.write(summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='monitoring-output')
    args = parser.parse_args()
    report, code = monitor()
    write_report(report, args.output, os.environ.get('GITHUB_STEP_SUMMARY'))
    print(json.dumps(dict(authentication=report['authentication'], sitemap=report['sitemap'], counts=report['counts']), ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
