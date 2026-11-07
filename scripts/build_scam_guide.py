"""Generate editorial defensive tables/checklist. No reader data or wallet access."""
import argparse,hashlib,html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/scam-prevention';ARTICLE=ROOT/'articles/crypto-scam-prevention.html'
def sha(b):return hashlib.sha256(b).hexdigest()
def load():
    r=json.loads((DATA/'guide.json').read_text())
    if r['statistics_used'] is not False:raise ValueError('Unreviewed statistics')
    for key,minimum in [('types',10),('signals',10),('firstaid',8)]:
        rows=r[key];ids=[x['id'] for x in rows]
        if len(rows)<minimum or len(ids)!=len(set(ids)):raise ValueError('Missing/duplicate editorial items')
        if any(not isinstance(v,str) or not v.strip() for x in rows for v in x.values()):raise ValueError('Empty editorial item')
    if [x['id'] for x in r['firstaid']]!=list('ABCDEFGH'):raise ValueError('Missing first aid situation')
    sources=json.loads((DATA/'sources.json').read_text());urls={x['key']:x['url'] for x in sources['sources']}
    for x in r['types']+r['contacts']:
        if x['source'] not in urls:raise ValueError('Missing source')
    return r,urls

def tables():
    r,urls=load();escape=html.escape
    def link(key):return '<a href="'+escape(urls[key],quote=True)+'">公式資料</a>'
    out='<p class="small">この表の誘い文句は編集部による説明用の例です。特定事件の発言の引用ではありません。横に収まらない表は左右へスクロールできます。</p><div class="table-wrap wide" role="region" tabindex="0" aria-label="詐欺手口14種類の比較"><table><caption>接触から初動までの手口比較</caption><thead><tr>'+''.join('<th scope="col">'+v+'</th>' for v in ['種類・根拠','接触方法','誘い文句の例','危険な兆候','被害の仕組み','予防行動','気づいた後'])+'</tr></thead><tbody>'
    for x in r['types']:out+='<tr><th scope="row">'+escape(x['name'])+'<br>'+link(x['source'])+'</th>'+''.join('<td>'+escape(x[k])+'</td>' for k in ['contact','pitch','signal','mechanism','prevent','response'])+'</tr>'
    out+='</tbody></table></div>'
    checklist='<fieldset id="risk-checklist"><legend>自分の状況に当てはまる項目を確認</legend>'
    for x in r['signals']:
        checklist+='<label class="signal-row" for="signal-'+x['id']+'"><input type="checkbox" id="signal-'+x['id']+'"><span><strong>'+escape(x['title'])+'</strong><br><span class="reason">理由：'+escape(x['reason'])+'</span><br><span>対処：'+escape(x['action'])+'</span></span></label>'
    checklist+='</fieldset><p id="checklist-status" role="status" aria-live="polite">未選択でも安全とは判断できません。これは確認用のメモで、詐欺の判定や安全の保証ではありません。</p><button type="button" id="checklist-reset">選択を解除</button><p><a href="#firstaid">状況別の初動対応へ進む</a></p>'
    aid=''.join('<section class="aid"><h3 id="action-'+x['id']+'">'+x['id']+'．'+escape(x['situation'])+'</h3><p>'+escape(x['action'])+'</p><p class="note">'+escape(x['caution'])+'</p></section>' for x in r['firstaid'])
    contacts='<p class="small">2026年11月7日に公式ページで確認。電話番号・受付時間は変更されることがあります。発信前にリンク先の最新案内を確認してください。表は横にスクロールできます。</p><div class="table-wrap" role="region" tabindex="0" aria-label="日本の公式相談窓口"><table><caption>相談先の役割と連絡方法</caption><thead><tr>'+''.join('<th scope="col">'+v+'</th>' for v in ['相談先','連絡先','相談対象','時間・限界','根拠'])+'</tr></thead><tbody>'
    for x in r['contacts']:contacts+='<tr><th scope="row">'+escape(x['name'])+'</th>'+''.join('<td>'+escape(x[k])+'</td>' for k in ['phone','role','hours'])+'<td>'+link(x['source'])+(' / '+link(x['hours_source']) if x['hours_source']!=x['source'] else '')+'</td></tr>'
    contacts+='</tbody></table></div>'
    return dict(TYPES=out,CHECKLIST=checklist,FIRSTAID=aid,CONTACTS=contacts)
def outputs():
    text=ARTICLE.read_text()
    for key,value in tables().items():
        a='<!-- '+key+':START -->';b='<!-- '+key+':END -->'
        if text.count(a)!=1 or text.count(b)!=1:raise ValueError('Missing generation marker')
        text=text[:text.index(a)+len(a)]+'\n'+value+'\n'+text[text.index(b):]
    r,_=load();audit=dict(schema='editorial-audit-v1',review_date=r['review_date'],types=len(r['types']),signals=len(r['signals']),firstaid=len(r['firstaid']),contacts=len(r['contacts']),guide_sha256=sha((DATA/'guide.json').read_bytes()),checklist_js_sha256=sha((DATA/'checklist.js').read_bytes()),reader_data_transmitted=False,safety_score=False)
    return text,json.dumps(audit,ensure_ascii=False,indent=2)+'\n'
def diagram():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article12','font.size':17})
    fig,ax=plt.subplots(figsize=(8.5,5));fig.patch.set_facecolor('#f5f7f5');ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');ax.text(.5,.93,'Suspected crypto scam: first response',ha='center',fontsize=20,color='#173d3b',weight='bold')
    for y,title,body in [(.68,'STOP','No additional payment or signature'),(.47,'SAVE','Keep messages and transaction records'),(.26,'SECURE','Use a trusted device and official support'),(.05,'CONSULT','Police / consumer support / provider')]:
        ax.add_patch(FancyBboxPatch((.06,y),.88,.15,boxstyle='round,pad=0.015',facecolor='white',edgecolor='#176b57',linewidth=2));ax.text(.09,y+.10,title,color='#176b57',weight='bold',fontsize=15);ax.text(.09,y+.035,body,fontsize=13,color='#203a42')
        if y>.05:ax.annotate('',xy=(.5,y-.06),xytext=(.5,y-.015),arrowprops=dict(arrowstyle='->',color='#176b57'))
    fig.text(.5,.01,'Editorial defensive guide | reviewed 2026-11-07 | recovery is not guaranteed',ha='center',fontsize=8);fig.tight_layout(rect=[0,.025,1,1]);art=[]
    for ext in ('svg','png'):
        p=DATA/('first-response.'+ext);fig.savefig(p,dpi=160,metadata={'Date':None} if ext=='svg' else None)
        if ext=='svg':p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n')
        art.append(dict(file=p.name,sha256=sha(p.read_bytes())))
    plt.close(fig);(DATA/'diagram-audit.json').write_text(json.dumps(dict(guide_sha256=sha((DATA/'guide.json').read_bytes()),artifacts=art),indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--diagram',action='store_true');args=p.parse_args();text,audit=outputs()
    for path,value in [(ARTICLE,text),(DATA/'content-audit.json',audit),(DATA/'build_scam_guide.py.txt',Path(__file__).read_text())]:
        if args.check:
            if not path.exists() or path.read_text()!=value:raise SystemExit('Stale generated output: '+path.name)
        else:path.write_text(value)
    if args.diagram:diagram()
    print('Article12 outputs verified' if args.check else 'Article12 generated')
if __name__=='__main__':main()
