"""Article 7 calculations and a deliberately unwaived source-consistency gate."""
import json,subprocess,sys,unittest
from scripts.calculate_crypto_tax import ROOT,DATA,annual,MODELS,basic_deduction,income_tax,calculate,national_tax_components
from scripts.audit_crypto_tax import audit
from test_article_integrity import Page,BASE
import xml.etree.ElementTree as ET


class CryptoTaxTests(unittest.TestCase):
    def test_independent_24_scenarios(self):
        result=audit();self.assertEqual(result['scenarios'],24);self.assertEqual(result['checks'],192)

    def test_tables_csv_json_code_reproduce(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/calculate_crypto_tax.py'),'--check'],check=True,capture_output=True,text=True)

    def test_official_example_must_be_internally_consistent_before_publication(self):
        evidence=json.loads((DATA/'source-audit.json').read_text())['blockers'][0]
        calculated=income_tax(evidence['taxable_income_yen'])
        self.assertEqual(evidence['stated_income_tax_yen'],calculated)
        # The legal base is after eligible tax credits. Equality with assessed
        # income tax is valid only when zero credits are actually established.
        credit=evidence['documented_pre_reconstruction_credit_yen']
        self.assertIsNotNone(credit,
            'PUBLICATION BLOCKED: No.2260 does not document the cause of the 27,000-yen gap. Do not invent a credit or assume zero.')
        parts=national_tax_components(evidence['taxable_income_yen'],pre_reconstruction_credit_yen=credit)
        self.assertEqual(evidence['stated_reconstruction_base_yen'],parts['base_income_tax_yen'])
        self.assertEqual(evidence['stated_reconstruction_tax_yen'],parts['reconstruction_tax_yen'])
        self.assertEqual(json.loads((DATA/'source-audit.json').read_text())['status'],'passed',
                         'Official clarification and applicability audit are required before release')

    def test_deduction_thresholds_depend_on_total_income_and_year(self):
        self.assertEqual(basic_deduction(3360000,2025),880000)
        self.assertEqual(basic_deduction(3360001,2025),680000)
        self.assertEqual(basic_deduction(4890000,2026),1040000)
        self.assertEqual(basic_deduction(4890001,2026),670000)
        self.assertEqual(basic_deduction(6550001,2026),620000)
        with self.assertRaises(ValueError):basic_deduction(100,2027)
        with self.assertRaises(ValueError):annual(MODELS[0],-1,2026)

    def test_rounding_and_marginal_rate_bracket_boundaries(self):
        self.assertEqual(income_tax(1950000),97500)
        self.assertEqual(income_tax(1949999),97450)
        self.assertEqual(income_tax(7000000),974000)
        for row in calculate():
            self.assertEqual(row['national_payment_increase_yen']%100,0)
            self.assertEqual(row['resident_income_levy_increase_yen'],row['crypto_profit_yen']//10)
            self.assertEqual(row['with_crypto']['basic_deduction_yen'],basic_deduction(row['salary_income_yen']+row['crypto_profit_yen'],row['tax_year']))

    def test_preview_registration_and_reciprocal_links(self):
        name='crypto-tax-japan-guide.html';page=Page(ROOT/'articles'/name)
        self.assertEqual(Page(ROOT/'index.html').hrefs.count('./articles/'+name),1)
        urls=[n.text for n in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')]
        self.assertEqual(urls.count(BASE+'articles/'+name),1)
        for other in ['crypto-eth-sol-xrp-comparison.html','bitcoin-vs-stocks-long-term.html','new-nisa-beginners-guide.html','sp500-vs-all-country.html']:
            self.assertIn('./'+other,page.hrefs)
            self.assertEqual(Page(ROOT/'articles'/other).hrefs.count('./'+name),1)
        self.assertEqual(page.meta['robots'],'noindex,nofollow')

    def test_no_credit_example_has_974000_base_and_20454_surtax(self):
        result=national_tax_components(7000000,pre_reconstruction_credit_yen=0)
        self.assertEqual(result['assessed_income_tax_yen'],974000)
        self.assertEqual(result['base_income_tax_yen'],974000)
        self.assertEqual(result['reconstruction_tax_yen'],20454)

    def test_hypothetical_27000_credit_explains_arithmetic_not_source_fact(self):
        result=national_tax_components(7000000,pre_reconstruction_credit_yen=27000)
        self.assertEqual(result['assessed_income_tax_yen'],974000)
        self.assertEqual(result['base_income_tax_yen'],947000)
        self.assertEqual(result['reconstruction_tax_yen'],19887)
        evidence=json.loads((DATA/'source-audit.json').read_text())['blockers'][0]
        self.assertIsNone(evidence['documented_pre_reconstruction_credit_yen'])

    def test_unknown_or_invalid_credit_is_not_coerced_to_zero(self):
        for credit in [None,-1,'27000']:
            with self.assertRaises(ValueError):
                national_tax_components(7000000,pre_reconstruction_credit_yen=credit)

    def test_nta1000_2026_example_and_zero_credit_model_scope(self):
        result=national_tax_components(1240000,pre_reconstruction_credit_yen=0)
        self.assertEqual(result['assessed_income_tax_yen'],62000)
        self.assertEqual(result['base_income_tax_yen'],62000)
        self.assertEqual(result['reconstruction_tax_yen'],1302)
        self.assertEqual(result['national_annual_yen'],63300)
        for row in calculate():
            for record in [row['baseline'],row['with_crypto']]:
                self.assertEqual(record['pre_reconstruction_credit_yen'],0)
                self.assertEqual(record['assessed_income_tax_yen'],record['base_income_tax_yen'])
