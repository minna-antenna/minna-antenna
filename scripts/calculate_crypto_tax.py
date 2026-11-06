"""Article 7 review-only tax examples. Publication is blocked by source audit."""
import argparse,csv,hashlib,io,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'articles/data/crypto-tax'
ARTICLE=ROOT/'articles/crypto-tax-japan-guide.html'
MODELS=[dict(salary_yen=4000000,salary_income_yen=2760000,social_insurance_yen=600000),dict(salary_yen=8000000,salary_income_yen=6100000,social_insurance_yen=1200000),dict(salary_yen=12000000,salary_income_yen=10050000,social_insurance_yen=1800000)]
PROFITS=[100000,500000,1000000,3000000]
BRACKETS=[(1950000,5,0),(3300000,10,97500),(6950000,20,427500),(9000000,23,636000),(18000000,33,1536000),(40000000,40,2796000),(None,45,4796000)]


def basic_deduction(total,year):
    if total<0 or year not in (2025,2026):raise ValueError('Unsupported income/year')
    thresholds=[(1320000,950000),(3360000,880000),(4890000,680000),(6550000,630000),(23500000,580000)] if year==2025 else [(4890000,1040000),(6550000,670000),(23500000,620000)]
    thresholds += [(24000000,480000),(24500000,320000),(25000000,160000)]
    return next((value for ceiling,value in thresholds if total<=ceiling),0)


