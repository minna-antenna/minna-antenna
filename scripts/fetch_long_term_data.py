#!/usr/bin/env python3
"""Explicit one-off acquisition for article 4. Never called by RSS or deployment."""
import argparse
import csv
import datetime as dt
import hashlib
from html.parser import HTMLParser
import io
import json
import math
from pathlib import Path
import urllib.parse
import urllib.request

START, END = '2016-10-31', '2026-10-30'
FED_URL = 'https://www.federalreserve.gov/releases/h10/hist/dat00_ja.htm'
FIELDS = ['date', 'btc_usd', 'spy_close_usd', 'spy_adjusted_usd', 'acwi_close_usd', 'acwi_adjusted_usd', 'usd_jpy']


class FedRates(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.rows, self.cells, self.cell = [], None, None
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.cells = []
        if tag in ('td', 'th') and self.cells is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.cells.append(''.join(self.cell).strip())
            self.cell = None
        if tag == 'tr' and self.cells is not None:
            self.rows.append(self.cells)
            self.cells = None


def chart_url(symbol):
    start = int(dt.datetime.fromisoformat(START).replace(tzinfo=dt.timezone.utc).timestamp())
    end = int((dt.datetime.fromisoformat(END) + dt.timedelta(days=1)).replace(tzinfo=dt.timezone.utc).timestamp())
    return 'https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(symbol, safe='') + '?' + urllib.parse.urlencode(dict(period1=start, period2=end, interval='1d', events='div,splits'))


def parse_chart(raw):
    data = json.loads(raw)['chart']
    if data.get('error') or not data.get('result'):
        raise ValueError('Chart response has no data')
    result = data['result'][0]
    if result['meta']['currency'] != 'USD':
        raise ValueError('Unexpected quote currency')
    closes = result['indicators']['quote'][0]['close']
    adjusted = result['indicators']['adjclose'][0]['adjclose']
    times = result['timestamp']
    if not len(times) == len(closes) == len(adjusted):
        raise ValueError('Mismatched array lengths')
    records = {}
    for stamp, close, adj in zip(times, closes, adjusted):
        day = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).date().isoformat()
        if not START <= day <= END or close is None or adj is None:
            continue
        if day in records or not all(math.isfinite(x) and x > 0 for x in (close, adj)):
            raise ValueError('Duplicate date or invalid price')
        records[day] = (close, adj)
    if not records or min(records) != START or max(records) != END:
        raise ValueError('Requested endpoints are missing; no extrapolation allowed')
    return records, result['meta']['exchangeTimezoneName']


def parse_fed(raw):
    parser = FedRates(raw.decode('utf-8'))
    records = {}
    for row in parser.rows:
        if len(row) != 2:
            continue
        try:
            day = dt.datetime.strptime(row[0], '%d-%b-%y').date().isoformat()
        except ValueError:
            continue
        if not START <= day <= END or row[1] == 'ND':
            continue
        value = float(row[1])
        if day in records or not math.isfinite(value) or value <= 0:
            raise ValueError('Invalid Fed FX record')
        records[day] = value
    if not records or min(records) != START or max(records) != END:
        raise ValueError('Fed FX endpoints are missing')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New destination directory; never overwrite the frozen snapshot')
    parser.add_argument('--cached-raw', type=Path, help='Reuse retained acquisition responses instead of downloading')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output directory already exists; frozen data must not be overwritten')
    sources, raw_data = [], {}
    urls = {symbol: chart_url(symbol) for symbol in ('BTC-USD', 'SPY', 'ACWI')}
    urls['FED_JPY'] = FED_URL
    # Validate all sources before creating any final output.
    for name, url in urls.items():
        if args.cached_raw:
            path = args.cached_raw / (name + '.raw')
            raw = path.read_bytes()
            retrieved = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat()
        else:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=40) as response:
                raw = response.read(8_000_000)
            retrieved = dt.datetime.now(dt.timezone.utc).isoformat()
        raw_data[name] = raw
        sources.append(dict(series=name, url=url, retrieved_at_utc=retrieved, response_sha256=hashlib.sha256(raw).hexdigest()))
    charts = {}
    for symbol in ('BTC-USD', 'SPY', 'ACWI'):
        charts[symbol], zone = parse_chart(raw_data[symbol])
        entry = next(s for s in sources if s['series'] == symbol)
        entry.update(rows=len(charts[symbol]), provider_timezone=zone)
        if symbol != 'BTC-USD':
            response = json.loads(raw_data[symbol])['chart']['result'][0]
            if response.get('events', {}).get('splits'):
                raise ValueError('Split adjustment requires separate validation')
            times = response['timestamp']
            prices = response['indicators']['quote'][0]['close']
            adjusted = response['indicators']['adjclose'][0]['adjclose']
            factor = 1.0
            dividends = response['events']['dividends'].values()
            for event in dividends:
                i = next(i for i, stamp in enumerate(times) if stamp >= event['date'])
                if i:
                    factor *= 1 - event['amount'] / prices[i-1]
            provider_factor = (adjusted[0]/prices[0])/(adjusted[-1]/prices[-1])
            error = factor/provider_factor - 1
            if abs(error) > 1e-5:
                raise ValueError('Dividend events do not reproduce adjustment factor')
            entry['adjustment_validation'] = dict(dividend_events=len(dividends), reconstructed_factor=factor, provider_factor=provider_factor, relative_error=error)

    fx = parse_fed(raw_data['FED_JPY'])
    sources[-1]['rows'] = len(fx)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader()
    dates = sorted(set(fx).union(*(set(v) for v in charts.values())))
    for day in dates:
        row = dict(date=day)
        for symbol, prefix in [('BTC-USD', 'btc'), ('SPY', 'spy'), ('ACWI', 'acwi')]:
            if day in charts[symbol]:
                close, adj = charts[symbol][day]
                if prefix == 'btc':
                    row['btc_usd'] = format(close, '.17g')
                else:
                    row[prefix + '_close_usd'] = format(close, '.17g')
                    row[prefix + '_adjusted_usd'] = format(adj, '.17g')
        if day in fx:
            row['usd_jpy'] = format(fx[day], '.17g')
        writer.writerow(row)
    payload = buffer.getvalue().encode()
    manifest = dict(requested_start=START, requested_end=END, input_sha256=hashlib.sha256(payload).hexdigest(), sources=sources,
                    excluded_attempts=[dict(url='https://fred.stlouisfed.org/graph.csv?id=DEXJPUS&cosd=2016-10-31&coed=2026-10-30', result='HTTP 404; not used. Used Federal Reserve H.10 source instead.')],
                    note='Snapshot of observed values. Blanks are missing observations, never filled. Yahoo adjusted ETF closes are distribution/split-adjusted market prices, not official index total return series or NAV.')
    args.output.mkdir(parents=True)
    (args.output / 'observations.csv').write_bytes(payload)
    (args.output / 'sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print('Saved observed data:', len(dates), 'dates;', len(fx), 'Fed FX observations')


if __name__ == '__main__':
    main()
