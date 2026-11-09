"""Read-only live technical audit, independently enumerated from repository articles."""
import argparse
import csv
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, quote
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
import monitor_indexing as gsc

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, source=''):
        super().__init__(convert_charrefs=True)
        self.canonicals, self.links, self.robots, self.descriptions, self.titles = [], [], [], [], []
        self.in_title = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title':
            self.in_title = True
            self.titles.append('')
        if tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonicals.append(a.get('href', ''))
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])
        if tag == 'meta':
            name = a.get('name', '').lower()
            if name in ('robots', 'googlebot'):
                self.robots.append(a.get('content', ''))
            if name == 'description':
                self.descriptions.append(a.get('content', ''))

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.titles[-1] += data


def fetch(url):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'TopicBase-TechnicalAudit/1.0'}), timeout=30) as r:
            raw = r.read(5_000_001)
            if len(raw) > 5_000_000:
                return dict(status=r.status, final_url=r.url, error='response_too_large', text='', headers={})
            return dict(status=r.status, final_url=r.url, error='', text=raw.decode('utf-8-sig', errors='replace'), headers=dict(r.headers))
    except HTTPError as e:
        return dict(status=e.code, final_url=url, error='http_error', text='', headers={})
    except (URLError, TimeoutError, OSError):
        return dict(status=None, final_url=url, error='network_error', text='', headers={})


def sitemap_urls(source):
    if '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper():
        raise ValueError('unsafe_xml')
    tree = ET.fromstring(source)
    ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    if tree.tag != ns + 'urlset':
        raise ValueError('unsupported_sitemap_type')
    urls = []
    for node in tree.findall(ns + 'url'):
        loc = node.find(ns + 'loc')
        if loc is None or not loc.text or not loc.text.startswith(gsc.BASE):
            raise ValueError('invalid_loc')
        urls.append(loc.text.strip())
    if len(urls) != len(set(urls)):
        raise ValueError('duplicate_loc')
    return urls


