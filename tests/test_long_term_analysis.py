import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from analyze_long_term import analyze, load_data, metrics, DATA
from fetch_long_term_data import parse_chart, parse_fed


class CalculationTests(unittest.TestCase):
    def test_cagr_uses_actual_days_and_drawdown_recovers_at_equality(self):
        dates = ['2020-01-01', '2020-04-01', '2020-07-01', '2021-01-01']
        r = metrics(dates, [100, 200, 100, 200])
        self.assertAlmostEqual(r['total_return'], 1)
        self.assertAlmostEqual(r['cagr'], 2**(365.2425/366)-1)
        self.assertEqual(r['maximum_drawdown'], -.5)
        self.assertEqual(r['recovery_date'], '2021-01-01')
        self.assertEqual(r['peak_to_recovery_days'], 275)
        self.assertEqual(r['trough_to_recovery_days'], 184)

    def test_unrecovered_and_new_peak_are_distinguished(self):
        r = metrics(['2020-01-01', '2020-01-02', '2020-01-03'], [100, 50, 75])
        self.assertIsNone(r['recovery_date'])
        self.assertIsNone(r['peak_to_recovery_days'])
        self.assertFalse(r['longest_underwater']['recovered'])
        self.assertEqual(r['longest_underwater']['days'], 2)
        flat = metrics(['2020-01-01', '2020-01-02'], [1, 1])
        self.assertEqual(flat['maximum_drawdown'], 0)
        self.assertIsNone(flat['longest_underwater'])

    def test_bad_inputs_fail(self):
        for dates, values in [(['2020-01-01']*2,[1,2]), (['2020-01-02','2020-01-01'],[1,2]), (['2020-01-01','2020-01-02'],[1,0]), (['2020-01-01','2020-01-02'],[1,float('nan')])]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                metrics(dates, values)

    def test_snapshot_results_and_article_tables_reproduce_offline(self):
        r = subprocess.run([sys.executable, str(ROOT/'scripts/analyze_long_term.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout+r.stderr)

    def test_daily_risk_and_annual_chain_independent_calculation(self):
        result, common = analyze()
        for key, column in [('btc','btc_usd'),('spy','spy_adjusted_usd'),('acwi','acwi_adjusted_usd')]:
            values = [float(r[column])*float(r['usd_jpy']) for r in common]
            brute_dd = min(v/max(values[:i+1])-1 for i,v in enumerate(values))
            self.assertAlmostEqual(result['assets'][key]['jpy']['maximum_drawdown'], brute_dd)
            annual_product = math.prod(1+r['returns'][key]['jpy'] for r in result['annual'])
            self.assertAlmostEqual(annual_product, values[-1]/values[0])
        self.assertEqual(result['observations'], 2486)
        self.assertEqual(result['btc_calendar_observations'], 3652)
        self.assertLessEqual(result['btc_calendar_usd']['maximum_drawdown'], result['assets']['btc']['usd']['maximum_drawdown'])
        self.assertTrue(result['annual'][0]['partial'])
        self.assertTrue(result['annual'][-1]['partial'])

    def test_hash_mismatch_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)
            (path/'observations.csv').write_text('date\n2020-01-01\n')
            (path/'sources.json').write_text((DATA/'sources.json').read_text())
            with self.assertRaises(ValueError):
                load_data(path)

    def test_source_parsers_fail_without_fabricating_prices(self):
        with self.assertRaises(ValueError):
            parse_chart(b'{"chart":{"error":{"code":"Not Found"},"result":null}}')
        with self.assertRaises(ValueError):
            parse_fed(b'<html><p>Temporarily unavailable</p></html>')


if __name__ == '__main__':
    unittest.main()