def income_tax(taxable):
    if taxable<0:raise ValueError('Negative taxable income')
    base=taxable//1000*1000
    for ceiling,rate,offset in BRACKETS:
        if ceiling is None or base<ceiling:return max(0,base*rate//100-offset)


def national_tax_components(taxable_income_yen,*,pre_reconstruction_credit_yen=0):
    """2025/2026 ordinary resident model, after specified eligible tax credits.

    The caller must establish that a credit reduces the reconstruction-tax base.
    Foreign tax credit and distribution-adjustment credit are not modeled here.
    None is unknown evidence, never silently treated as zero.
    """
    if not isinstance(pre_reconstruction_credit_yen,int) or pre_reconstruction_credit_yen<0:
        raise ValueError('An explicit nonnegative eligible tax credit is required')
    assessed=income_tax(taxable_income_yen)
    applied=min(assessed,pre_reconstruction_credit_yen)
    base=assessed-applied
    reconstruction=base*21//1000
    return dict(assessed_income_tax_yen=assessed,pre_reconstruction_credit_yen=applied,
                base_income_tax_yen=base,reconstruction_tax_yen=reconstruction,
                national_annual_yen=(base+reconstruction)//100*100)


def annual(model,profit,year):
    if profit<0:raise ValueError('Examples do not model losses')
    total=model['salary_income_yen']+profit
    basic=basic_deduction(total,year)
    taxable=max(0,total-model['social_insurance_yen']-basic)//1000*1000
    components=national_tax_components(taxable,pre_reconstruction_credit_yen=0)
    tax=components['assessed_income_tax_yen'];surtax=components['reconstruction_tax_yen']
    # Resident: standard 6%+4%, basic 430k, no dependants, adjustment credit 1500+1000.
    # All model cases are above exemption thresholds and the 50k personal-deduction difference.
    resident_base=max(0,total-model['social_insurance_yen']-430000)//1000*1000
    ward=max(0,resident_base*6//100-1500)//100*100
    prefecture=max(0,resident_base*4//100-1000)//100*100
    return dict(total_income_yen=total,basic_deduction_yen=basic,taxable_income_yen=taxable,income_tax_yen=tax,assessed_income_tax_yen=tax,pre_reconstruction_credit_yen=0,base_income_tax_yen=components['base_income_tax_yen'],reconstruction_tax_yen=surtax,national_annual_yen=components['national_annual_yen'],resident_taxable_income_yen=resident_base,resident_income_levy_yen=ward+prefecture)


def calculate():
    rows=[]
    for year in (2025,2026):
        for model in MODELS:
            baseline=annual(model,0,year)
            for profit in PROFITS:
                final=annual(model,profit,year)
                delta=final['national_annual_yen']-baseline['national_annual_yen']
                local=final['resident_income_levy_yen']-baseline['resident_income_levy_yen']
                rows.append(dict(tax_year=year,law_status='A_applied_reference_2025' if year==2025 else 'B_enacted_2026_effective_2026-12-01_for_normal_annual_returns',**model,crypto_profit_yen=profit,baseline=baseline,with_crypto=final,income_tax_increase_yen=final['income_tax_yen']-baseline['income_tax_yen'],reconstruction_tax_increase_yen=final['reconstruction_tax_yen']-baseline['reconstruction_tax_yen'],national_payment_increase_yen=delta,resident_income_levy_increase_yen=local,total_increase_yen=delta+local))
    return rows


def tables(rows):
    parts=[]
    for year in (2026,2025):
        label='B：成立済み・12月施行後の2026年分通常申告' if year==2026 else 'A：適用済み2025年分の参考比較'
        parts.append(f'<h3 id="tax-{year}">{label}</h3>')
        for salary in [4000000,8000000,12000000]:
            selected=[r for r in rows if r['tax_year']==year and r['salary_yen']==salary]
            title=f'給与年収{salary//10000}万円・暗号資産を全額申告するモデル（円）'
            body=''.join('<tr>'+f'<th scope="row">{r["crypto_profit_yen"]:,}</th><td>{r["income_tax_increase_yen"]:,}</td><td>{r["reconstruction_tax_increase_yen"]:,}</td><td>{r["national_payment_increase_yen"]:,}</td><td>{r["resident_income_levy_increase_yen"]:,}</td><td>{r["total_increase_yen"]:,}</td>'+'</tr>' for r in selected)
            parts.append(f'<div class="table-wrap" role="region" aria-label="{title}" tabindex="0"><table><caption>{title}</caption><thead><tr><th scope="col">利益</th><th scope="col">所得税本体の増分</th><th scope="col">復興税の増分</th><th scope="col">国税納付増分（端数処理後）</th><th scope="col">住民税所得割の増分</th><th scope="col">合計増分</th></tr></thead><tbody>{body}</tbody></table></div>')
    return '\n'.join(parts)


def outputs():
    rows=calculate()
    result=dict(status='review_only_publication_blocked',calculated_on_utc='2026-11-06',model_assumptions='Single employed resident, no dependants or other deductions/income; eligible pre-reconstruction tax credits explicitly zero; fixed social insurance; crypto treated as miscellaneous in these hypothetical facts only; all crypto included on return, no exemption determination; resident standard rates 6%+4%, constant per-capita/forest levies cancel; no insurance premium increase',scenarios=rows)
    files={'results.json':json.dumps(result,ensure_ascii=False,indent=2)+'\n'}
    buffer=io.StringIO(newline='');fields=['tax_year','salary_yen','social_insurance_yen','crypto_profit_yen','income_tax_increase_yen','reconstruction_tax_increase_yen','national_payment_increase_yen','resident_income_levy_increase_yen','total_increase_yen'];w=csv.DictWriter(buffer,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows);files['results.csv']=buffer.getvalue()
    for name in ['calculate_crypto_tax.py','audit_crypto_tax.py']:files[name+'.txt']=(ROOT/'scripts'/name).read_text()
    source=ARTICLE.read_text();start='<!-- TAX:START -->';end='<!-- TAX:END -->'
    if source.count(start)!=1 or source.count(end)!=1:raise ValueError('Missing table markers')
    updated=source[:source.index(start)+len(start)]+'\n'+tables(rows)+'\n'+source[source.index(end):]
    return files,updated


def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article7-tax','font.size':12})
    rows=calculate();fig,ax=plt.subplots(figsize=(9,5.4))
    for offset,salary,color in [(-.25,4000000,'#176b57'),(0,8000000,'#a66a12'),(.25,12000000,'#296da3')]:
        values=[r['total_increase_yen']/10000 for r in rows if r['tax_year']==2026 and r['salary_yen']==salary]
        ax.bar([i+offset for i in range(4)],values,width=.24,label=f'Salary JPY {salary/1000000:g}m',color=color)
    ax.set_xticks(range(4),['100k','500k','1m','3m']);ax.set(title='REVIEW ONLY | Enacted 2026 year rules effective Dec 1',xlabel='Crypto profit (JPY)',ylabel='Additional tax (JPY 10,000)');ax.legend();ax.grid(axis='y',alpha=.2);fig.tight_layout();fig.savefig(DATA/'tax-models.svg',metadata={'Date':None});fig.savefig(DATA/'tax-models.png',dpi=160);plt.close(fig)
    p=DATA/'tax-models.svg';p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--plots',action='store_true');a=p.parse_args();files,text=outputs()
    if a.check:
        if ARTICLE.read_text()!=text or any((DATA/k).read_text()!=v for k,v in files.items()):raise SystemExit('Stale tax outputs')
        print('24 review-only scenarios reproduce exactly')
    else:
        ARTICLE.write_text(text)
        for k,v in files.items():(DATA/k).write_text(v)
    if a.plots:plot()


if __name__=='__main__':main()
