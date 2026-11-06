"""Explicit network acquisition to a NEW directory; never overwrites frozen data."""
import argparse,csv,datetime as dt,hashlib,io,json
from pathlib import Path
from urllib.request import Request,urlopen

def fetch(output):
    output.mkdir(parents=True,exist_ok=False);(output/'raw').mkdir()
    start=dt.date(2013,1,1);end=dt.date(2026,11,5);chunks=[];by={};overlap=0
    while start<=end:
        stop=min(end,start+dt.timedelta(days=999));stamp=lambda d:int(dt.datetime.combine(d,dt.time(),dt.timezone.utc).timestamp())
        url=f'https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000&start={stamp(start)}&end={stamp(stop)}&exclude_current_candle=true'
        with urlopen(Request(url,headers={'User-Agent':'TopicBase-Research/1.0'}),timeout=60) as response:raw=response.read();status=response.status
        name=f'bitstamp-{start}-{stop}.json';(output/'raw'/name).write_bytes(raw);rows=json.loads(raw)['data']['ohlc']
        dates=[dt.datetime.fromtimestamp(int(r['timestamp']),dt.timezone.utc).date().isoformat() for r in rows]
        for date,row in zip(dates,rows):
            if date in by:
                if by[date]!=row:raise ValueError('Conflicting overlap; do not overwrite audited dataset')
                overlap+=1
            by[date]=row
        chunks.append(dict(url=url,file=name,sha256=hashlib.sha256(raw).hexdigest(),retrieved_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),status=status,rows=len(rows),returned_first_date=min(dates),returned_last_date=max(dates)))
        start=stop+dt.timedelta(days=1)
    by={d:r for d,r in sorted(by.items()) if '2013-01-01'<=d<='2026-11-05'}
    expected=[(dt.date(2013,1,1)+dt.timedelta(days=i)).isoformat() for i in range(5057)]
    if list(by)!=expected:raise ValueError('Missing calendar data; do not interpolate')
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=['date','timestamp','open','high','low','close','volume'],lineterminator='\n');writer.writeheader()
    for date,row in by.items():writer.writerow(dict(date=date,**row))
    (output/'observations.csv').write_text(buf.getvalue())
    manifest=dict(provider='Bitstamp',market='BTC/USD',interval_seconds=86400,start_date='2013-01-01',end_date='2026-11-05',requested_rows=5057,actual_rows=len(by),missing_dates=[],duplicates=0,input_sha256=hashlib.sha256(buf.getvalue().encode()).hexdigest(),raw_overlap_rows=overlap,overlap_all_fields_consistent=True,chunks=chunks,timestamp_convention='UTC interval start; close is next day 00:00 UTC / 09:00 JST; zero-volume rows excluded from extrema and charted as gaps')
    (output/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n');print(len(by),'daily observations acquired; compare before using')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();fetch(args.output)
