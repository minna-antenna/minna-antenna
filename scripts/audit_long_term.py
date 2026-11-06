#!/usr/bin/env python3
"""Independent audit: raw responses -> CSV -> Decimal calculations. No network."""
import argparse
import csv
import datetime as dt
from decimal import Decimal, localcontext
import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'articles/data/bitcoin-vs-stocks'
COLUMNS = {'btc': 'btc_usd', 'spy': 'spy_adjusted_usd', 'acwi': 'acwi_adjusted_usd'}
D = Decimal


def csv_rows(payload):
    rows = list(csv.DictReader(io.StringIO(payload.decode())))
    assert [r['date'] for r in rows] == sorted({r['date'] for r in rows}), 'Duplicate or unordered CSV dates'
    for row in rows:
        dt.date.fromisoformat(row['date'])
        for k,v in row.items():
            if k != 'date' and v:
                assert D(v).is_finite() and D(v) > 0, 'Invalid value'
    return rows


def verify_raw(data_dir, manifest, rows):
    start, end = manifest['requested_start'], manifest['requested_end']
    expected, corporate, acquired = {}, {}, {}
    for source in manifest['sources']:
        symbol = source['series']
        name = symbol + ('.html.gz' if symbol == 'FED_JPY' else '.json.gz')
        payload = gzip.decompress((data_dir/'raw'/name).read_bytes())
        assert hashlib.sha256(payload).hexdigest() == source['response_sha256'], f'Raw hash mismatch: {symbol}'
        acquired[symbol] = dict(url=source['url'], retrieved_at_utc=source['retrieved_at_utc'], raw_sha256_verified=True)
        if symbol == 'FED_JPY':
            # Deliberately independent of fetch_long_term_data.FedRates.
            rates = {}
            for row_html in re.findall(r'<tr\b[^>]*>(.*?)</tr>', payload.decode(), re.I|re.S):
                cells = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',row_html,re.I|re.S)]
                if len(cells) != 2:
                    continue
                try:
                    date = dt.datetime.strptime(cells[0], '%d-%b-%y').date().isoformat()
                except ValueError:
                    continue
                if start <= date <= end and cells[1] != 'ND':
                    assert date not in rates
                    rates[date] = float(cells[1])
            expected['usd_jpy'] = rates
        else:
            response = json.loads(payload)['chart']
            assert response['error'] is None and len(response['result']) == 1
            result = response['result'][0]
            assert result['meta']['currency'] == 'USD'
            times = result['timestamp']
            close = result['indicators']['quote'][0]['close']
            adjusted = result['indicators']['adjclose'][0]['adjclose']
            assert len(times) == len(close) == len(adjusted)
            dates = [dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in times]
            assert len(set(dates)) == len(dates)
            prefix = {'BTC-USD':'btc','SPY':'spy','ACWI':'acwi'}[symbol]
            close_name = 'btc_usd' if prefix == 'btc' else prefix+'_close_usd'
            expected[close_name] = {d:v for d,v in zip(dates,close) if start <= d <= end and v is not None}
            if prefix != 'btc':
                expected[prefix+'_adjusted_usd'] = {d:v for d,v in zip(dates,adjusted) if start <= d <= end and v is not None}
                events = result.get('events',{})
                assert not events.get('splits'), 'Split handling not supported by this snapshot audit'
                dividends = {dt.datetime.fromtimestamp(e['date'],dt.timezone.utc).date().isoformat():e['amount'] for e in events['dividends'].values()}
                factor = 1.0
                errors = []
                # Each daily adjustment factor must follow the cash-distribution events.
                for i in range(len(times)-1,0,-1):
                    if dates[i] in dividends:
                        factor *= 1-dividends[dates[i]]/close[i-1]
                    observed = (adjusted[i-1]/close[i-1])/(adjusted[-1]/close[-1])
                    errors.append(abs(factor/observed-1))
                assert max(errors) < 0.000002, 'Daily adjustment reconstruction failed'
                ex_date_wealth = 1.0
                for i in range(1,len(times)):
                    ex_date_wealth *= (close[i]+dividends.get(dates[i],0))/close[i-1]
                corporate[symbol] = dict(split_events=0,dividend_events=len(dividends),maximum_daily_adjustment_relative_error=max(errors),
                                        adjusted_close_growth=adjusted[-1]/adjusted[0],
                                        hypothetical_ex_date_close_reinvestment_growth=ex_date_wealth,
                                        adjusted_relative_to_hypothetical=adjusted[-1]/adjusted[0]/ex_date_wealth-1,
                                        note='Sensitivity only: assumes reinvestment on ex-date at close before investor tax; not payment-date execution or realized holdings.')
    all_dates = sorted(set().union(*(set(values) for values in expected.values())))
    assert all_dates == [r['date'] for r in rows], 'CSV source-date union differs'
    count = 0
    for row in rows:
        for column, values in expected.items():
            value = values.get(row['date'])
            if value is None:
                assert row[column] == '', 'A missing source observation was filled'
            else:
                assert float(row[column]) == value, f'Raw-to-CSV mismatch: {column} {row["date"]}'
                count += 1
    return acquired, corporate, count


def independent_metrics(dates, values):
    high = values[0]
    drawdowns = []
    for value in values:
        high = max(high,value)
        drawdowns.append(value/high-1)
    trough = min(range(len(values)),key=drawdowns.__getitem__)
    peak = max(range(trough+1),key=values.__getitem__)
    recovered = next((i for i in range(trough+1,len(values)) if values[i] >= values[peak]),None)
    days = (dt.date.fromisoformat(dates[-1])-dt.date.fromisoformat(dates[0])).days
    growth = values[-1]/values[0]
    cagr = (growth.ln()*D('365.2425')/D(days)).exp()-1
    return dict(growth=growth,cagr=cagr,maximum_drawdown=drawdowns[trough],peak_date=dates[peak],trough_date=dates[trough],
                recovery_date=dates[recovered] if recovered is not None else None,
                peak_to_recovery_days=(dt.date.fromisoformat(dates[recovered])-dt.date.fromisoformat(dates[peak])).days if recovered is not None else None)


