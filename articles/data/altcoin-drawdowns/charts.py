"""Build standalone SVG charts (requires matplotlib; core analysis needs only Python)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from analyze import HERE, START, END, load, results

COLORS = {'ETH': '#00766c', 'LTC': '#86549a', 'XRP': '#286698', 'BTC': '#a34b0e'}
SOURCE = 'Ghent Cryptocurrency Dataset / CryptoCompare · CC BY-SA 4.0'
matplotlib.rcParams.update({'svg.fonttype': 'none', 'svg.hashsalt': 'topic-kichi-14',
                            'path.simplify': False, 'font.size': 12, 'axes.spines.top': False, 'axes.spines.right': False})


def save(fig, filename, period):
    fig.subplots_adjust(left=.14, right=.97, bottom=.27, top=.94)
    fig.text(.02, .10, period, fontsize=10)
    fig.text(.02, .035, SOURCE, fontsize=9)
    output = HERE / filename
    fig.savefig(output, metadata={'Date': None})
    output.write_text('\n'.join(line.rstrip() for line in output.read_text().splitlines()) + '\n')
    plt.close(fig)


def draw():
    prices = load()
    report = results(prices)
    symbols = sorted(prices, key=lambda s: float(report[s]['full']['drawdown_pct']))
    span = f'{START} — {END} · daily USD close'
    for key, name, unit in [('drawdown_pct', 'drawdown.svg', 'Loss from peak (%)'),
                            ('bottom_yen', 'balance.svg', 'Balance at trough (JPY)')]:
        fig, ax = plt.subplots(figsize=(5.6, 3.65))
        vals = [abs(float(report[s]['full'][key])) for s in symbols]
        bars = ax.barh(symbols, vals, color=[COLORS[s] for s in symbols])
        ax.invert_yaxis()
        ax.set_xlabel(unit)
        ax.set_xlim(0, 118 if key == 'drawdown_pct' else 220000)
        ax.bar_label(bars, labels=[f'{v:.2f}%' if key == 'drawdown_pct' else f'{v:,.0f}' for v in vals], padding=4)
        save(fig, name, span)

    fig, ax = plt.subplots(figsize=(5.6, 4.1))
    for s, series in prices.items():
        ax.plot([d for d, _ in series], [float(100*p/series[0][1]) for _, p in series],
                label=s, color=COLORS[s], lw=1.2, gid='prices-'+s)
    ax.set_yscale('log')
    ax.set_ylabel('Price index (start = 100, log scale)')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.legend(ncol=4, fontsize=10)
    ax.grid(axis='y', alpha=.25)
    save(fig, 'prices.svg', span)

    fig, ax = plt.subplots(figsize=(5.6, 3.65))
    window = 'first_half_2017'
    periods = [report[s][window] for s in symbols]
    falling = [r['decline_days'] for r in periods]
    recovering = [r['days_from_bottom'] for r in periods]
    ax.barh(symbols, falling, label='Peak to trough', color='#536b7a')
    bars = ax.barh(symbols, recovering, left=falling, label='Trough to recovery', color='#168277')
    ax.bar_label(bars, labels=[str(r['days_from_peak']) for r in periods], padding=4)
    ax.legend(fontsize=9, loc='lower right')
    ax.set_xlabel('Calendar days to first close at or above peak')
    ax.set_xlim(0, 210)
    ax.invert_yaxis()
    save(fig, 'recovery.svg', 'Peaks and troughs: 2017 H1 · follow-up to 2019-04-06')


if __name__ == '__main__':
    draw()
