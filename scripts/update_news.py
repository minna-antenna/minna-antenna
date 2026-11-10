#!/usr/bin/env python3
"""Retrieve public RSS metadata and rank news candidates; no scraping article bodies."""
import tempfile
import unicodedata
import argparse, datetime as dt, hashlib, json, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

JST=dt.timezone(dt.timedelta(hours=9))
FEEDS = [{'name': 'NHK総合',
  'provider': 'NHK',
  'publisher_id': 'nhk',
  'category': 'ニュース',
  'url': 'https://www.nhk.or.jp/rss/news/cat0.xml'},
 {'name': 'NHK社会',
  'provider': 'NHK',
  'publisher_id': 'nhk',
  'category': 'ニュース',
  'url': 'https://www.nhk.or.jp/rss/news/cat1.xml'},
 {'name': 'BBC News 日本語',
  'provider': 'BBC',
  'publisher_id': 'bbc',
  'category': 'アジア・翻訳',
  'url': 'https://feeds.bbci.co.uk/japanese/rss.xml'},
 {'name': 'Google ニュース・ゲーム',
  'provider': 'Google News',
  'publisher_id': None,
  'category': 'ゲーム',
  'url': 'https://news.google.com/rss/search?q=%E3%82%B2%E3%83%BC%E3%83%A0%20%E6%96%B0%E4%BD%9C%20OR%20%E4%BB%BB%E5%A4%A9%E5%A0%82%20OR%20PlayStation&hl=ja&gl=JP&ceid=JP:ja'},
 {'name': 'Google ニュース・アニメ',
  'provider': 'Google News',
  'publisher_id': None,
  'category': 'アニメ',
  'url': 'https://news.google.com/rss/search?q=%E3%82%A2%E3%83%8B%E3%83%A1%20%E6%96%B0%E4%BD%9C%20OR%20%E5%A3%B0%E5%84%AA%20OR%20%E5%8A%87%E5%A0%B4%E7%89%88&hl=ja&gl=JP&ceid=JP:ja'},
 {'name': 'Google ニュース・車',
  'provider': 'Google News',
  'publisher_id': None,
  'category': '車・バイク',
  'url': 'https://news.google.com/rss/search?q=%E8%87%AA%E5%8B%95%E8%BB%8A%20OR%20%E3%83%9B%E3%83%B3%E3%83%80%20OR%20%E3%83%88%E3%83%A8%E3%82%BF%20OR%20EV&hl=ja&gl=JP&ceid=JP:ja'},
 {'name': 'Google ニュース・株',
  'provider': 'Google News',
  'publisher_id': None,
  'category': '株・投資',
  'url': 'https://news.google.com/rss/search?q=%E6%97%A5%E6%9C%AC%E6%A0%AA%20OR%20%E6%B1%BA%E7%AE%97%20OR%20%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87&hl=ja&gl=JP&ceid=JP:ja'},
 {'name': 'Google ニュース・仮想通貨',
  'provider': 'Google News',
  'publisher_id': None,
  'category': '仮想通貨',
  'url': 'https://news.google.com/rss/search?q=%E3%83%93%E3%83%83%E3%83%88%E3%82%B3%E3%82%A4%E3%83%B3%20OR%20%E4%BB%AE%E6%83%B3%E9%80%9A%E8%B2%A8&hl=ja&gl=JP&ceid=JP:ja'},
 {'name': 'Google ニュース・政治',
  'provider': 'Google News',
  'publisher_id': None,
  'category': '政治・経済',
  'url': 'https://news.google.com/rss/search?q=%E6%94%BF%E5%BA%9C%20OR%20%E5%9B%BD%E4%BC%9A%20OR%20%E6%97%A5%E9%8A%80&hl=ja&gl=JP&ceid=JP:ja'},
 {'name': 'Google ニュース・スポーツ',
  'provider': 'Google News',
  'publisher_id': None,
  'category': 'スポーツ',
  'url': 'https://news.google.com/rss/search?q=%E9%87%8E%E7%90%83%20OR%20%E3%82%B5%E3%83%83%E3%82%AB%E3%83%BC%20OR%20%E3%82%B9%E3%83%9D%E3%83%BC%E3%83%84&hl=ja&gl=JP&ceid=JP:ja'}]
