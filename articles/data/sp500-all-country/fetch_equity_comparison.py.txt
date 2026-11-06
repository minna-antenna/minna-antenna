"""Explicit acquisition only; never run by RSS/Pages. Frozen snapshots are immutable."""
import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
if __package__:
    from .fetch_long_term_data import FedRates
else:
    from fetch_long_term_data import FedRates

START, END = '2016-09-30', '2026-09-30'


def urls():
    a = int(dt.datetime.fromisoformat(START).replace(tzinfo=dt.timezone.utc).timestamp())
    b = int((dt.datetime.fromisoformat(END)+dt.timedelta(days=1)).replace(tzinfo=dt.timezone.utc).timestamp())
    return {**{s:f'https://query1.finance.yahoo.com/v8/finance/chart/{s}?period1={a}&period2={b}&interval=1d&events=div%2Csplits' for s in ('SPY','ACWI')},
            'FED_JPY':'https://www.federalreserve.gov/releases/h10/hist/dat00_ja.htm'}


def prepare(raw):
    series = {}
    for name, payload in raw.items():
        if name == 'FED_JPY':
            fx = {}
            for row in FedRates(payload.decode()).rows:
                if len(row) != 2: continue
                try: day = dt.datetime.strptime(row[0], '%d-%b-%y').date().isoformat()
                except ValueError: continue
                if START <= day <= END and row[1] != 'ND':
                    if day in fx: raise ValueError('Duplicate FX observation')
                    fx[day] = float(row[1])
            series['usd_jpy'] = fx
        else:
            chart = json.loads(payload)['chart']
            if chart.get('error') or len(chart.get('result') or []) != 1: raise ValueError('Missing chart')
            result = chart['result'][0]
            if result['meta']['currency'] != 'USD': raise ValueError('Unexpected currency')
            if result.get('events',{}).get('splits'): raise ValueError('Split requires explicit new validation')
            times = result['timestamp']
            dates = [dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in times]
            if dates != sorted(set(dates)): raise ValueError('Duplicate/unordered source dates')
            for column, values in [('close',result['indicators']['quote'][0]['close']),('adjusted',result['indicators']['adjclose'][0]['adjclose'])]:
                if len(values) != len(dates): raise ValueError('Mismatched source arrays')
                series[name.lower()+'_'+column+'_usd'] = {d:float(v) for d,v in zip(dates,values) if START<=d<=END and v is not None}
    if any(START not in values or END not in values for values in series.values()): raise ValueError('Missing endpoints')
    buffer = io.StringIO(newline='')
    writer=csv.DictWriter(buffer,fieldnames=['date','spy_close_usd','spy_adjusted_usd','acwi_close_usd','acwi_adjusted_usd','usd_jpy'],lineterminator='\n')
    writer.writeheader()
    for day in sorted(set().union(*(set(v) for v in series.values()))):
        row={'date':day}
        for key,values in series.items():
            if day in values:
                v=values[day]
                if not 0<v<float('inf'): raise ValueError('Invalid value')
                row[key]=format(v,'.17g')
        writer.writerow(row)
    return buffer.getvalue().encode()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cached-source-dir',type=Path,help='Use independently retained responses and their acquisition manifest')
    a=p.parse_args()
    if a.output.exists(): p.error('Refusing to overwrite snapshot')
    records=[];raw={}
    cached=json.loads((a.cached_source_dir/'history-sources.json').read_text()) if a.cached_source_dir else None
    for name,url in urls().items():
        if cached:
            payload=gzip.decompress((a.cached_source_dir/(name+'.gz')).read_bytes())
            record=next(x for x in cached if x['name']==name)
            if record['url']!=url or hashlib.sha256(payload).hexdigest()!=record['sha256']: raise ValueError('Cached provenance mismatch')
            record=dict(record)
        else:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=60) as response: payload=response.read()
            record=dict(name=name,url=url,retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),sha256=hashlib.sha256(payload).hexdigest())
        records.append(record);raw[name]=payload
    payload=prepare(raw)
    a.output.mkdir(parents=True);(a.output/'raw').mkdir()
    for name,value in raw.items(): (a.output/'raw'/f'{name}.gz').write_bytes(gzip.compress(value,mtime=0))
    (a.output/'observations.csv').write_bytes(payload)
    (a.output/'sources.json').write_text(json.dumps(dict(start=START,end=END,input_sha256=hashlib.sha256(payload).hexdigest(),sources=records),indent=2)+'\n')
    print('Saved independently acquired ETF/FX snapshot')


if __name__=='__main__':
    # Supports direct script execution as well as python -m scripts.fetch_equity_comparison.
    main()
