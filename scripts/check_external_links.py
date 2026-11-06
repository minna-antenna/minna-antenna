"""Read-only GET link audit. Network restrictions/timeouts are not called broken links.

Run explicitly; never part of the scheduled RSS updater. Non-success is never
converted to success. The result certifies reachability only, not source accuracy.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.urls=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and attrs.get('href','').startswith('https://'):
            self.urls.add(attrs['href'])


def classify(status=None,error=None):
    if error:
        if isinstance(error,(ssl.SSLError,ssl.CertificateError)):
            return 'tls_unverified'
        return 'network_unverified'
    if status in (404,410):return 'broken'
    if status in (401,403):return 'access_restricted'
    if status==429 or (status is not None and 500<=status<600):return 'transient_unverified'
    if status is not None and 200<=status<300:return 'reachable'
    return 'http_unverified'


def decode_html(body,content_type):
    # NTA error pages may use Shift_JIS even when the requested content uses UTF-8.
    declarations=re.findall(r'charset=["\']?([\w-]+)',content_type,re.I)
    declarations+=re.findall(br'charset=["\']?([\w-]+)',body[:4096],re.I)
    for encoding in declarations+['utf-8','cp932']:
        if isinstance(encoding,bytes):encoding=encoding.decode('ascii')
        try:return body.decode(encoding)
        except (UnicodeDecodeError,LookupError):continue
    return body.decode('utf-8',errors='replace')


def body_problem(url,body,content_type):
    if not body:return 'empty_response'
    if 'html' in content_type.lower() or b'<html' in body[:1024].lower():
        text=decode_html(body,content_type)
        title=re.search(r'<title\b[^>]*>(.*?)</title>',text,re.S|re.I)
        heading=title[1] if title else ''
        if re.search(r'page not found|指定されたページを表示できませんでした|ページが見つかりません',heading,re.I):
            return 'soft_not_found_page'
        if re.search(r'access denied|forbidden|captcha|verify you are human|アクセスが拒否|アクセス制限|認証が必要',heading,re.I):
            return 'soft_access_restriction'
    if urlsplit(url).path.lower().endswith('.pdf') and not body.startswith(b'%PDF'):
        return 'expected_pdf_not_received'
    return None


def check(url,*,opener=urlopen,attempt_limit=3,timeout=20,sleeper=time.sleep):
    attempts=[];result={'url':url,'checked_at_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    for index in range(attempt_limit):
        try:
            with opener(Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html,application/pdf;q=0.9,*/*;q=0.8'}),timeout=timeout) as response:
                body=response.read();status=response.status;ctype=response.headers.get('Content-Type','')
                category=classify(status)
                problem=body_problem(url,body,ctype)
                if category=='reachable' and problem:
                    category={'soft_not_found_page':'soft_404','soft_access_restriction':'access_restricted'}.get(problem,'content_unverified')
                result.update(status=status,final_url=response.url,redirected=response.url!=url,classification=category,content_type=ctype,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
                if problem:result['content_problem']=problem
        except HTTPError as exc:
            category=classify(exc.code)
            result.update(status=exc.code,classification=category)
        except (URLError,TimeoutError,OSError) as exc:
            cause=exc.reason if isinstance(exc,URLError) else exc
            category=classify(error=cause)
            # Keep error types only; exception text may contain signed URLs or proxy credentials.
            result.update(status=None,classification=category,error_type=type(cause).__name__)
        attempts.append({'number':index+1,'status':result.get('status'),'classification':category})
        if category not in ('transient_unverified','network_unverified') or index+1==attempt_limit:break
        sleeper(index+1)
    result['attempts']=attempts
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--article',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();links=Links();links.feed(a.article.read_text(encoding='utf-8'))
    if not links.urls:raise SystemExit('No external source links found')
    with ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(check,sorted(links.urls)))
    counts={}
    for row in results:counts[row['classification']]=counts.get(row['classification'],0)+1
    payload={'scope':a.article.relative_to(ROOT).as_posix() if a.article.is_relative_to(ROOT) else str(a.article),
             'method':'HTTP GET; follow redirects; retry network errors, 429 and 5xx up to 3 attempts; distinguish restrictions and TLS; no content correctness certification',
             'all_reachable':all(r['classification']=='reachable' for r in results),'counts':counts,'links':results}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'counts':counts,'all_reachable':payload['all_reachable']},ensure_ascii=False))
    for row in results:print(row.get('status'),row['classification'],row['url'])
    raise SystemExit(0 if payload['all_reachable'] else 1)


if __name__=='__main__':main()