PUBLISHERS = {
 'nhk': {'name': 'NHK', 'aliases': ('NHK', 'NHK総合', 'NHK社会', 'NHKニュース', 'NHK NEWS WEB'), 'hosts': ('nhk.or.jp', 'news.web.nhk')},
 'bbc': {'name': 'BBC', 'aliases': ('BBC', 'BBC News', 'BBC News 日本語', 'BBCニュース'), 'hosts': ('bbc.com', 'bbc.co.uk')},
}
SCORING_RULE = '新しさ0〜60点（72時間で減衰）＋正規化した同一見出しを掲載した、設定で識別済みの発行主体1追加につき15点（最大30点）。同一主体の複数フィードは加点しません。未識別の発行元は加点対象外。内容の正しさ・独立取材・PV・SNS人気の評価ではありません。'


def publisher_identity(label, source_url=''):
 # Only explicitly mapped identities count. A hostname is not a verified corporate group.
 original_label=label.strip()
 label = unicodedata.normalize('NFKC', label).strip().casefold()
 host = (urllib.parse.urlsplit(source_url).hostname or '').lower()
 for pid, info in PUBLISHERS.items():
  if host:
   if any(host == h or host.endswith('.'+h) for h in info['hosts']):
    return pid, info['name']
  elif label in {unicodedata.normalize('NFKC', a).casefold() for a in info['aliases']}:
   return pid, info['name']
 return None, original_label or '発行元未記載'

USER_AGENT='MinnaAntennaDemo/1.0 RSS metadata fetcher (+manual browser links)'

def parse_date(s):
 try:
  d=parsedate_to_datetime(s)
 except Exception:
  try:d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
  except Exception:return None
 if not d.tzinfo:d=d.replace(tzinfo=dt.timezone.utc)
 return d.astimezone(dt.timezone.utc)

def text(node, tag):
 x=node.find(tag)
 return (x.text or '').strip() if x is not None else ''

def parse_rss(raw, source, category, now):
 root=ET.fromstring(raw)
 config=next((f for f in FEEDS if f['name']==source), {})
 records=[]
 for item in root.findall('.//item'):
  title=text(item,'title'); url=text(item,'link'); pub=parse_date(text(item,'pubDate'))
  if not title or not url or not pub or urllib.parse.urlsplit(url).scheme not in ('https','http'):continue
  age=(now-pub).total_seconds()/3600
  if age < -3 or age > 72:continue
  original=title
  source_node=item.find('source')
  source_url=source_node.get('url','') if source_node is not None else ''
  label=source
  if source.startswith('Google ニュース'):
   label=text(item,'source')
   if ' - ' in title:
    headline,suffix=title.rsplit(' - ',1)
    if not label or label==suffix.strip():
     title=headline;label=label or suffix.strip()
   label=label or '発行元未記載'
  pid,publisher=publisher_identity(label,source_url)
  if config.get('publisher_id'):
   pid=config['publisher_id'];publisher=PUBLISHERS[pid]['name']
  records.append(dict(title=title.strip(),url=url,source=label,feed=source,
   provider=config.get('provider',source),publisher_id=pid,publisher=publisher,
   publisher_identification='configured' if pid else 'unidentified',source_url=source_url,
   category=category,published_at=pub.isoformat().replace('+00:00','Z'),
   age_hours=round(max(0,age),1),original_title=original))
 return records


def normalize(s):
 # Retain bracketed words and the full title to avoid unrelated headline collisions.
 return re.sub(r'\s+|[\W_]+','',unicodedata.normalize('NFKC',s),flags=re.UNICODE).casefold()


