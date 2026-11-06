"""Independent integer-cents/Fraction audit, with exhaustive prefix extrema."""
import csv,datetime as dt,hashlib,json
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/bitcoin-crash'

def audit():
    rows=list(csv.DictReader((DATA/'observations.csv').open()));result=json.loads((DATA/'results.json').read_text());manifest=json.loads((DATA/'sources.json').read_text());by={};raw_checks=0
    assert manifest['provider']=='Bitstamp' and manifest['market']=='BTC/USD' and manifest['interval_seconds']==86400
    for c in manifest['chunks']:
        raw=(DATA/'raw'/c['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==c['sha256']
        payload=json.loads(raw);assert payload['data']['pair']=='BTC/USD'
        for r in payload['data']['ohlc']:
            date=dt.datetime.fromtimestamp(int(r['timestamp']),dt.timezone.utc).date().isoformat()
            if date in by:assert by[date]==r
            by[date]=r
    for r in rows:
        assert {k:v for k,v in r.items() if k!='date'}==by[r['date']];raw_checks+=1
    assert all((Fraction(r['close'])*100).denominator==1 for r in rows)
    valid=[r for r in rows if Fraction(r['volume'])>0];dates=[dt.date.fromisoformat(r['date']) for r in valid];cents=[int(Fraction(r['close'])*100) for r in valid];checks=0
    assert len(rows)==5057 and len(valid)==5054
    for event in result['events']:
        indexes=[i for i,r in enumerate(valid) if event['window_start']<=r['date']<=event['window_end']]
        candidates=[]
        for position,index in enumerate(indexes):
            peak=max(indexes[:position+1],key=lambda i:cents[i])
            candidates.append((Fraction(cents[index],cents[peak])-1,position,peak,index))
        drop,_,peak,trough=min(candidates)
        recovery=next((i for i in range(trough+1,len(valid)) if cents[i]>=cents[peak]),None)
        expected={'peak_date':valid[peak]['date'],'peak_usd':valid[peak]['close'],'trough_date':valid[trough]['date'],'trough_usd':valid[trough]['close'],'peak_to_trough_days':(dates[trough]-dates[peak]).days,'recovery_date':valid[recovery]['date'] if recovery is not None else None,'peak_to_recovery_days':(dates[recovery]-dates[peak]).days if recovery is not None else None,'trough_to_recovery_days':(dates[recovery]-dates[trough]).days if recovery is not None else None,'unrecovered_days':(dates[-1]-dates[peak]).days if recovery is None else None}
        for k,v in expected.items():assert event[k]==v,(event['label'],k);checks+=1
        assert abs(Fraction(event['drawdown_pct'])-drop*100)<Fraction(1,10**20);checks+=1
        amount=Fraction(1000000*cents[trough],cents[peak]);rounded=(amount.numerator*2//amount.denominator+1)//2
        assert event['model_trough_jpy']==rounded;checks+=1
        assert abs(Fraction(event['required_rebound_pct'])-(Fraction(cents[peak],cents[trough])-1)*100)<Fraction(1,10**20);checks+=1
        # None means no valid later close ever reached the threshold, not zero days.
        assert all(cents[i]<cents[peak] for i in range(trough+1,recovery if recovery is not None else len(valid)));checks+=1
    points=json.loads((DATA/'point-checks.json').read_text())
    assert points['all_match'] and len(points['checks'])==15
    for p in points['checks']:
        raw=(DATA/'raw'/p['raw_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==p['sha256']
        observation=json.loads(raw)['data']['ohlc'];assert len(observation)==1
        assert observation[0]['close']==p['close']
        assert p['returned_date']==p['date'] and p['close']==by[p['date']]['close'];checks+=1
    for h in points['hourly_checks']:
        raw=(DATA/'raw'/h['raw_file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==h['sha256']
        hourly=json.loads(raw)['data']['ohlc'];start=int(dt.datetime.fromisoformat(h['date']).replace(tzinfo=dt.timezone.utc).timestamp())
        assert [int(r['timestamp']) for r in hourly]==[start+i*3600 for i in range(24)]
        assert hourly[-1]['close']==h['hourly_last_close']
        assert h['hours']==24 and h['hourly_last_close']==by[h['date']]['close'];checks+=1
    return dict(status='passed',raw_rows_verified=raw_checks,valid_trading_rows=len(valid),zero_volume_excluded=3,events=5,independent_checks=checks,point_requeries=len(points['checks']),hourly_close_crosschecks=len(points['hourly_checks']))

if __name__=='__main__':print(json.dumps(audit(),indent=2))
