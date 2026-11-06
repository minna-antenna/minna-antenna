#!/usr/bin/env python3
"""Offline, deterministic analysis for article 4; standard library except optional plots."""
import argparse
import csv
import datetime as dt
import hashlib
import html
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'articles/data/bitcoin-vs-stocks'
ARTICLE = ROOT / 'articles/bitcoin-vs-stocks-long-term.html'
START_MARK, END_MARK = '<!-- ANALYSIS:START -->', '<!-- ANALYSIS:END -->'
SERIES = {'btc': ('BTC', 'btc_usd'), 'spy': ('米国株式ETF SPY', 'spy_adjusted_usd'), 'acwi': ('全世界株式ETF ACWI', 'acwi_adjusted_usd')}


def metrics(dates, values):
    if len(dates) != len(values) or len(dates) < 2:
        raise ValueError('At least two paired observations required')
    if dates != sorted(set(dates)) or any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Dates must increase and prices must be finite and positive')
    parsed = [dt.date.fromisoformat(x) for x in dates]
    days = (parsed[-1] - parsed[0]).days
    if days <= 0:
        raise ValueError('Zero time span')
    peak = 0
    deepest_peak = deepest_trough = 0
    worst = 0.0
    episodes = []
    for i, value in enumerate(values):
        if value >= values[peak]:
            if i > peak + 1:
                episodes.append(dict(peak=dates[peak], recovery=dates[i], days=(parsed[i] - parsed[peak]).days, recovered=True))
            peak = i
        drawdown = value / values[peak] - 1
        if drawdown < worst:
            worst, deepest_peak, deepest_trough = drawdown, peak, i
    if peak < len(values) - 1:
        episodes.append(dict(peak=dates[peak], recovery=None, days=(parsed[-1] - parsed[peak]).days, recovered=False))
    recovery = next((i for i in range(deepest_trough + 1, len(values)) if values[i] >= values[deepest_peak]), None) if worst < 0 else 0
    ratio = values[-1] / values[0]
    return dict(total_return=ratio-1, cagr=ratio ** (365.2425 / days)-1, maximum_drawdown=worst,
                peak_date=dates[deepest_peak], trough_date=dates[deepest_trough],
                recovery_date=dates[recovery] if recovery is not None else None,
                peak_to_recovery_days=(parsed[recovery]-parsed[deepest_peak]).days if recovery is not None else None,
                trough_to_recovery_days=(parsed[recovery]-parsed[deepest_trough]).days if recovery is not None else None,
                ending_drawdown=values[-1]/values[peak]-1,
                longest_underwater=max(episodes, key=lambda e:e['days']) if episodes else None)


def load_data(data_dir=DATA):
    payload = (data_dir / 'observations.csv').read_bytes()
    manifest = json.loads((data_dir / 'sources.json').read_text())
    if hashlib.sha256(payload).hexdigest() != manifest['input_sha256']:
        raise ValueError('Input snapshot hash mismatch')
    rows = list(csv.DictReader(io.StringIO(payload.decode())))
    dates = [row['date'] for row in rows]
    if dates != sorted(set(dates)):
        raise ValueError('Input dates are duplicated or unordered')
    for row in rows:
        dt.date.fromisoformat(row['date'])
        for key, value in row.items():
            if key != 'date' and value and (not math.isfinite(float(value)) or float(value) <= 0):
                raise ValueError('Invalid observation')
    required = ('btc_usd', 'spy_close_usd', 'spy_adjusted_usd', 'acwi_close_usd', 'acwi_adjusted_usd', 'usd_jpy')
    common = [row for row in rows if all(row.get(k) for k in required)]
    if not common or common[0]['date'] != manifest['requested_start'] or common[-1]['date'] != manifest['requested_end']:
        raise ValueError('Common endpoints missing; no forward filling or extrapolation')
    if len(common) < 2400:
        raise ValueError('Insufficient common observations for this frozen ten-year window')
    return rows, common, manifest