def build(feeds,now):
 grouped={}
 for x in feeds:
  key=normalize(x['title'])
  if key:grouped.setdefault(key,[]).append(x)
 scored=[]
 for group in grouped.values():
  lead=min(group,key=lambda x:x['age_hours'])
  age=lead['age_hours'];freshness=max(0,round(60*(1-min(age,72)/72)))
  publishers={x['publisher_id']:x['publisher'] for x in group if x.get('publisher_id')}
  multi=min(30,max(0,len(publishers)-1)*15)
  key=hashlib.sha1((normalize(lead['title'])+lead['url']).encode()).hexdigest()[:14]
  reason=dict(freshness_points=freshness,additional_publisher_points=multi,age_hours=age,
   identified_publisher_count=len(publishers),publishers=[dict(id=k,name=v) for k,v in sorted(publishers.items())],
   feed_names=sorted({x['feed'] for x in group}),
   unidentified_source_names=sorted({x['source'] for x in group if not x.get('publisher_id')}),
   scoring_rule=SCORING_RULE)
  item={k:v for k,v in lead.items() if k not in ('age_hours','original_title')}
  item.update(id=key,score=freshness+multi,scoring_version=2,reason=reason)
  scored.append(item)
 scored.sort(key=lambda x:x['published_at'],reverse=True)
 scored.sort(key=lambda x:x['score'],reverse=True)
 counts={};selected=[]
 for item in scored:
  cat=item['category']
  if counts.get(cat,0)>=10:continue
  selected.append(item);counts[cat]=counts.get(cat,0)+1
  if len(selected)>=60:break
 return selected

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fixtures',help='directory of example .xml feeds for offline testing');ap.add_argument('--output',default='data/news.json');args=ap.parse_args()
 now=dt.datetime.now(dt.timezone.utc); all_items=[]; success=[]; errors=[]
 for i,feed in enumerate(FEEDS):
  name,category,url=feed['name'],feed['category'],feed['url']
  try:
   if args.fixtures:
    p=Path(args.fixtures)/f'{i}.xml'
    if not p.exists():continue
    raw=p.read_bytes()
   else:
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml, application/xml;q=0.9'})
    with urllib.request.urlopen(req,timeout=18) as response:raw=response.read(2_000_000)
   entries=parse_rss(raw,name,category,now);all_items.extend(entries)
   success.append(dict(name=name,provider=feed['provider'],publisher_id=feed['publisher_id'],url=url,count=len(entries)))
  except Exception as e:errors.append(dict(feed=name,error=str(e)[:180]))
 out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
 # If all feeds unavailable, keep prior valid items (clearly mark as stale).
 previous={}
 if out.exists():
  try:previous=json.loads(out.read_text(encoding='utf-8'))
  except Exception:pass
 candidate=build(all_items,now) if success else []
 # An empty/invalid RSS response must not wipe the last usable snapshot.
 usable=bool(candidate)
 if not usable:
  errors.append(dict(feed='all',error='No usable recent news; previous snapshot retained'))
 items=candidate if usable else previous.get('articles',[])
 # Preserve news from failed feeds while replacing successful feeds normally.
 failed={e['feed'] for e in errors}
 known={x.get('url') for x in items}
 if usable:
  items += [x for x in previous.get('articles',[]) if x.get('feed') in failed and x.get('url') not in known]
 output=dict(schema_version=2,generated_at=now.isoformat().replace('+00:00','Z') if usable else previous.get('generated_at'),last_attempt_at=now.isoformat().replace('+00:00','Z'),status='ok' if usable and not errors else ('partial' if usable else 'error'),method=SCORING_RULE+' 取得失敗時は以前のデータを保持します。旧方式の保存データは再採点前として区別します。',feed_success=success,feed_errors=errors,articles=items)
 with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=out.parent,delete=False) as f:
  temporary=Path(f.name)
  f.write(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
 try:temporary.replace(out)
 finally:temporary.unlink(missing_ok=True)
 print(f'Feeds OK={len(success)} errors={len(errors)} articles={len(items)} out={out}')
 if not usable:sys.exit(1)
if __name__=='__main__':main()
