"""Article 7 calculations and fail-closed verification of the authorities actually used."""
import json,subprocess,sys,unittest,tempfile
from unittest.mock import patch
from scripts import audit_crypto_tax as audit_module
from scripts.verify_crypto_tax_sources import verify
from scripts.calculate_crypto_tax import ROOT,DATA,ARTICLE,annual,MODELS,basic_deduction,income_tax,calculate,national_tax_components
from scripts.audit_crypto_tax import audit
from test_article_integrity import Page,BASE
import xml.etree.ElementTree as ET


class CryptoTaxTests(unittest.TestCase):
    def test_independent_24_scenarios(self):
        result=audit();self.assertEqual(result['scenarios'],24);self.assertEqual(result['checks'],192);self.assertEqual(result['basis_checks'],96);self.assertEqual(result['full_field_checks'],624)
        self.assertEqual(json.loads((DATA/'calculation-audit.json').read_text()),result)

    def test_independent_audit_rejects_changed_annual_fields_and_deltas(self):
        original=json.loads((DATA/'results.json').read_text())
        for field in ['taxable_income_yen','base_income_tax_yen','reconstruction_tax_yen','resident_income_levy_yen','total_increase_yen']:
            data=json.loads(json.dumps(original));row=data['scenarios'][0]
            record=row if field=='total_increase_yen' else row['with_crypto']
            record[field]+=1
            with tempfile.TemporaryDirectory() as tmp:
                from pathlib import Path
                (Path(tmp)/'results.json').write_text(json.dumps(data))
                with patch.object(audit_module,'DATA',Path(tmp)):
                    with self.assertRaises(AssertionError):audit_module.audit()

    def test_tables_csv_json_code_reproduce(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/calculate_crypto_tax.py'),'--check'],check=True,capture_output=True,text=True)

    def test_used_official_authorities_must_be_consistent_before_publication(self):
        result=verify()
        self.assertEqual(result['calculation_authorities'],8)
        self.assertEqual(result['primary_evidence_records'],13)
        self.assertEqual(result['excluded_inconsistent_examples'],1)

    def test_source_gate_rejects_missing_evidence_unresolved_scope_and_reintroduced_source(self):
        evidence=json.loads((DATA/'rule-evidence.json').read_text())
        evidence['evidence'][0]['excerpt']+=' unexpected change'
        with self.assertRaises(ValueError):verify(evidence=evidence)
        evidence=json.loads((DATA/'rule-evidence.json').read_text())
        evidence['evidence']=evidence['evidence'][1:]
        with self.assertRaises(ValueError):verify(evidence=evidence)
        audit=json.loads((DATA/'source-audit.json').read_text())
        audit['unresolved_release_issues']=['unknown applicability']
        with self.assertRaises(ValueError):verify(audit=audit)
        audit=json.loads((DATA/'source-audit.json').read_text())
        audit['applicability']['crypto_separate_tax_used']=True
        with self.assertRaises(ValueError):verify(audit=audit)
        with self.assertRaises(ValueError):verify(article=ARTICLE.read_text()+'https://www.nta.go.jp/taxes/shiraberu/taxanswer/shotoku/2260.htm')

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
        self.assertEqual(page.meta['robots'],'index,follow')

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
        evidence=json.loads((DATA/'source-audit.json').read_text())['excluded_sources'][0]
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
