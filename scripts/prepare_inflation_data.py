"""Rebuild CSVs from frozen raw inputs; no network, no provenance overwrite.
Run from repository root: python -m scripts.prepare_inflation_data
"""
from pathlib import Path
import csv,io,json,gzip,hashlib,datetime as dt,sys,math
from scripts.fetch_long_term_data import FedRates
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'articles/data/inflation'
raw={k:gzip.decompress((D/'raw'/(k+'.gz')).read_bytes()) for k in ['GLD','SPY','USCPI','JP_OFFICIAL','FX','BTC']}
fx={}
for r in FedRates(raw['FX'].decode()).rows:
 if len(r)!=2 or r[1]=='ND':continue
 try:date=dt.datetime.strptime(r[0],'%d-%b-%y').date().isoformat()
 except ValueError:continue
 fx[date]=float(r[1])
series={};distribution_audit={}
for symbol in ['GLD','SPY']:
 a=json.loads(raw[symbol])['chart']['result'][0];assert a['meta']['currency']=='USD' and a['meta']['symbol']==symbol;assert not a.get('events',{}).get('splits')
 dates=[dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in a['timestamp']]
 close=a['indicators']['quote'][0]['close'];adj=a['indicators']['adjclose'][0]['adjclose'];series[symbol]={d:(c,v) for d,c,v in zip(dates,close,adj) if c is not None and v is not None}
 dividends=a.get('events',{}).get('dividends',{});baseline='2016-09-30';factor0=series[symbol][baseline][1]/series[symbol][baseline][0];product=1.;maxerror=0;count=0
 bydate={dt.datetime.fromtimestamp(v['date'],dt.timezone.utc).date().isoformat():v['amount'] for v in dividends.values()}
 for i,d in enumerate(dates):
  if not baseline<d<='2026-09-30':continue
  if d in bydate:product*=1-bydate[d]/close[i-1];count+=1
  got=(series[symbol][d][1]/series[symbol][d][0])/factor0;expected=1/product;maxerror=max(maxerror,abs(got/expected-1))
 assert maxerror<1e-5,(symbol,maxerror)
 distribution_audit[symbol]=dict(dividends_in_comparison_period=count,splits=0,max_adjustment_relative_error=maxerror,tolerance=1e-5)
btc={r['date']:r for r in csv.DictReader(io.StringIO(raw['BTC'].decode())) if float(r['volume'])>0}
us={r['observation_date'][:7]:float(r['CPIAUCNS']) for r in csv.DictReader(io.StringIO(raw['USCPI'].decode())) if r['CPIAUCNS'] not in ['','.']}
jp={r[0][:4]+'-'+r[0][4:]:float(r[1]) for r in csv.reader(io.StringIO(raw['JP_OFFICIAL'].decode('cp932'))) if len(r)>1 and len(r[0])==6 and r[0].isdigit()}
assert jp['2026-09']==102.2 and us['2026-09']==336.940
common=sorted(set(series['GLD']) & set(series['SPY']) & set(fx) & set(btc));common=[d for d in common if '2016-09-30'<=d<='2026-09-30'];assert common[0]=='2016-09-30' and common[-1]=='2026-09-30'
rows=[]
for date in common:
 rows.append(dict(date=date,gld_close_usd=series['GLD'][date][0],gld_adjusted_usd=series['GLD'][date][1],btc_close_usd=btc[date]['close'],spy_close_usd=series['SPY'][date][0],spy_adjusted_usd=series['SPY'][date][1],usd_jpy=fx[date]))
def csvout(name,rows):
 b=io.StringIO();w=csv.DictWriter(b,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);payload=b.getvalue().encode();(D/name).write_bytes(payload);return hashlib.sha256(payload).hexdigest()
dailyhash=csvout('daily.csv',rows)
last={r['date'][:7]:r for r in rows};monthly=[]
for month,r in sorted(last.items()):monthly.append(dict(month=month,**r,us_cpi=us.get(month,''),jp_cpi=jp[month],us_cpi_yoy=(us[month]/us[f'{int(month[:4])-1}{month[4:]}']-1) if month in us and f'{int(month[:4])-1}{month[4:]}' in us else '',jp_cpi_yoy=jp[month]/jp[f'{int(month[:4])-1}{month[4:]}']-1))
assert len(monthly)==121 and monthly[60]['month']=='2021-09';monthlyhash=csvout('monthly.csv',monthly)
cpirows=[dict(month=m,us_cpi=us.get(m,''),jp_cpi=jp[m]) for m in sorted(jp) if '2015-09'<=m<='2026-09'];assert len(cpirows)==133;cpihash=csvout('cpi.csv',cpirows)
print('Rebuilt archived daily/monthly/CPI CSVs:',len(rows),len(monthly),len(cpirows))
