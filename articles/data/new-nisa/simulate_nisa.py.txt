"""Reproducible hypothetical savings; no market data or forecasts.

python scripts/simulate_nisa.py [--check] [--plots]
Only optional chart regeneration needs matplotlib. CI uses the standard library.
"""
import argparse
import csv
from decimal import Decimal, ROUND_HALF_UP, localcontext
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'articles/data/new-nisa'
ARTICLE = ROOT / 'articles/new-nisa-beginners-guide.html'
MONTHLY = (10000, 30000, 50000)
RATES = (0, 3, 5, 7)
YEARS = (10, 20, 30)


def future_value(monthly, annual_percent, months):
    """End-of-month ordinary annuity; effective annual percentage rate."""
    if monthly < 0 or months < 0 or int(months) != months or annual_percent <= -100:
        raise ValueError('Invalid contribution, month count, or annual rate')
    with localcontext() as ctx:
        ctx.prec = 50
        p, r = Decimal(str(monthly)), Decimal(str(annual_percent)) / 100
        if r == 0:
            return p * months
        m = (1 + r) ** (Decimal(1) / 12) - 1
        return +(p * (((1 + m) ** months - 1) / m))


def yen(value):
    return int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def scenarios():
    return [dict(monthly_yen=p, years=y, annual_percent=r, principal_yen=p*y*12,
                 final_yen=yen(future_value(p, r, y*12)),
                 gain_yen=yen(future_value(p, r, y*12))-p*y*12)
            for p in MONTHLY for y in YEARS for r in RATES]


def payload():
    return dict(model='hypothetical-effective-annual-rate-month-end-v1',
                currency='JPY', initial_yen=0, contribution_timing='month-end',
                annual_rate_definition='effective; net of assumed ongoing fund costs',
                monthly_rate='(1 + annual_percent / 100) ** (1/12) - 1',
                withdrawals=False, rounding='half-up to integer yen at output only',
                scenarios=scenarios())


def table_html():
    parts = []
    for p in MONTHLY:
        label = f'毎月{p//10000}万円：10年・20年・30年の仮定計算（円）'
        rows = ''.join(f'<tr><th scope="row">{x["years"]}年</th><td>{x["annual_percent"]}%</td>'
                       f'<td>{x["principal_yen"]:,}</td><td>{x["final_yen"]:,}</td>'
                       f'<td>{x["gain_yen"]:+,}</td></tr>'
                       for x in scenarios() if x['monthly_yen'] == p)
        parts.append(f'<h3 id="monthly-{p}">毎月{p//10000}万円を積み立てる場合</h3>'
                     f'<div class="table-wrap" role="region" aria-label="{label}" tabindex="0">'
                     f'<table><caption>{label}</caption><thead><tr>'
                     '<th scope="col">期間</th><th scope="col">仮定年率</th>'
                     '<th scope="col">積立元本</th><th scope="col">最終資産額</th>'
                     '<th scope="col">元本との差額</th></tr></thead><tbody>' + rows + '</tbody></table></div>')
    return '\n'.join(parts)


def artifacts():
    data = json.dumps(payload(), ensure_ascii=False, indent=2) + '\n'
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(scenarios()[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(scenarios())
    return {'results.json': data, 'results.csv': output.getvalue(),
            'simulate_nisa.py.txt': Path(__file__).read_text(encoding='utf-8')}


def charts():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype': 'none', 'svg.hashsalt': 'nisa-v1', 'font.size': 12})
    plots = [('rate-comparison', [(30000, r, f'{r}%') for r in RATES],
              'Monthly JPY 30,000 / hypothetical annual rates'),
             ('contribution-comparison', [(p, 5, f'JPY {p:,}/month') for p in MONTHLY],
              'Hypothetical annual rate 5% / monthly contributions')]
    for name, series, title in plots:
        fig, ax = plt.subplots(figsize=(9, 5.4))
        for p, r, label in series:
            ax.plot([m/12 for m in range(361)],
                    [float(future_value(p, r, m))/10000 for m in range(361)],
                    label=label, linewidth=2.3)
        ax.set(xlabel='Years', ylabel='Asset value (JPY 10,000)', title=title, xlim=(0, 30), ylim=(0, None))
        ax.grid(alpha=.2)
        ax.legend(loc='upper left', fontsize=11)
        fig.tight_layout()
        fig.savefig(OUT / f'{name}.svg', metadata={'Date': None})
        fig.savefig(OUT / f'{name}.png', dpi=160, metadata={'Software': 'Topic base simulation'})
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--plots', action='store_true')
    args = parser.parse_args()
    expected = artifacts()
    article = ARTICLE.read_text(encoding='utf-8')
    updated, count = re.subn(r'<!-- NISA:START -->.*?<!-- NISA:END -->',
                            '<!-- NISA:START -->\n' + table_html() + '\n<!-- NISA:END -->',
                            article, flags=re.S)
    if count != 1:
        raise SystemExit('Exactly one simulation marker pair required')
    if args.check:
        for name, text in expected.items():
            if (OUT / name).read_text(encoding='utf-8') != text:
                raise SystemExit(f'Stale generated output: {name}')
        if updated != article:
            raise SystemExit('Stale article tables')
        print('36 scenarios, JSON/CSV and article tables reproduce exactly')
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, text in expected.items():
            (OUT / name).write_text(text, encoding='utf-8')
        ARTICLE.write_text(updated, encoding='utf-8')
    if args.plots:
        charts()


if __name__ == '__main__':
    main()
