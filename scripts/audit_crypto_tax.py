"""Independent Decimal/marginal-bracket audit. Does not override publication gate."""
from decimal import Decimal,ROUND_DOWN
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/crypto-tax'


def audit():
    rows=json.loads((DATA/'results.json').read_text())['scenarios'];checks=0;basis_checks=0;full_field_checks=0
    for row in rows:
        assert row['tax_year'] in (2025,2026)
        assert row['salary_yen'] in (4000000,8000000,12000000)
        assert row['crypto_profit_yen'] in (100000,500000,1000000,3000000)
        expected_records=[]
        for profit,record in [(0,row['baseline']),(row['crypto_profit_yen'],row['with_crypto'])]:
            salary=row['salary_yen']
            income=salary-(salary*20//100+440000 if salary<=6600000 else salary*10//100+1100000 if salary<=8500000 else 1950000)
            total=income+profit;year=row['tax_year']
            if year==2025:basic=950000 if total<=1320000 else 880000 if total<=3360000 else 680000 if total<=4890000 else 630000 if total<=6550000 else 580000
            else:basic=1040000 if total<=4890000 else 670000 if total<=6550000 else 620000
            assert row['salary_income_yen']==income
            assert row['social_insurance_yen']=={4000000:600000,8000000:1200000,12000000:1800000}[salary]
            assert record['basic_deduction_yen']==basic
            base=max(0,total-row['social_insurance_yen']-basic)//1000*1000
            bounds=[0,1950000,3300000,6950000,9000000,18000000,40000000,10**20];rates=['.05','.10','.20','.23','.33','.40','.45'];tax=Decimal(0)
            for lower,upper,rate in zip(bounds,bounds[1:],rates):tax+=Decimal(max(0,min(base,upper)-lower))*Decimal(rate)
            credit=record['pre_reconstruction_credit_yen'];assert credit==0
            basis=max(Decimal(0),tax-Decimal(credit))
            assert record['assessed_income_tax_yen']==int(tax)
            assert record['base_income_tax_yen']==int(basis)
            basis_checks+=2
            surtax=(basis*Decimal('.021')).quantize(Decimal(1),rounding=ROUND_DOWN)
            assert int(tax)==record['income_tax_yen'] and int(surtax)==record['reconstruction_tax_yen']
            assert int((basis+surtax)/100)*100==record['national_annual_yen'];checks+=3
            resident_base=max(0,total-row['social_insurance_yen']-430000)//1000*1000
            adjustment_base=min(50000,resident_base) if resident_base<=2000000 else max(50000-(resident_base-2000000),50000)
            assert total<=25000000
            municipal=int((Decimal(resident_base)*Decimal('.06')-Decimal(adjustment_base)*Decimal('.03'))/100)*100
            prefectural=int((Decimal(resident_base)*Decimal('.04')-Decimal(adjustment_base)*Decimal('.02'))/100)*100
            expected=dict(total_income_yen=total,basic_deduction_yen=basic,taxable_income_yen=base,
                income_tax_yen=int(tax),assessed_income_tax_yen=int(tax),pre_reconstruction_credit_yen=0,
                base_income_tax_yen=int(basis),reconstruction_tax_yen=int(surtax),
                national_annual_yen=int((basis+surtax)/100)*100,resident_taxable_income_yen=resident_base,
                resident_income_levy_yen=municipal+prefectural)
            assert record==expected, (row['tax_year'],salary,profit,'annual fields')
            full_field_checks+=len(expected);expected_records.append(expected)
        before,after=expected_records
        for result_key,field in [('income_tax_increase_yen','income_tax_yen'),('reconstruction_tax_increase_yen','reconstruction_tax_yen'),('national_payment_increase_yen','national_annual_yen'),('resident_income_levy_increase_yen','resident_income_levy_yen')]:
            assert row[result_key]==after[field]-before[field],result_key
            full_field_checks+=1
        # All four profit inputs are multiples that leave resident levy adjustment/rounding unchanged.
        assert row['resident_income_levy_increase_yen']==row['crypto_profit_yen']//10
        assert row['total_increase_yen']==row['national_payment_increase_yen']+row['resident_income_levy_increase_yen'];checks+=2
    assert len(rows)==24 and len({(r['tax_year'],r['salary_yen'],r['crypto_profit_yen']) for r in rows})==24
    return dict(status='calculation_passed',scenarios=len(rows),checks=checks,basis_checks=basis_checks,full_field_checks=full_field_checks)


if __name__=='__main__':print(json.dumps(audit(),indent=2))
