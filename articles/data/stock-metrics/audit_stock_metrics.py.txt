"""Independent Fraction/Decimal audit of Article13, including exception handling."""
import datetime as dt,gzip,hashlib,json,math
from fractions import Fraction as F
from decimal import Decimal as D,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/stock-metrics'
def audit(result=None):
    r=result or json.loads((DATA/'results.json').read_text());m=json.loads((DATA/'sources.json').read_text());count=0
    def eq(a,b):
        nonlocal count
        if b is None:
            if a is not None:raise ValueError('Undefined ratio should be null')
        elif a is None or not math.isclose(float(a),float(b),rel_tol=2e-15,abs_tol=1e-9):raise ValueError(f'Numeric audit mismatch: {a} / {b}')
        count+=1
    for name,digest in m['input_sha256'].items():
        if hashlib.sha256((DATA/name).read_bytes()).hexdigest()!=digest:raise ValueError('Input hash mismatch')
    inputs=json.loads((DATA/'companies.json').read_text())['companies'];facts={x['code']:x['facts'] for x in json.loads((DATA/'financial-evidence.json').read_text())['companies']}
    if len(inputs)!=6 or {x['code'] for x in r['companies']}!={x['code'] for x in inputs}:raise ValueError('Company set differs')
    for c in inputs:
        for key,value in facts[c['code']].items():
            if c[key]!=value:raise ValueError('Issuer ledger differs: '+key)
            count+=1
        if c['price_date']!='2026-03-31' or c['fiscal_end']!='2026-03-31' or c['fiscal_start']!='2025-04-01' or c['equity_begin_date']!='2025-03-31' or c['disclosed_date']<=c['price_date']:raise ValueError('Date scope mismatch')
        raw=json.loads(gzip.decompress((DATA/'raw'/f'price_{c["code"]}.json.gz').read_bytes()))['chart']['result'][0];pairs=[(dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat(),v) for t,v in zip(raw['timestamp'],raw['indicators']['quote'][0]['close'])];quote=[v for d,v in pairs if d==c['price_date']]
        if len(quote)!=1:raise ValueError('Quote missing')
        if raw['meta']['currency']!='JPY' or raw['meta']['symbol']!=c['code']+'.T':raise ValueError('Quote unit/symbol mismatch')
        p=F(D(str(quote[0])).quantize(D('.01'),rounding=ROUND_HALF_UP));s=c['issued_shares']-c['treasury_shares'];w=c['weighted_average_shares'];n=c['profit_million_yen']*1000000;e0=c['equity_begin_million_yen']*1000000;e1=c['equity_end_million_yen']*1000000;x=next(x for x in r['companies'] if x['code']==c['code'])
        for event in raw.get('events',{}).get('splits',{}).values():
            if dt.datetime.fromtimestamp(event['date'],dt.timezone.utc).date().isoformat()>c['price_date']:raise ValueError('Post-date split unreviewed')
        expected=dict(price=p,price_raw_api=quote[0],issued=c['issued_shares'],treasury=c['treasury_shares'],shares=s,weighted=w,profit=n,equity_begin=e0,equity_end=e1,market_cap=p*s,eps=F(n,w),bps=F(e1,s),per=p*w/n if n>0 else None,pbr=p*s/e1 if e1>0 else None,roe_average=F(n*2,e0+e1) if e0+e1>0 else None,roe_end=F(n,e1) if e1>0 else None,eps_end=F(n,s),per_end=p*s/n if n>0 else None,forecast_per=None)
        for key,v in expected.items():eq(x[key],v)
        eq(x['eps_vs_reported'],F(n,w)-F(c['reported_eps_yen']));eq(x['bps_vs_reported'],F(e1,s)-F(c['reported_bps_yen']))
        if abs(F(n,w)-F(c['reported_eps_yen']))>=F('.01')+F(1000000,w):raise ValueError('EPS report mismatch')
        if abs(F(e1,s)-F(c['reported_bps_yen']))>=F('.01')+F(1000000,s):raise ValueError('BPS report mismatch')
        if n>0 and e1>0:eq(x['pbr'],x['per_end']*x['roe_end'])
    e=r['examples']
    for x in e['price_cap']:eq(x['market_cap'],x['price']*x['shares'])
    for x in e['per']:eq(x['per'],F(x['price'],x['eps']) if x['eps']>0 else None)
    for x in e['pbr']:eq(x['pbr'],F(x['price'],x['bps']) if x['bps']>0 else None)
    for k,p,s,w,n,equity in [('base',1000,100000000,100000000,10000000000,100000000000),('split',500,200000000,200000000,10000000000,100000000000),('issue',1000,120000000,120000000,10000000000,120000000000),('buyback',1000,80000000,80000000,10000000000,80000000000)]:
        x=e[k]
        for key,value in [('price',p),('shares',s),('weighted',w),('market_cap',p*s),('profit',n),('equity_end',equity),('equity_begin',equity),('eps',F(n,w)),('bps',F(equity,s)),('per',F(p*w,n)),('pbr',F(p*s,equity)),('roe_end',F(n,equity)),('roe_average',F(n,equity)),('eps_end',F(n,s)),('per_end',F(p*s,n))]:eq(x[key],value)
    for key,v in dict(price=1000,eps_before=100,eps_after=50,per_before=10,per_after=20).items():eq(e['profit_halved'][key],v)
    eq(e['issue_existing_owner_before'],F(1,100));eq(e['issue_existing_owner_after'],F(1000000,120000000))
    for x in r['growth']:
        for point in x['points']:
            eps=100*(1+F(str(x['growth'])))**point['year'];eq(point['eps'],eps);eq(point['per'],F(1000)/eps)
    for x in r['identity']:
        for point in x['points']:eq(point['pbr'],x['per']*F(str(point['roe'])))
    return dict(status='pass',independent_checks=count,methods=['issuer fact ledger / dated scopes','raw quote and split history','exact Fraction arithmetic','Decimal JPY display normalization','EPS/BPS disclosed precision bounds','matched-denominator identity','all hypothetical capital changes / growth and exception cases'])
if __name__=='__main__':
    r=audit();(DATA/'calculation-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
