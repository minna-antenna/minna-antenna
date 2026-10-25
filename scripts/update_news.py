#!/usr/bin/env python3
"""Retrieve public RSS metadata and rank news candidates; no scraping article bodies."""
import argparse, datetime as dt, hashlib, json, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

JST=dt.timezone(dt.timedelta(hours=9))
FEEDS=[
 ('NHK総合','ニュース','https://www.nhk.or.jp/rss/news/cat0.xml'),
 ('NHK社会','ニュース','https://www.nhk.or.jp/rss/news/cat1.xml'),
 ('BBC News 日本語','アジア・翻訳','https://feeds.bbci.co.uk/japanese/rss.xml'),
 ('Google ニュース・ゲーム','ゲーム','https://news.google.com/rss/search?q='+urllib.parse.quote('ゲーム 新作 OR 任天堂 OR PlayStation')+'&hl=ja&gl=JP&ceid=JP:ja'),
 ('Google ニュース・アニメ','アニメ','https://news.google.com/rss/search?q='+urllib.parse.quote('アニメ 新作 OR 声優 OR 劇場版')+'&hl=ja&gl=JP&ceid=JP:ja'),
 ('Google ニュース・車','車・バイク','https://news.google.com/rss/search?q='+urllib.parse.quote('自動車 OR ホンダ OR トヨタ OR EV')+'&hl=ja&gl=JP&ceid=JP:ja'),
 ('Google ニュース・株','株・投資','https://news.google.com/rss/search?q='+urllib.parse.quote('日本株 OR 決算 OR 日経平均')+'&hl=ja&gl=JP&ceid=JP:ja'),
 ('Google ニュース・仮想通貨','仮想通貨','https://news.google.com/rss/search?q='+urllib.parse.quote('ビットコイン OR 仮想通貨')+'&hl=ja&gl=JP&ceid=JP:ja'),
 ('Google ニュース・政治','政治・経済','https://news.google.com/rss/search?q='+urllib.parse.quote('政府 OR 国会 OR 日銀')+'&hl=ja&gl=JP&ceid=JP:ja'),
 ('Google ニュース・スポーツ','スポーツ','https://news.google.com/rss/search?q='+urllib.parse.quote('野球 OR サッカー OR スポーツ')+'&hl=ja&gl=JP&ceid=JP:ja'),
]
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
 records=[]
 for item in root.findall('.//item'):
  title=text(item,'title'); url=text(item,'link'); pub=parse_date(text(item,'pubDate'))
  if not title or not url or not pub or not url.startswith(('https://','http://')):continue
  age=(now-pub).total_seconds()/3600
  if age < -3 or age > 72:continue
  # Do not reproduce snippets or full text; use metadata only.
  original=title
  publisher=source
  if source.startswith('Google ニュース') and ' - ' in title:
   title,publisher=title.rsplit(' - ',1)
  records.append(dict(title=title.strip(),url=url,source=publisher.strip(),feed=source,category=category,published_at=pub.isoformat().replace('+00:00','Z'),age_hours=round(max(0,age),1),original_title=original))
 return records

def normalize(s):
 s=re.sub(r'【[^】]{1,35}】','',s)
 s=re.sub(r'\s+|[\W_]+','',s,flags=re.UNICODE)
 return s.casefold()[:100]

def build(feeds,now):
 # dedupe near-identical titles, group distinct publishers only; not claimed as canonical same-event detection.
 grouped={}
 for x in feeds:
  k=normalize(x['title']);
  if not k:continue
  if k not in grouped:grouped[k]=[]
  if x['source'] not in {y['source'] for y in grouped[k]}:grouped[k].append(x)
 scored=[]
 for group in grouped.values():
  lead=min(group,key=lambda x:x['age_hours'])
  age=lead['age_hours']; freshness=max(0,round(60*(1-min(age,72)/72)))
  sources=len({x['source'] for x in group})
  multi=min(30, max(0,sources-1)*15)
  trusted=10 if any(x['feed'].startswith('NHK') or x['feed'].startswith('BBC') for x in group) else 0
  score=freshness+multi+trusted
  key=hashlib.sha1((normalize(lead['title'])+lead['url']).encode()).hexdigest()[:14]
  scored.append(dict(id=key,title=lead['title'],url=lead['url'],source=lead['source'],feed=lead['feed'],category=lead['category'],published_at=lead['published_at'],score=score,reason=dict(freshness_points=freshness,additional_source_points=multi,primary_feed_bonus=trusted,age_hours=age,independent_publishers=sources,source_names=sorted({x['source'] for x in group}),scoring_rule='新しさ 0〜60点（72時間で減衰）＋異なる媒体の同一見出し 1媒体追加ごとに15点・最大30点＋NHK/BBCフィード 10点。SNSの実測人気ではありません。')))
 scored.sort(key=lambda x:(-x['score'],x['published_at']),reverse=False)
 # Set highest score first, newest first for ties.
 scored.sort(key=lambda x:x['published_at'],reverse=True)
 scored.sort(key=lambda x:x['score'],reverse=True)
 # modest genre diversity, max 10 per category
 counts={}; selected=[]
 for item in scored:
  cat=item['category']
  if counts.get(cat,0)>=10:continue
  selected.append(item);counts[cat]=counts.get(cat,0)+1
  if len(selected)>=60:break
 return selected

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fixtures',help='directory of example .xml feeds for offline testing');ap.add_argument('--output',default='data/news.json');args=ap.parse_args()
 now=dt.datetime.now(dt.timezone.utc); all_items=[]; success=[]; errors=[]
 for i,(name,category,url) in enumerate(FEEDS):
  try:
   if args.fixtures:
    p=Path(args.fixtures)/f'{i}.xml'
    if not p.exists():continue
    raw=p.read_bytes()
   else:
    req=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml, application/xml;q=0.9'})
    with urllib.request.urlopen(req,timeout=18) as response:raw=response.read(2_000_000)
   entries=parse_rss(raw,name,category,now);all_items.extend(entries)
   success.append(dict(name=name,url=url,count=len(entries)))
  except Exception as e:errors.append(dict(feed=name,error=str(e)[:180]))
 out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
 # If all feeds unavailable, keep prior valid items (clearly mark as stale).
 previous={}
 if out.exists():
  try:previous=json.loads(out.read_text(encoding='utf-8'))
  except Exception:pass
 items=build(all_items,now) if success else previous.get('articles',[])
 output=dict(generated_at=now.isoformat().replace('+00:00','Z') if success else previous.get('generated_at'),last_attempt_at=now.isoformat().replace('+00:00','Z'),status='ok' if success and not errors else ('partial' if success else 'error'),method='公開RSSメタデータを取得。記事の公開日時・見出しの同一性・フィード種別に基づく透明なスコア。PV、SNSシェア数、実際のトレンド順位は使用していません。',feed_success=success,feed_errors=errors,articles=items)
 out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Feeds OK={len(success)} errors={len(errors)} articles={len(items)} out={out}')
 if not success:sys.exit(1)
if __name__=='__main__':main()
