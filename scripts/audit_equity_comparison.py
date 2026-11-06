"""Independent audit of raw responses and Decimal calculations; offline, fail closed."""
import csv
import datetime as dt
from decimal import Decimal, localcontext, ROUND_HALF_UP
import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import re
D=Decimal
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'articles/data/sp500-all-country'


def run_audit():
    manifest=json.loads((DATA/'sources.json').read_text());payload=(DATA/'observations.csv').read_bytes()
    assert hashlib.sha256(payload).hexdigest()==manifest['input_sha256'],'CSV hash changed'
    rows=list(csv.DictReader(io.StringIO(payload.decode())));series={};dividends={}
    for src in manifest['sources']:
        raw=gzip.decompress((DATA/'raw'/(src['name']+'.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==src['sha256'],'Raw source hash changed'
        if src['name']=='FED_JPY':
            values={}
            for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',raw.decode(),re.S|re.I):
                cells=[html.unescape(re.sub('<[^>]+>','',s)).strip() for s in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.S|re.I)]
                if len(cells)!=2:continue
                try:date=dt.datetime.strptime(cells[0],'%d-%b-%y').date().isoformat()
                except ValueError:continue
                if manifest['start']<=date<=manifest['end'] and cells[1]!='ND':
                    assert date not in values;values[date]=float(cells[1])
            series['usd_jpy']=values
        else:
            response=json.loads(raw)['chart'];assert response['error'] is None and len(response['result'])==1
            r=response['result'][0];assert r['meta']['currency']=='USD';assert not r.get('events',{}).get('splits')
            dates=[dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in r['timestamp']]
            assert dates==sorted(set(dates))
            close=r['indicators']['quote'][0]['close'];adj=r['indicators']['adjclose'][0]['adjclose']
            assert len(dates)==len(close)==len(adj)
            for key,vals in [('close',close),('adjusted',adj)]:series[src['name'].lower()+'_'+key+'_usd']={d:v for d,v in zip(dates,vals) if manifest['start']<=d<=manifest['end'] and v is not None}
            events={dt.datetime.fromtimestamp(e['date'],dt.timezone.utc).date().isoformat():D(str(e['amount'])) for e in r['events']['dividends'].values()}
            with localcontext() as ctx:
                ctx.prec=50;factor=D(1);errors=[]
                for i in range(len(dates)-1,0,-1):
                    if dates[i] in events:factor*=1-events[dates[i]]/D(str(close[i-1]))
                    observed=D(str(adj[i-1]))/D(str(close[i-1]))/(D(str(adj[-1]))/D(str(close[-1])))
                    errors.append(abs(factor/observed-1))
                assert max(errors)<D('0.000002'),'Cash distribution adjustment differs'
                dividends[src['name']]=dict(events=len(events),splits=0,max_adjustment_relative_error=float(max(errors)))
    assert [r['date'] for r in rows]==sorted(set().union(*(set(v) for v in series.values())))
    for row in rows:
        for col,vals in series.items():
            if row['date'] in vals:assert float(row[col])==vals[row['date']],'Raw to CSV mismatch'
            else:assert row[col]=='','Missing value was filled'
    common=[r for r in rows if all(r.values())]
    result=json.loads((DATA/'results.json').read_text());primary=json.loads((DATA/'primary-facts.json').read_text())
    checks=0
    with localcontext() as ctx:
        ctx.prec=60
        for years,w in result['windows'].items():
            selected=[r for r in common if r['date']>=w['start']]
            for key in ['spy','acwi']:
                for ccy in ['usd','jpy']:
                    values=[D(r[key+'_adjusted_usd'])*(D(r['usd_jpy']) if ccy=='jpy' else 1) for r in selected]
                    span=D((dt.date.fromisoformat(selected[-1]['date'])-dt.date.fromisoformat(selected[0]['date'])).days)
                    cagr=((values[-1]/values[0]).ln()*D('365.2425')/span).exp()-1
                    high=values[0];worst=D(0)
                    for v in values:high=max(high,v);worst=min(worst,v/high-1)
                    a=w['assets'][key][ccy]
                    assert abs(cagr-D(str(a['cagr'])))<D('1e-12')
                    assert abs(worst-D(str(a['maximum_drawdown'])))<D('1e-12');checks+=2
                    if ccy=='jpy':
                        assert abs(D(1000000)*values[-1]/values[0]-D(str(w['assets'][key]['final_jpy'])))<D('.00001')
                        ends={r['date'][:7]:v for r,v in zip(selected,values)};v=list(ends.values());ret=[b/a-1 for a,b in zip(v,v[1:])];mean=sum(ret)/len(ret)
                        vol=(sum((r-mean)**2 for r in ret)/(len(ret)-1)*12).sqrt()
                        assert abs(vol-D(str(w['assets'][key]['monthly_volatility_jpy'])))<D('1e-12');checks+=2
                    else:
                        # A reconciliation, not identity: official SPY uses bid/offer midpoint.
                        difference=cagr*100-D(str(primary[key]['official_market_cagr_percent'][years]))
                        assert abs(difference)<D('.10'),'Official CAGR reconciliation exceeds disclosed 0.10 pp limit'
                        assert abs(difference-D(str(w['assets'][key]['difference_from_official_percentage_points'])))<D('1e-10')
        for record in result['annual']:
            initial=next(r for r in common if r['date']==record['start']);last=next(r for r in common if r['date']==record['end'])
            for key in ['spy','acwi']:
                for ccy in ['usd','jpy']:
                    ratio=D(last[key+'_adjusted_usd'])/D(initial[key+'_adjusted_usd'])
                    if ccy=='jpy':ratio*=D(last['usd_jpy'])/D(initial['usd_jpy'])
                    assert abs(ratio-1-D(str(record['returns'][key][ccy])))<D('1e-12');checks+=1
        ends={r['date'][:7]:r for r in common};months=list(ends.values())[1:];assert len(months)==120
        for key in ['spy','acwi']:
            balance=D(0);previous=None
            for row in months:
                value=D(row[key+'_adjusted_usd'])*D(row['usd_jpy'])
                if previous is not None:balance*=value/previous
                balance+=30000;previous=value
            expected=int(balance.quantize(D(1),rounding=ROUND_HALF_UP))
            assert result['historical_monthly'][key]['final_yen']==expected;checks+=1
        for scenario in result['hypothetical']:
            growth=((1+D(scenario['annual_percent'])/100).ln()/12).exp();balance=D(0)
            for _ in range(scenario['years']*12):balance=balance*growth+30000
            assert int(balance.quantize(D(1),rounding=ROUND_HALF_UP))==scenario['final_yen']
            assert scenario['gain_yen']==scenario['final_yen']-scenario['principal_yen'];checks+=1
    evidence=json.loads((DATA/'primary-audit.json').read_text())
    assert evidence['status']=='passed' and len(evidence['checks'])==49
    assert evidence['primary_facts_sha256']==hashlib.sha256((DATA/'primary-facts.json').read_bytes()).hexdigest(),'Primary facts no longer match independently checked source values'
    assert evidence['source_hashes']=={source['name']:source['sha256'] for source in primary['sources']}
    assert len(primary['spy']['top10'])==len(primary['acwi']['top10'])==10
    assert abs(sum(x[1] for x in primary['spy']['top10'])-39.04)<1e-10
    assert abs(sum(x[1] for x in primary['acwi']['top10'])-25.29)<1e-10
    for key in ['spy','acwi']:assert abs(sum(primary[key]['sectors'].values())-100)<.1
    return dict(status='passed',numeric_checks=checks,primary_label_value_checks=49,common_dates=len(common),source_hashes='passed',raw_to_csv='passed',corporate_actions=dividends,official_reconciliation_limit_percentage_points=.10,
                note='Official performance is a methodological cross-check, not the identical adjusted-close calculation. Primary holdings/fees checked against source PDFs at acquisition; published source hash and extracted numeric facts retained.')


if __name__=='__main__':print(json.dumps(run_audit(),ensure_ascii=False,indent=2))