def analyze(data_dir=DATA):
    rows, common, manifest = load_data(data_dir)
    dates = [r['date'] for r in common]
    fx = [float(r['usd_jpy']) for r in common]
    result = dict(start=dates[0], end=dates[-1], calendar_days=(dt.date.fromisoformat(dates[-1])-dt.date.fromisoformat(dates[0])).days,
                  observations=len(common), snapshot_sha256=manifest['input_sha256'], initial_jpy=1_000_000,
                  fx_start=fx[0], fx_end=fx[-1], assets={}, annual=[])
    values_by_asset = {}
    for key, (label, column) in SERIES.items():
        usd = [float(r[column]) for r in common]
        jpy = [v*rate for v, rate in zip(usd, fx)]
        price_column = 'btc_usd' if key == 'btc' else key + '_close_usd'
        price = [float(r[price_column]) for r in common]
        result['assets'][key] = dict(label=label, start_price_usd=price[0], end_price_usd=price[-1], price_return_usd=price[-1]/price[0]-1,
                                    usd=metrics(dates, usd), jpy=metrics(dates,jpy), final_jpy=1_000_000*jpy[-1]/jpy[0])
        values_by_asset[key] = (usd, jpy)
    baseline = 0
    for year in range(int(dates[0][:4]), int(dates[-1][:4])+1):
        end = max(i for i,d in enumerate(dates) if d[:4] == str(year))
        record = dict(year=year, start=dates[baseline], end=dates[end], partial=year in (int(dates[0][:4]), int(dates[-1][:4])), returns={})
        for key, (usd,jpy) in values_by_asset.items():
            record['returns'][key] = dict(usd=usd[end]/usd[baseline]-1, jpy=jpy[end]/jpy[baseline]-1)
        result['annual'].append(record)
        baseline = end
    btc_rows = [r for r in rows if r['btc_usd']]
    result['btc_calendar_usd'] = metrics([r['date'] for r in btc_rows], [float(r['btc_usd']) for r in btc_rows])
    result['btc_calendar_observations'] = len(btc_rows)
    return result, common


def pct(value):
    return f'{value*100:+.2f}%'


def table(caption, headers, rows):
    head = ''.join(f'<th scope="col">{html.escape(h)}</th>' for h in headers)
    body = ''.join('<tr>'+''.join(f'<{ "th scope=\"row\"" if i==0 else "td"}>{html.escape(str(cell))}</{"th" if i==0 else "td"}>' for i,cell in enumerate(row))+'</tr>' for row in rows)
    return f'<div class="table-wrap" role="region" aria-label="{html.escape(caption)}" tabindex="0"><table><caption>{html.escape(caption)}</caption><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_tables(result):
    assets = result['assets']
    summary = table('同じ観測日で比較した約10年間の結果', ['対象','累積収益率 USD','CAGR USD','100万円の期末額 JPY','CAGR JPY','最大DD JPY'],
                    [(a['label'],pct(a['usd']['total_return']),pct(a['usd']['cagr']),f"{a['final_jpy']:,.0f}円",pct(a['jpy']['cagr']),pct(a['jpy']['maximum_drawdown'])) for a in assets.values()])
    prices = table('価格だけの変化と、分配金調整後の変化（米ドル建て）', ['対象','開始日価格 USD','終了日価格 USD','価格のみ','調整後系列'],
                   [(a['label'],f"{a['start_price_usd']:,.4f}",f"{a['end_price_usd']:,.4f}",pct(a['price_return_usd']),pct(a['usd']['total_return'])) for a in assets.values()])
    risks = table('最大下落と、その下落前の高値を初めて回復した日（円換算）', ['対象','最大DD USD','最大DD JPY','下落前の高値','底値','回復日','高値→回復','底値→回復'],
                  [(a['label'],pct(a['usd']['maximum_drawdown']),pct(a['jpy']['maximum_drawdown']),a['jpy']['peak_date'],a['jpy']['trough_date'],a['jpy']['recovery_date'] or '期間内未回復',str(a['jpy']['peak_to_recovery_days'])+'日' if a['jpy']['peak_to_recovery_days'] is not None else '未回復',str(a['jpy']['trough_to_recovery_days'])+'日' if a['jpy']['trough_to_recovery_days'] is not None else '未回復') for a in assets.values()])
    ongoing = table('最長の高値未回復期間と期末時点の状態（円換算）',['対象','最長期間の高値日','最長期間の回復日','高値からの暦日数','期末の直近高値からの下落'],
                    [(a['label'],a['jpy']['longest_underwater']['peak'],a['jpy']['longest_underwater']['recovery'] or '期間内未回復',str(a['jpy']['longest_underwater']['days'])+'日'+('（期末まで）' if not a['jpy']['longest_underwater']['recovered'] else ''),pct(a['jpy']['ending_drawdown'])) for a in assets.values()])
    annual = table('年別騰落率（円換算・共通観測日、両端年は部分期間）',['年','比較開始日','比較終了日','BTC','SPY','ACWI'],
                   [(str(r['year'])+('（部分）' if r['partial'] else ''),r['start'],r['end'],*(pct(r['returns'][k]['jpy']) for k in SERIES)) for r in result['annual']])
    return '\n'.join(['<h3 id="returns">累積リターン・CAGR・100万円の比較</h3>',summary,'<h3 id="price-only">配当を含めるかで結果は変わる</h3>',prices,'<h3 id="drawdown-data">最大ドローダウンと回復までの期間</h3>',risks,'<h3 id="underwater">最長の未回復期間も別に見る</h3>',ongoing,'<h3 id="annual">年間騰落率と部分期間</h3>',annual])