def diagnose(root=ROOT):
    paths = sorted((root / 'articles').glob('*.html'))
    urls = [gsc.BASE + p.relative_to(root).as_posix() for p in paths]
    if not urls or len(urls) > gsc.MAX_URLS:
        raise ValueError('invalid_article_count')
    report = dict(checked_at=dt.datetime.now(dt.timezone.utc).isoformat(), expected_count=len(urls),
                  authentication='not_configured', articles=[], sitemap={}, robots={})
    sm = fetch(gsc.SITEMAP)
    try:
        if sm['status'] != 200:
            raise ValueError('sitemap_fetch_failed')
        locations = sitemap_urls(sm['text'])
        report['sitemap'] = dict(http_status=sm['status'], valid_xml=True, missing=sorted(set(urls)-set(locations)), total=len(locations))
    except (ValueError, ET.ParseError) as e:
        locations = None
        report['sitemap'] = dict(http_status=sm['status'], valid_xml=False, error=str(e))
    rb_url = 'https://minna-antenna.github.io/robots.txt'
    rb = fetch(rb_url)  # Only origin-root robots.txt governs Google crawling.
    rp = RobotFileParser()
    if rb['status'] == 200:
        rp.parse(rb['text'].splitlines())
    report['robots'] = dict(url=rb_url, http_status=rb['status'], error=rb['error'], project_file=fetch(gsc.BASE+'robots.txt'))
    pages = {gsc.BASE: fetch(gsc.BASE)}
    for url in urls:
        pages[url] = fetch(url)
    # Include all repository HTML as potential inbound sources, but verify each source live.
    for p in sorted(root.glob('*.html')):
        url = gsc.BASE + quote(p.name)
        if url not in pages:
            pages[url] = fetch(url)
    parsed = {url: Page(data['text']) for url, data in pages.items()}
    try:
        local_locations = sitemap_urls((root / 'sitemap.xml').read_text(encoding='utf-8'))
        report['local_sitemap'] = dict(valid_xml=True, missing=sorted(set(urls)-set(local_locations)), total=len(local_locations))
    except (OSError, ValueError, ET.ParseError) as e:
        report['local_sitemap'] = dict(valid_xml=False, error=type(e).__name__)
    link_results = {}
    for article_url in urls:
        for href in parsed[article_url].links:
            target = urljoin(pages[article_url]['final_url'], href).split('#')[0]
            if urlsplit(target).netloc == urlsplit(gsc.BASE).netloc and target not in link_results:
                response = pages.get(target)
                if response is None:
                    response = fetch(target)
                link_results[target] = {k: response[k] for k in ('status', 'final_url', 'error')}
    token = None
    site = os.environ.get('GSC_SITE_URL') or gsc.BASE
    if site not in (gsc.BASE, 'https://minna-antenna.github.io/', 'sc-domain:minna-antenna.github.io'):
        report['authentication'] = 'unsupported_property'
    else:
        try:
            token = gsc.credentials(os.environ)
            report['authentication'] = 'token_acquired'
        except gsc.MonitorError as e:
            report['authentication'] = e.code
    for url in urls:
        data, page = pages[url], parsed[url]
        issues = []
        if data['status'] != 200:
            issues.append('HTTP取得失敗')
        if data['final_url'] != url:
            issues.append('リダイレクトあり')
        if page.canonicals != [url]:
            issues.append('canonical欠落・重複・不一致')
        if len(page.titles) != 1 or not page.titles[0].strip():
            issues.append('title欠落・重複')
        if len(page.descriptions) != 1 or not page.descriptions[0].strip():
            issues.append('description欠落・重複')
        headers = {k.lower(): v for k, v in data['headers'].items()}
        directives = ','.join(page.robots + [headers.get('x-robots-tag', '')]).lower()
        if any(x in directives.replace(',', ' ').split() for x in ('noindex', 'none')):
            issues.append('noindex指定あり（適用エージェント要確認）')
        allowed = rp.can_fetch('Googlebot', url) if rb['status'] == 200 else (True if rb['status'] and 400 <= rb['status'] < 500 and rb['status'] != 429 else None)
        if allowed is not True:
            issues.append('robots.txt拒否または取得不明')
        inbound = [src for src, doc in parsed.items() if src != url and pages[src]['status'] == 200 and url in {urljoin(pages[src]['final_url'], link).split('#')[0] for link in doc.links}]
        if not inbound:
            issues.append('検査対象内に内部被リンクなし')
        internal_checks = {target: result for target, result in link_results.items() if target in {urljoin(data['final_url'], href).split('#')[0] for href in page.links}}
        if any(v['status'] != 200 for v in internal_checks.values()):
            issues.append('内部リンク先の取得失敗')
        if any(len(peers) > 1 and url in peers for peers in ([u for u in urls if parsed[u].titles == page.titles], [u for u in urls if parsed[u].descriptions == page.descriptions])):
            issues.append('記事間でtitleまたはdescription重複')
        in_sitemap = url in locations if locations is not None else None
        if in_sitemap is not True:
            issues.append('サイトマップ未掲載または検証不可')
        inspection = gsc.row(url, site, reason=report['authentication'])
        if token:
            try:
                inspection = gsc.classify(url, site, gsc.request(gsc.API, token=token, payload=dict(inspectionUrl=url, siteUrl=site, languageCode='ja-JP')))
            except gsc.MonitorError as e:
                inspection = gsc.row(url, site, 'fetch_error', e.code, http_status=e.status)
                if e.status in (401, 403, 429):
                    token = None
                    report['authentication'] = 'api_authorization_or_quota_error'
            time.sleep(.25)
        status = {'indexed':'登録済み', 'not_indexed':'未登録', 'fetch_error':'取得不可', 'unverifiable':'要確認'}[inspection['status']]
        if data['status'] != 200 and status == '要確認':
            status = '取得不可'
        report['articles'].append(dict(url=url, status=status, http_status=data['status'], final_url=data['final_url'],
            canonical=page.canonicals, robots_meta=page.robots, x_robots_tag=headers.get('x-robots-tag', ''), robots_allowed=allowed,
            title=page.titles, description=page.descriptions, inbound_sources=inbound,
            internal_links=sorted({urljoin(url, l).split('#')[0] for l in page.links if urlsplit(urljoin(url,l)).netloc == urlsplit(url).netloc}),
            internal_link_checks=internal_checks, in_sitemap=in_sitemap, issues=issues, google=inspection))
    report['counts'] = {s: sum(r['status']==s for r in report['articles']) for s in ('登録済み','未登録','取得不可','要確認')}
    return report


