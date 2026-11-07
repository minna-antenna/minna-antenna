"""Independent Decimal/iterative audit of Article 10 outputs and raw observations."""
import csv,datetime as dt,gzip,hashlib,json,math,statistics
from decimal import Decimal as D,localcontext,ROUND_HALF_EVEN
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/dividends'
def audit(result=None):
    r=result or json.loads((DATA/'results.json').read_text());manifest=json.loads((DATA/'sources.json').read_text());checks=0
    def close(a,b,tol=1e-9):
        nonlocal checks
        if not math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol):raise ValueError(f'Numeric audit mismatch: {a} / {b}')
        checks+=1
    with localcontext() as ctx:
        ctx.prec=45
        for s in ('VYM','SPY'):
            name=f'raw/{s}.json.gz';raw=(DATA/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=manifest['input_sha256'][name]:raise ValueError('Checksum mismatch')
            o=json.loads(gzip.decompress(raw))['chart']['result'][0];dates=[dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in o['timestamp']];q=o['indicators']['quote'][0]['close'];adj=o['indicators']['adjclose'][0]['adjclose']
            points={d:(D(str(p)),D(str(a))) for d,p,a in zip(dates,q,adj) if p is not None and a is not None};div={dt.datetime.fromtimestamp(e['date'],dt.timezone.utc).date().isoformat():D(str(e['amount'])) for e in o['events']['dividends'].values()}
            factor=D(1);start=next(iter(points));prev=points[start][0];maxerror=0
            for date,(price,adjusted) in list(points.items())[1:]:
                factor*=1-div.get(date,D(0))/prev;relative=adjusted/price/(points[start][1]/points[start][0]);maxerror=max(maxerror,abs(float(relative*factor-1)));prev=price;checks+=1
            if maxerror>1e-5:raise ValueError('Dividend reconstruction mismatch')
            for p in [p for p in r['periods'] if p['asset']==s]:
                rows=[(d,v) for d,v in points.items() if p['start']<=d<=p['end']];a,b=rows[0][1],rows[-1][1]
                if rows[0][0]!=p['start'] or rows[-1][0]!=p['end'] or len(rows)!=p['observations']:raise ValueError('Period mismatch')
                growth=b[1]/a[1];close(p['total_return'],growth-1);close(p['price_return'],b[0]/a[0]-1);close(p['cagr'],growth**(D(1)/p['years'])-1)
                # Brute prefix maxima independently of the production running-peak algorithm.
                values=[v[1] for _,v in rows];dds=[v/max(values[:i+1])-1 for i,v in enumerate(values)];worst=min(dds);idx=dds.index(worst);peak=values[:idx+1].index(max(values[:idx+1]));close(p['mdd']['value'],worst)
                if (p['mdd']['peak'],p['mdd']['trough'])!=(rows[peak][0],rows[idx][0]):raise ValueError('Drawdown dates differ')
                months={d[:7]:v[1] for d,v in rows};vs=list(months.values());returns=[vs[i]/vs[i-1]-1 for i in range(1,len(vs))];mean=sum(returns)/len(returns);variance=sum((v-mean)**2 for v in returns)/(len(returns)-1);close(p['annualized_volatility'],variance.sqrt()*D(12).sqrt())
                distributions=sum(v for d,v in div.items() if '2025-09-30'<d<='2026-09-30');close(p['trailing_12m_distributions'],distributions);close(p['trailing_yield'],distributions/b[0])
            for y in [x for x in r['annual'] if x['asset']==s]:close(y['total_return'],points[y['end']][1]/points[y['start']][1]-1)
            curve=r['curves'][s];selected={d[:7]:(d,v[1]) for d,v in points.items() if r['start']<=d<=r['end']}
            if len(curve)!=121 or [x['date'] for x in curve]!=[x[0] for x in selected.values()]:raise ValueError('Curve date selection mismatch')
            for c,(d,v) in zip(curve,selected.values()):close(c['wealth'],100*v/points[r['start']][1])
        for x in r['accumulation']:
            rate=(1+D(str(x['rate'])))**(D(1)/12)-1;v=D(0)
            for month in range(x['years']*12):v=v*(1+rate)+30000
            expected=int(v.quantize(D(1),rounding=ROUND_HALF_EVEN));close(x['final'],expected,0);close(x['principal'],x['years']*360000,0);close(x['gain'],expected-x['principal'],0)
        for x in r['income']:
            annual=D(x['initial'])*D(str(x['yield_rate']));close(x['annual'],annual);close(x['monthly_average'],annual/12)
        reinvest=D(1000000);asset=D(1000000);cash=D(0)
        for i,x in enumerate(r['cashflows']):
            if x['year']!=i:raise ValueError('Flow year mismatch')
            for key,expected in [('reinvested',reinvest),('distributed_asset',asset),('distributed_cash',cash),('withdrawal_asset',asset),('withdrawal_cash',cash)]:close(x[key],expected)
            payment=asset*D('.03');asset=asset*D('1.06')-payment;cash+=payment;reinvest*=D('1.06')
    return dict(status='pass',independent_checks=checks,precision=45,methods=['raw SHA-256','Decimal adjusted-price ratios / CAGR','raw cash distributions reconstruction','brute-prefix drawdown and exact dates','sample monthly volatility','iterative monthly annuity','cash conservation and equivalent withdrawals'])
if __name__=='__main__':
    result=audit();(DATA/'calculation-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
