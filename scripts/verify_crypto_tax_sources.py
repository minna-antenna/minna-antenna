"""Fail closed on the authorities actually used by the article, including scope."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/crypto-tax'
REQUIRED={'income_law','reconstruction_law','rounding_law','basic_deduction','salary_deduction','nta1000','resident_rules','resident_2027'}
TRANSITION={'financial_law','financial_revisions','partial_commencement','crypto_tax_transition','crypto_outline'}

def verify(audit=None,evidence=None,article=None):
    audit=json.loads((DATA/'source-audit.json').read_text()) if audit is None else audit
    evidence=json.loads((DATA/'rule-evidence.json').read_text()) if evidence is None else evidence
    article=(ROOT/'articles/crypto-tax-japan-guide.html').read_text() if article is None else article
    def require(value,message):
        if not value:raise ValueError(message)
    require(audit['status']=='passed_for_declared_2025_2026_scope','Unapproved source scope')
    require(not audit['blockers'] and not audit['unresolved_release_issues'],'Unresolved material release issue')
    used=set(audit['calculation_authority_ids'])
    require(used==REQUIRED,'Missing or unexpected calculation authority')
    rows=evidence['evidence'];by_id={r['id']:r for r in rows}
    require(len(by_id)==len(rows) and REQUIRED|TRANSITION<=set(by_id),'Missing or duplicated evidence')
    for row in rows:
        require(row['url'].startswith(('https://www.nta.go.jp/','https://www.fsa.go.jp/','https://laws.e-gov.go.jp/','https://www.city.tokyo-nakano.lg.jp/','https://www.city.taito.lg.jp/')),'Non-primary evidence')
        require(hashlib.sha256(row['excerpt'].encode()).hexdigest()==row['excerpt_sha256'],'Evidence excerpt changed')
        require(len(row['raw_sha256'])==64 and row['retrieved_at_utc'].startswith('2026-11-06'),'Missing dated acquisition evidence')
    excluded=audit['excluded_sources']
    require(len(excluded)==1 and excluded[0]['id']=='NTA_2260_EXAMPLE_MISMATCH','Lost discrepancy audit trail')
    require(excluded[0]['documented_pre_reconstruction_credit_yen'] is None,'Invented official credit')
    require(excluded[0]['disposition']=='excluded_from_article_and_calculation_authority','Unresolved source still relied upon')
    require(excluded[0]['url'] not in article,'Excluded source reintroduced in article')
    require(all(by_id[id]['url']!=excluded[0]['url'] for id in used),'Excluded calculation authority')
    scope=audit['applicability']
    require(scope['model_years']==[2025,2026] and scope['normal_annual_return_only'] and scope['credits_yen']==0,'Unverified model assumptions')
    require(scope['crypto_current_scope_verified'] and not scope['crypto_separate_tax_used'] and not scope['future_calendar_date_asserted'] and not scope['future_credit_or_tax_rate_used'],'Unverified tax applicability')
    require('令和八年' in by_id['financial_law']['excerpt'] and '政令で定める日' in by_id['financial_law']['excerpt'],'Missing commencement rule')
    revisions=json.loads(by_id['financial_revisions']['excerpt'])
    main=next(r for r in revisions if r['amendment_enforcement_comment']=='公布の日から起算して一年を超えない範囲内において政令で定める日')
    require(main['current_revision_status']=='UnEnforced','Crypto commencement status changed: re-audit required')
    require('翌年の一月一日' in by_id['crypto_tax_transition']['excerpt'],'Missing conditional tax transition')
    require('12月1日' in by_id['basic_deduction']['excerpt'] and '令和8年分' in by_id['basic_deduction']['excerpt'],'Missing annual deduction applicability')
    require('基準所得税額' in by_id['reconstruction_law']['excerpt'] and '百分の二・一' in by_id['reconstruction_law']['excerpt'],'Missing reconstruction base/rate')
    require('千円未満' in by_id['rounding_law']['excerpt'] and '百円未満' in by_id['rounding_law']['excerpt'],'Missing rounding law')
    require('43万円' in by_id['resident_rules']['excerpt'] and '1,500円' in by_id['resident_rules']['excerpt'] and '1,000円' in by_id['resident_rules']['excerpt'],'Missing resident-tax base or adjustment')
    require('基礎控除の変更はありません' in by_id['resident_2027']['excerpt'] and '220万円以下' in by_id['resident_2027']['excerpt'],'Missing 2027 resident-tax applicability')
    return dict(status='passed',calculation_authorities=len(used),primary_evidence_records=len(rows),excluded_inconsistent_examples=len(excluded),scope_years=scope['model_years'])

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False,indent=2))
