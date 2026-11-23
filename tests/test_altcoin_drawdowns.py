"""Independent audit of Issue 14's price history, publication and chart values."""
import csv
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
import math
import re
from pathlib import Path
import runpy
import tempfile
import unittest
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'articles/data/altcoin-drawdowns'
analysis = runpy.run_path(str(DATA / 'analyze.py'))


class AltcoinTests(unittest.TestCase):
    def setUp(self):
        self.prices = analysis['load']()
        self.saved = json.loads((DATA / 'results.json').read_text())

    def test_frozen_input_and_results(self):
        digest = hashlib.sha256((DATA / 'input.csv').read_bytes()).hexdigest()
        self.assertEqual(digest, json.loads((DATA / 'sources.json').read_text())['input_csv_sha256'])
        self.assertEqual(set(self.prices), {'BTC', 'ETH', 'XRP', 'LTC'})
        for s in self.prices.values():
            self.assertEqual(len(s), 826)
        self.assertEqual(analysis['results'](self.prices), self.saved)

    def test_all_peak_trough_pairs_and_first_recovery(self):
        for symbol, series in self.prices.items():
            for window, end in [('full', analysis['END']), ('first_half_2017', analysis['FIRST_HALF'])]:
                sample = [(d, float(p)) for d, p in series if d <= end]
                # Score absolute fractional loss for every chronological pair without a running maximum.
                loss, peak, trough = max(((1-q/p, a, b) for i, (a,p) in enumerate(sample)
                                          for b,q in sample[i+1:]), key=lambda x: x[0])
                row = self.saved[symbol][window]
                prices = dict(series)
                recovered = [d for d, p in series if d > trough and p >= prices[peak]]
                with self.subTest(symbol=symbol, window=window):
                    self.assertEqual((str(peak), str(trough)), (row['high_date'], row['low_date']))
                    self.assertEqual(round(-loss*100, 2), float(row['drawdown_pct']))
                    self.assertEqual(round(1000000*(1-loss)), int(row['bottom_yen']))
                    self.assertEqual(row['recovery'], str(min(recovered)) if recovered else None)
                    self.assertEqual(row['days_from_peak'], (min(recovered)-peak).days if recovered else None)
                    self.assertEqual(row['days_from_bottom'], (min(recovered)-trough).days if recovered else None)

    def test_recovery_at_equality_and_no_decline(self):
        first = analysis['START']
        series = [(first + timedelta(days=i), Decimal(x)) for i, x in enumerate([10, 10, 4, 4, 10])]
        row = analysis['episode'](series, first+timedelta(days=3))
        self.assertEqual((row['high_date'],row['low_date']), (str(first),str(first+timedelta(days=2))))
        self.assertEqual((row['days_from_peak'],row['days_from_bottom']), (4,2))
        self.assertIsNone(analysis['episode'](series[:2], first+timedelta(days=1)))

    def test_missing_duplicate_and_nonpositive_values_stop(self):
        lines = (DATA/'input.csv').read_text().splitlines()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'input.csv'
            for rows in (lines[:-1], lines+[lines[-1]], lines[:1]+['2017-01-01,BTC,0,1,2']+lines[2:]):
                path.write_text('\n'.join(rows)+'\n')
                with self.assertRaises(ValueError):
                    analysis['load'](path)

    def test_reported_values_and_figures(self):
        article = (ROOT/'articles/altcoin-drawdown-history.html').read_text()
        def labels(chart):
            root = ElementTree.parse(DATA / (chart+'.svg'))
            return {node.text for node in root.findall('.//{*}text')}
        for symbol, windows in self.saved.items():
            r = windows['full']
            self.assertIn(r['drawdown_pct']+'%',article)
            self.assertIn(str(abs(Decimal(r['drawdown_pct'])))+'%',labels('drawdown'))
            self.assertIn(f"{int(r['bottom_yen']):,}",labels('balance'))
            self.assertIn(str(windows['first_half_2017']['days_from_peak']),labels('recovery'))
            self.assertIn(symbol,labels('prices'))
            fixed = {str(d):p for d,p in self.prices[symbol]}
            loss = (fixed['2018-12-14']/fixed['2018-01-13']-1)*100
            self.assertIn(format(abs(loss),'.2f')+'%',article)
        with (ROOT/'articles/data/bitcoin-crash/observations.csv').open() as f:
            venues = {r['date']:Decimal(r['close']) for r in csv.DictReader(f)}
        btc = self.saved['BTC']['full']
        loss = (venues[btc['low_date']]/venues[btc['high_date']]-1)*100
        self.assertEqual(format(loss,'.2f'),'-83.43')


    def test_plotted_daily_series_match_input_on_log_axis(self):
        svg = ElementTree.parse(DATA/'prices.svg')
        y_ticks = {}
        x_ticks = {}
        for group in svg.findall('.//{*}g'):
            group_id = group.get('id', '')
            label = group.find('.//{*}text')
            if label is None:
                continue
            if group_id.startswith('ytick_'):
                line = group.find('.//{*}path')
                y_ticks[label.text] = float(line.get('d').split()[2])
            if group_id.startswith('xtick_'):
                x_ticks[label.text] = float(label.get('x'))
        decade = y_ticks['1,000'] - y_ticks['100']
        daily_step = (x_ticks['2018-01'] - x_ticks['2017-01']) / 365
        for symbol, series in self.prices.items():
            line = svg.find(f'.//*[@id="prices-{symbol}"]/{{*}}path')
            points = re.findall(r'[ML] ([0-9.]+) ([0-9.]+)', line.get('d'))
            self.assertEqual(len(points), len(series))
            for (x, y), (day, price) in zip(points, series):
                expected_x = x_ticks['2017-01'] + daily_step*(day-series[0][0]).days
                expected_y = y_ticks['100'] + decade*math.log10(float(price/series[0][1]))
                self.assertAlmostEqual(float(x), expected_x, places=4)
                self.assertAlmostEqual(float(y), expected_y, places=4)
