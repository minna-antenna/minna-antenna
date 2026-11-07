"""Independent Decimal audit of raw provenance, FX, purchasing power and risks."""
import csv,datetime as dt,gzip,hashlib,io,json
from decimal import Decimal,localcontext
from pathlib import Path
if __package__:
    from .fetch_long_term_data import FedRates
else:
    from fetch_long_term_data import FedRates
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/inflation';D=Decimal

def audit():
    manifest=json.loads((DATA/'sources.json').read_text());result=json.loads((DATA/'results.json').read_text());raw={};checks=0
    for name,digest in manifest['input_sha256'].items():assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==digest
    for s in manifest['sources']+manifest['cpi_primary_crosscheck']:
        b=gzip.decompress((DATA/s['file']).read_bytes());assert hashlib.sha256(b).hexdigest()==s['sha256'],s['name'];raw[s['name']]=b
    assert raw['BTC']==(ROOT/'articles/data/bitcoin-crash/observations.csv').read_bytes()
    jp={r[0][:4]+'-'+r[0][4:]:D(r[1]) for r in csv.reader(io.StringIO(raw['JP_OFFICIAL'].decode('cp932'))) if r[0].isdigit() and len(r[0])==6}
    us={r['observation_date'][:7]:D(r['CPIAUCNS']) if r['CPIAUCNS'] else None for r in csv.DictReader(io.StringIO(raw['USCPI'].decode()))}
    primary={}
    for name in ['bls2015','bls2025']:
        payload=json.loads(raw[name]);assert payload['status']=='REQUEST_SUCCEEDED';series=payload['Results']['series'][0];assert series['seriesID']=='CUUR0000SA0'
        for r in series['data']:
            if r['period']=='M13':continue
            primary[r['year']+'-'+r['period'][1:]]=D(r['value']) if r['value'] not in ['-',''] else None
    for month,value in us.items():assert primary[month]==value;checks+=1
    assert [m for m,v in us.items() if v is None]==['2025-10']
    cpi_rows=list(csv.DictReader(io.StringIO((DATA/'cpi.csv').read_text())))
    assert [r['month'] for r in cpi_rows]==list(us)
    for r in cpi_rows:
        assert (D(r['us_cpi']) if r['us_cpi'] else None)==us[r['month']]
        assert D(r['jp_cpi'])==jp[r['month']];checks+=2
    fx={}
    for r in FedRates(raw['FX'].decode()).rows:
        if len(r)!=2 or r[1]=='ND':continue
        try:date=dt.datetime.strptime(r[0],'%d-%b-%y').date().isoformat()
        except ValueError:continue
        fx[date]=D(r[1])
    assets={};distributions={}
    for name in ['GLD','SPY']:
        a=json.loads(raw[name])['chart']['result'][0];assert a['meta']['currency']=='USD' and a['meta']['symbol']==name
        assert not a.get('events',{}).get('splits')
        dates=[dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in a['timestamp']];close=a['indicators']['quote'][0]['close'];adjusted=a['indicators']['adjclose'][0]['adjclose']
        assets[name]={d:(D(str(c)),D(str(v))) for d,c,v in zip(dates,close,adjusted) if c is not None and v is not None}
        # Independent distribution-factor reconstruction in Decimal for every daily observation.
        events={dt.datetime.fromtimestamp(e['date'],dt.timezone.utc).date().isoformat():D(str(e['amount'])) for e in a.get('events',{}).get('dividends',{}).values()}
        factor=D(1);base=assets[name]['2016-09-30'];initial=base[1]/base[0];count=0
        for i,date in enumerate(dates):
            if not '2016-09-30'<date<='2026-09-30':continue
            if date in events:factor*=1-events[date]/D(str(close[i-1]));count+=1
            observed=(assets[name][date][1]/assets[name][date][0])/initial
            assert abs(observed*factor-1)<D('.00001');checks+=1
        distributions[name]=count
    assert distributions=={'GLD':0,'SPY':40}
    btc={r['date']:D(r['close']) for r in csv.DictReader(io.StringIO(raw['BTC'].decode())) if D(r['volume'])>0}
    daily=list(csv.DictReader(io.StringIO((DATA/'daily.csv').read_text())));monthly=list(csv.DictReader(io.StringIO((DATA/'monthly.csv').read_text())))
    common=sorted(d for d in set(assets['GLD'])&set(assets['SPY'])&set(btc)&set(fx) if '2016-09-30'<=d<='2026-09-30');assert [r['date'] for r in daily]==common
    def near(a,b):assert abs(D(str(a))-b)<=max(D('1e-11'),abs(b)*D('1e-12')),(a,b)
    for r in daily:
        date=r['date']
        for key,value in [('gld_close_usd',assets['GLD'][date][0]),('gld_adjusted_usd',assets['GLD'][date][1]),('btc_close_usd',btc[date]),('spy_close_usd',assets['SPY'][date][0]),('spy_adjusted_usd',assets['SPY'][date][1]),('usd_jpy',fx[date])]:near(r[key],value);checks+=1
    last={r['date'][:7]:r for r in daily};assert len(monthly)==121
    for r in monthly:
        month=r['month'];assert r['date']==last[month]['date']
        for key in daily[0]:assert r[key]==last[month][key];checks+=1
        assert (D(r['us_cpi']) if r['us_cpi'] else None)==us[month];assert D(r['jp_cpi'])==jp[month];checks+=2
    keys={'gld':'gld_adjusted_usd','btc':'btc_close_usd','spy':'spy_adjusted_usd'}
    def ratio(first,last,key,mode):
        value=D(last[key])/D(first[key])
        if mode.startswith('jpy'):value*=D(last['usd_jpy'])/D(first['usd_jpy'])
        if mode.endswith('real'):
            cpi='us_cpi' if mode.startswith('usd') else 'jp_cpi'
            if not first[cpi] or not last[cpi]:return None
            value*=D(first[cpi])/D(last[cpi])
        return value
    with localcontext() as ctx:
        ctx.prec=45
        for p in result['periods']:
            first=monthly[0 if p['years']==10 else 60];lastrow=monthly[-1];assert p['start']==first['date'] and p['end']==lastrow['date']
            for mode,m in p['metrics'].items():
                value=ratio(first,lastrow,keys[p['asset']],mode);near(m['total_return'],value-1);near(m['cagr'],value**(D(1)/D(p['years']))-1);checks+=2
            for mode,field in [('jpy_nominal','ending_jpy_nominal'),('jpy_real','ending_jpy_real')]:assert p[field]==int((ratio(first,lastrow,keys[p['asset']],mode)*1000000).to_integral_value(rounding='ROUND_HALF_UP'));checks+=1
            near(p['us_inflation'],us['2026-09']/us[first['month']]-1);near(p['jp_inflation'],jp['2026-09']/jp[first['month']]-1);near(p['fx_ratio'],D(lastrow['usd_jpy'])/D(first['usd_jpy']));checks+=3
        for asset,key in keys.items():
            for mode,values in result['chart']['wealth'][asset].items():
                assert len(values)==len(monthly)
                for r,value in zip(monthly,values):
                    expected=ratio(monthly[0],r,key,mode)
                    if expected is None:assert value is None
                    else:near(value,expected)
                    checks+=1
        bydate={r['date']:r for r in monthly}
        for y in result['annual']:
            first,lastrow=bydate[y['start']],bydate[y['end']];us_rate=D(lastrow['us_cpi'])/D(first['us_cpi'])-1;jp_rate=D(lastrow['jp_cpi'])/D(first['jp_cpi'])-1
            near(y['us_inflation'],us_rate);near(y['jp_inflation'],jp_rate)
            assert y['us_high']==(us_rate>=D('.04') if y['full_calendar_year'] else None);assert y['jp_high']==(jp_rate>=D('.02') if y['full_calendar_year'] else None);checks+=4
            for asset,key in keys.items():
                for mode,value in y['assets'][asset].items():near(value,ratio(first,lastrow,key,mode)-1);checks+=1
        for risk in result['risk']:
            rows=[r for r in daily if r['date']>=('2016-09-30' if risk['years']==10 else '2021-09-30')];assert risk['observations']==len(rows)
            for mode in ['usd','jpy']:
                values=[D(r[keys[risk['asset']]])*(D(r['usd_jpy']) if mode=='jpy' else 1) for r in rows]
                candidates=[(v/max(values[:i+1])-1,i) for i,v in enumerate(values)];drop,bottom=min(candidates);peak=values.index(max(values[:bottom+1]));near(risk[mode]['drawdown'],drop);assert risk[mode]['peak_date']==rows[peak]['date'] and risk[mode]['trough_date']==rows[bottom]['date'];checks+=3
    return dict(status='passed',independent_checks=checks,common_daily_rows=len(daily),monthly_rows=len(monthly),cpi_primary_months=len(us),us_cpi_missing=['2025-10'],verified_dividends=distributions)

if __name__=='__main__':print(json.dumps(audit(),indent=2))