def write(report, output):
    output.mkdir(parents=True, exist_ok=True)
    (output/'diagnosis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    (output/'urls.txt').write_text(''.join(r['url']+'\n' for r in report['articles']))
    fields = ['url','status','http_status','final_url','canonical','robots_meta','x_robots_tag','robots_allowed','title','description','inbound_sources','internal_links','internal_link_checks','in_sitemap','issues','google']
    with (output/'diagnosis.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        for row in report['articles']:
            w.writerow({k:gsc.csv_safe(json.dumps(row[k], ensure_ascii=False) if isinstance(row[k], (list,dict)) else str(row[k]) if row[k] is not None else '') for k in fields})
    esc = lambda v: html.escape(str(v))
    headings = ['記事URL', '分類', 'HTTP', '技術的問題', '内部被リンク数', 'サイトマップ', '詳細']
    rows = ''
    for r in report['articles']:
        values = [r['url'], r['status'], r['http_status'], ' / '.join(r['issues']) or '検出なし', len(r['inbound_sources']), '掲載' if r['in_sitemap'] else '未掲載または不明']
        rows += '<tr>' + ''.join('<td>' + esc(v) + '</td>' for v in values)
        rows += '<td><details><summary>検査値を見る</summary><pre>' + esc(json.dumps(r, ensure_ascii=False, indent=2)) + '</pre></details></td></tr>'
    content = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>トピック基地 インデックス診断</title><style>body{font:15px sans-serif;margin:24px;color:#172b40}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:8px;min-width:120px;vertical-align:top}td{overflow-wrap:anywhere;max-width:450px}th:first-child,td:first-child{min-width:280px}pre{white-space:pre-wrap;max-width:500px;font-size:12px}details[open]{min-width:400px}.scroll{overflow:auto}</style><h1>トピック基地 インデックス診断</h1>'
    content += '<p>確認日時 UTC: '+esc(report['checked_at'])+'</p><p>'+esc(report['counts'])+'</p><p>認証: '+esc(report['authentication'])+'</p><p>サイトマップ: '+esc(report['sitemap'])+'</p><p>ローカルサイトマップ: '+esc(report['local_sitemap'])+'</p><p>robots.txt（origin直下）: '+esc({k:v for k,v in report['robots'].items() if k!='project_file'})+'</p><p>origin直下robots.txtの404はクロール許可扱いです。プロジェクト配下robots.txtはGoogleの制御対象になりません。</p><p>HTTP 200や技術検査の合格はGoogleへの登録を意味しません。認証なしは要確認。登録・順位は保証しません。APIは既存情報の照会のみです。</p><p><a href="'+esc(gsc.manual_link(gsc.BASE))+'">Search Consoleを開く</a> → 各行のURLを上部のURL検査欄に貼り付けて確認してください。</p><div class="scroll"><table><thead><tr>'+''.join('<th>'+k+'</th>' for k in headings)+'</tr></thead><tbody>'+rows+'</tbody></table></div></html>'
    (output/'diagnosis.html').write_text(content, encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=Path('monitoring-output'))
    args = p.parse_args()
    report = diagnose()
    write(report, args.output)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with Path(summary).open('a', encoding='utf-8') as f:
            f.write('## 記事インデックス一括診断\n\n確認日時 UTC: ' + report['checked_at'] + '\n\n' + json.dumps(report['counts'], ensure_ascii=False) + '\n\n認証: ' + report['authentication'] + '\n\n詳細はartifactの diagnosis.html / diagnosis.csv / urls.txt を確認してください。登録や順位は保証しません。\n')
    print(json.dumps({k:report[k] for k in ('checked_at','counts','authentication','sitemap')}, ensure_ascii=False))
    return 2 if not report['local_sitemap']['valid_xml'] or report['local_sitemap'].get('missing') or not report['sitemap']['valid_xml'] or report['sitemap'].get('missing') or any(r['issues'] or r['status'] in ('取得不可','要確認') for r in report['articles']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
