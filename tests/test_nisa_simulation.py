"""Independent month-by-month audit of every published NISA scenario."""
from decimal import Decimal, localcontext
import json
import subprocess
import sys
import unittest
from scripts.simulate_nisa import ROOT, OUT, future_value, scenarios, yen


class NisaSimulationTests(unittest.TestCase):
    def test_all_36_with_independent_monthly_recurrence(self):
        rows = json.loads((OUT / 'results.json').read_text())['scenarios']
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({(x['monthly_yen'], x['years'], x['annual_percent']) for x in rows}), 36)
        with localcontext() as ctx:
            ctx.prec = 60
            for x in rows:
                # Separately implemented recurrence, using logarithm/exponential for rate.
                growth = ((1 + Decimal(x['annual_percent'])/100).ln()/12).exp()
                balance = Decimal(0)
                for _ in range(x['years']*12):
                    balance = balance * growth + x['monthly_yen']
                with self.subTest(scenario=x):
                    self.assertEqual(x['final_yen'], yen(balance))
                    self.assertEqual(x['gain_yen'], x['final_yen'] - x['principal_yen'])
                    self.assertEqual(x['principal_yen'], x['monthly_yen']*12*x['years'])
                    self.assertLessEqual(x['principal_yen'], 18000000)
                    self.assertLessEqual(x['monthly_yen']*12, 1200000)

    def test_zero_rate_one_month_and_negative_rate(self):
        self.assertEqual(future_value(10000, 0, 360), 3600000)
        self.assertEqual(yen(future_value(10000, 7, 1)), 10000)
        self.assertLess(future_value(10000, -5, 120), 1200000)
        self.assertEqual(future_value(10000, 3, 0), 0)
        for args in [(-1, 3, 12), (1, -100, 12), (1, 3, -1), (1, 3, 1.5)]:
            with self.assertRaises(ValueError):
                future_value(*args)

    def test_effective_annual_rate_not_divided_by_12(self):
        # A single month-end payment compounds for exactly 12 months by month 13.
        difference = future_value(10000, 7, 13) - future_value(10000, 7, 12)
        self.assertEqual(yen(difference), 10700)

    def test_published_artifacts_reproduce(self):
        subprocess.run([sys.executable, str(ROOT / 'scripts/simulate_nisa.py'), '--check'],
                       check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