def plot(common, output=DATA):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    plt.rcParams.update({'svg.fonttype':'none','font.family':'DejaVu Sans','svg.hashsalt':'topic-base-article4','axes.spines.top':False,'axes.spines.right':False})
    dates = [dt.date.fromisoformat(r['date']) for r in common]
    colors = ['#996307','#176456','#296da3']
    fig, (ax, ddax) = plt.subplots(2,1,figsize=(9,7),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    for (key,(label,column)),color in zip(SERIES.items(),colors):
        vals = [float(r[column])*float(r['usd_jpy']) for r in common]
        wealth = [1_000_000*v/vals[0] for v in vals]
        peak = vals[0];dd=[]
        for v in vals:
            peak=max(peak,v);dd.append(100*(v/peak-1))
        ax.plot(dates,wealth,label=key.upper(),color=color,linewidth=1.1)
        ddax.plot(dates,dd,color=color,linewidth=0.9)
    ax.set_yscale('log');ax.set_ylabel('JPY (log scale)');ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x/1_000_000:g}m'))
    ax.set_title('JPY value of an initial JPY 1,000,000 | 2016-10-31 to 2026-10-30',fontsize=10)
    ax.legend(loc='upper left');ddax.set_ylabel('Drawdown (%)');ddax.set_ylim(-100,5)
    ddax.xaxis.set_major_locator(mdates.YearLocator(2));ddax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    for axis in (ax,ddax):axis.grid(alpha=.2);axis.margins(x=0)
    fig.tight_layout();fig.savefig(output/'wealth-and-drawdown.svg',metadata={'Date':None,'Creator':'Topic Base / Matplotlib'})
    fig.savefig(output/'wealth-and-drawdown.png', dpi=160, metadata={'Software':'Topic Base / Matplotlib'})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify frozen JSON and article tables, without modifying files or using network')
    parser.add_argument('--plots', action='store_true', help='Also render the static SVG (requires matplotlib)')
    args = parser.parse_args()
    result, common = analyze()
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    fragment = render_tables(result)
    source = ARTICLE.read_text()
    if source.count(START_MARK)!=1 or source.count(END_MARK)!=1:
        raise ValueError('Article analysis markers missing or duplicated')
    expected = source[:source.index(START_MARK)+len(START_MARK)]+'\n'+fragment+'\n'+source[source.index(END_MARK):]
    if args.check:
        if (DATA/'results.json').read_text()!=serialized or source!=expected:
            raise ValueError('Analysis outputs differ from frozen data; regenerate explicitly')
    else:
        (DATA/'results.json').write_text(serialized)
        ARTICLE.write_text(expected)
    if args.plots:
        plot(common)
    print(f'Analysis verified: {result["start"]} to {result["end"]}, {result["observations"]} common dates')


if __name__ == '__main__':
    main()
