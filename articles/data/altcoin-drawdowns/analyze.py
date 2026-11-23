"""Offline, standard-library calculation from the attributed USD daily close CSV."""
import csv
import json
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = ('BTC', 'ETH', 'XRP', 'LTC')
START = date(2017, 1, 1)
END = date(2019, 4, 6)
FIRST_HALF = date(2017, 6, 30)


def load(path=HERE / 'input.csv'):
    prices = {symbol: {} for symbol in ASSETS}
    with path.open() as source:
        for row in csv.DictReader(source):
            day = date.fromisoformat(row['date'])
            series = prices[row['symbol']]
            values = [D(row[k]) for k in ('close_usd', 'volume_base', 'volume_usd')]
            if day in series or not all(v.is_finite() and v > 0 for v in values):
                raise ValueError(f'Duplicate or invalid observation: {row}')
            series[day] = values[0]
    calendar = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    for symbol in prices:
        if sorted(prices[symbol]) != calendar:
            raise ValueError(f'Incomplete calendar: {symbol}')
        prices[symbol] = sorted(prices[symbol].items())
    return prices


def rounded(value, unit='0.01'):
    return str(value.quantize(D(unit), rounding=ROUND_HALF_UP))


def episode(series, window_end):
    """Select extrema within window; follow the original high through final observation."""
    peak = series[0]
    worst_ratio = D(1)
    worst = None
    for day, price in series:
        if day > window_end:
            break
        if price > peak[1]:
            peak = day, price
        ratio = price / peak[1]
        if ratio < worst_ratio:
            worst_ratio = ratio
            worst = peak, (day, price)
    if worst is None:
        return None
    (high_day, high), (low_day, low) = worst
    last_day, last_close = series[-1]
    recovery = next((day for day, close in series if day > low_day and close >= high), None)
    return dict(high_date=str(high_day), high_usd=str(high), low_date=str(low_day), low_usd=str(low),
                drawdown_pct=rounded((worst_ratio-1)*100), decline_days=(low_day-high_day).days,
                recovery=str(recovery) if recovery else None,
                days_from_peak=(recovery-high_day).days if recovery else None,
                days_from_bottom=(recovery-low_day).days if recovery else None,
                days_observed_from_peak=(last_day-high_day).days,
                last_usd=str(last_close), last_vs_peak_pct=rounded((last_close/high-1)*100),
                bottom_yen=rounded(1000000*worst_ratio, '1'),
                rebound_needed_pct=rounded((1/worst_ratio-1)*100))


def results(prices):
    return {symbol: {'full': episode(series, END), 'first_half_2017': episode(series, FIRST_HALF)}
            for symbol, series in prices.items()}


if __name__ == '__main__':
    print(json.dumps(results(load()), indent=2))