def audit(data_dir=DATA):
    manifest = json.loads((data_dir/'sources.json').read_text())
    payload = (data_dir/'observations.csv').read_bytes()
    assert hashlib.sha256(payload).hexdigest() == manifest['input_sha256']
    rows = csv_rows(payload)
    acquired,corporate,matched = verify_raw(data_dir,manifest,rows)
    required = ('btc_usd','spy_close_usd','spy_adjusted_usd','acwi_close_usd','acwi_adjusted_usd','usd_jpy')
    common = [row for row in rows if all(row[c] for c in required)]
    dates = [r['date'] for r in common]
    assert dates[0] == manifest['requested_start'] and dates[-1] == manifest['requested_end']
    published = json.loads((data_dir/'results.json').read_text())
    report = dict(start=dates[0],end=dates[-1],calendar_days=(dt.date.fromisoformat(dates[-1])-dt.date.fromisoformat(dates[0])).days,
                  common_dates=len(dates),raw_to_csv_values_verified=matched,source_verification=acquired,corporate_actions=corporate,assets={})
    assert len(common) == published['observations']
    with localcontext() as context:
        context.prec = 50
        for asset,column in COLUMNS.items():
            usd = [D(row[column]) for row in common]
            jpy = [D(row[column])*D(row['usd_jpy']) for row in common]
            record = {}
            for currency,values in [('usd',usd),('jpy',jpy)]:
                independently = independent_metrics(dates,values)
                stored = published['assets'][asset][currency]
                assert abs(independently['growth']-(D(str(stored['total_return']))+1)) < D('1e-11')
                assert abs(independently['cagr']-D(str(stored['cagr']))) < D('1e-11')
                assert abs(independently['maximum_drawdown']-D(str(stored['maximum_drawdown']))) < D('1e-11')
                for key in ('peak_date','trough_date','recovery_date','peak_to_recovery_days'):
                    assert independently[key] == stored[key], f'{asset} {currency} {key}'
                record[currency] = {k:str(v) if isinstance(v,D) else v for k,v in independently.items()}
            final = D('1000000')*jpy[-1]/jpy[0]
            assert abs(final-D(str(published['assets'][asset]['final_jpy']))) < D('0.000001')
            # Inverse wealth/CAGR equation, checked without the analysis module.
            t=D(report['calendar_days'])/D('365.2425')
            inverse=D('1000000')*((D(record['jpy']['cagr'])+1).ln()*t).exp()
            assert abs(inverse-final) < D('1e-30')
            record['final_jpy']=str(final)
            record['start_input_usd']=common[0][column]
            record['end_input_usd']=common[-1][column]
            report['assets'][asset]=record
    # Refetch is separate evidence and does not replace the original snapshot.
    fresh_dir=data_dir/'audit-refetch'
    fresh_manifest=json.loads((fresh_dir/'sources.json').read_text())
    fresh_payload=gzip.decompress((fresh_dir/'observations.csv.gz').read_bytes())
    assert hashlib.sha256(fresh_payload).hexdigest() == fresh_manifest['input_sha256']
    fresh_rows=csv_rows(fresh_payload)
    assert [r['date'] for r in fresh_rows] == [r['date'] for r in rows]
    differences={}
    for column in required:
        changed=[]
        for old,new in zip(rows,fresh_rows):
            assert bool(old[column])==bool(new[column]), 'Refetch missingness changed'
            if old[column] and old[column]!=new[column]:
                changed.append(abs(D(new[column])/D(old[column])-1))
        differences[column]=dict(changed_observations=len(changed),maximum_relative_difference=str(max(changed,default=D(0))))
    fresh_common=[r for r in fresh_rows if all(r[c] for c in required)]
    impact={}
    with localcontext() as context:
        context.prec=50
        for asset,column in COLUMNS.items():
            growth=(D(fresh_common[-1][column])*D(fresh_common[-1]['usd_jpy']))/(D(fresh_common[0][column])*D(fresh_common[0]['usd_jpy']))
            final=D('1000000')*growth
            impact[asset]=dict(refetched_final_jpy=str(final),difference_from_frozen_jpy=str(final-D(report['assets'][asset]['final_jpy'])))
    report['refetch']=dict(snapshot_identical=payload==fresh_payload,original_input_sha256=manifest['input_sha256'],refetched_input_sha256=fresh_manifest['input_sha256'],
                           original_retrieval={s['series']:s['retrieved_at_utc'] for s in manifest['sources']},
                           refetch_retrieval={s['series']:s['retrieved_at_utc'] for s in fresh_manifest['sources']},
                           differences=differences,endpoint_impact=impact,
                           cause='Unverified; do not attribute small adjusted-close differences to a specific cause.')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    report=audit()
    output=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    path=DATA/'audit.json'
    if args.check:
        assert path.read_text()==output,'Saved audit report differs'
    else:
        path.write_text(output)
    print(f'Independent audit passed: {report["common_dates"]} common dates, {report["raw_to_csv_values_verified"]} source values matched')
    for asset,r in report['assets'].items():
        print(asset,'JPY',r['final_jpy'],'CAGR',r['jpy']['cagr'],'MDD',r['jpy']['maximum_drawdown'])


if __name__=='__main__':
    main()
