"""Independent Decimal audit; no production calculation functions imported."""
import csv,datetime as dt,gzip,hashlib,io,json,math
from decimal import Decimal as D,localcontext,ROUND_HALF_EVEN
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/etf-funds'
def audit(result=None):
    r=result or json.loads((DATA/'results.json').read_text());m=json.loads((DATA/'sources.json').read_text());count=0
    def equal(a,b,tol=1e-9):
        nonlocal count
        if not math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol):raise ValueError(f'Independent audit mismatch: {a} / {b}')
        count+=1
    def text(name):
        b=(DATA/'raw'/f'{name}.csv.gz').read_bytes()
        if hashlib.sha256(b).hexdigest()!=m['input_sha256'][f'raw/{name}.csv.gz']:raise ValueError('Checksum mismatch')
        return gzip.decompress(b).decode('cp932')
    def annuity(p,rate,years):
        v=D(0);factor=(1+rate)**(D(1)/12)
        for month in range(years*12):v=v*factor+p
        return int(v.quantize(D(1),rounding=ROUND_HALF_EVEN))
    with localcontext() as ctx:
        ctx.prec=45;data={'slim':{},'etf':{}}
        for x in csv.DictReader(io.StringIO(text('slim'))):
            d=dt.datetime.strptime(x['年月日'],'%Y年%m月%d日').date().isoformat()
            if D(x['分配金'] or 0):raise ValueError('Unreviewed fund dividend')
            v=D(x['基準価額(円)']);data['slim'][d]=(v,v,D(0))
        for x in csv.reader(io.StringIO(text('etf'))):
            if len(x)<7 or len(x[0])!=8 or not x[0].isdigit():continue
            d=dt.datetime.strptime(x[0],'%Y%m%d').date().isoformat();data['etf'][d]=tuple(D(x[i]) for i in (3,6,4))
        dates=sorted(d for d in set(data['slim'])&set(data['etf']) if '2021-09-30'<=d<='2026-09-30')
        if r['common_dates']!=dates or (dates[0],dates[-1])!=('2021-09-30','2026-09-30'):raise ValueError('Common date mismatch')
        series=list(data['etf'].values());factor=D(1);maxerror=D(0)
        for before,current in zip(series,series[1:]):
            factor*=(current[0]+current[2])/before[0];e=abs(factor/(current[1]/series[0][1])-1);maxerror=max(maxerror,e);count+=1
        if maxerror>D('1e-9'):raise ValueError('Dividend reinvestment mismatch')
        equal(r['reinvestment_max_relative_error'],maxerror,1e-13)
        for x in r['metrics']:
            s=data[x['asset']];a,b=s[dates[0]],s[dates[-1]];ratio=b[1]/a[1];equal(x['total_return'],ratio-1);equal(x['cagr'],ratio**(D(1)/5)-1);equal(x['nav_only_return'],b[0]/a[0]-1);equal(x['observations'],len(dates),0)
            values=[s[d][1] for d in dates];dds=[v/max(values[:i+1])-1 for i,v in enumerate(values)];worst=min(dds);idx=dds.index(worst);peak=values[:idx+1].index(max(values[:idx+1]));equal(x['mdd'],worst)
            if (x['peak'],x['trough'])!=(dates[peak],dates[idx]):raise ValueError('Drawdown date mismatch')
            selected={d[:7]:d for d in dates};vs=[s[d][1] for d in selected.values()];returns=[vs[i]/vs[i-1]-1 for i in range(1,len(vs))];mean=sum(returns)/len(returns);variance=sum((v-mean)**2 for v in returns)/(len(returns)-1);equal(x['annualized_volatility'],variance.sqrt()*D(12).sqrt())
            curve=r['curves'][x['asset']]
            if [c['date'] for c in curve]!=list(selected.values()) or len(curve)!=61:raise ValueError('Curve mismatch')
            for c in curve:equal(c['wealth'],100*s[c['date']][1]/a[1])
        for x in r['annual']:
            s=data[x['asset']];equal(x['return_value'],s[x['end']][1]/s[x['start']][1]-1)
            if x['partial']!=(x['year']==2026):raise ValueError('Partial year mislabeled')
        for x in r['accumulation']:
            expected=annuity(D(x['monthly']),D(str(x['annual'])),x['years']);equal(x['final'],expected,0);equal(x['principal'],x['monthly']*12*x['years'],0);equal(x['gain'],expected-x['principal'],0)
        for x in r['costs']:
            net=D('1.05')*(1-D(str(x['cost'])))-1;expected=annuity(D(x['monthly']),net,x['years']);base=annuity(D(x['monthly']),D('.05'),x['years']);equal(x['principal'],x['monthly']*12*x['years'],0);equal(x['net_annual'],net);equal(x['final'],expected,0);equal(x['no_cost_final'],base,0);equal(x['cost_impact'],base-expected,0)
        asset=D(1000000);cash=D(0);reinvest=D(1000000)
        for i,x in enumerate(r['cashflows']):
            equal(x['year'],i,0)
            for key,value in [('etf_cash_asset',asset),('etf_cash_received',cash),('etf_reinvest',reinvest),('fund_internal',reinvest),('fund_sale_asset',asset),('fund_sale_received',cash)]:equal(x[key],value)
            cash+=asset*D('.03');asset*=D('1.03');reinvest*=D('1.06')
    return dict(status='pass',independent_checks=count,decimal_precision=45,methods=['raw checksum','independent CSV decoding','official NAV distribution reconstruction','Decimal CAGR','brute-prefix MDD and dates','monthly volatility','iterative annuity','multiplicative cost factors','four cash-flow conservation scenarios'])
if __name__=='__main__':
    r=audit();(DATA/'calculation-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
