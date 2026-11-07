"""Article13: dated annual financial facts and explicit instructional models."""
import argparse,datetime as dt,gzip,hashlib,html,json,math
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/stock-metrics';ARTICLE=ROOT/'articles/market-cap-per-pbr-guide.html'
def sha(b):return hashlib.sha256(b).hexdigest()
def ratio(a,b):return a/b if b>0 else None
def price(code):
    raw=json.loads(gzip.decompress((DATA/'raw'/f'price_{code}.json.gz').read_bytes()))['chart']['result'][0]
    if raw['meta']['currency']!='JPY' or raw['meta']['symbol']!=code+'.T':raise ValueError('Wrong price currency/symbol')
    dates=[dt.datetime.fromtimestamp(x,dt.timezone.utc).date().isoformat() for x in raw['timestamp']]
    if dates.count('2026-03-31')!=1:raise ValueError('Price date missing/duplicated')
    for e in raw.get('events',{}).get('splits',{}).values():
        if dt.datetime.fromtimestamp(e['date'],dt.timezone.utc).date().isoformat()>'2026-03-31':raise ValueError('Post-reference split needs price rebasing review')
    index=dates.index('2026-03-31')
    if not raw['indicators']['quote'][0]['volume'][index]:raise ValueError('No observed trading volume')
    value=raw['indicators']['quote'][0]['close'][index]
    if value is None or not math.isfinite(value) or value<=0:raise ValueError('Invalid price')
    return float(Decimal(str(value)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),value

def load():
    m=json.loads((DATA/'sources.json').read_text())
    for name,digest in m['input_sha256'].items():
        if sha((DATA/name).read_bytes())!=digest:raise ValueError('Input checksum mismatch: '+name)
    rows=json.loads((DATA/'companies.json').read_text())['companies']
    if len(rows)!=6 or len({c['code'] for c in rows})!=6:raise ValueError('Company count/duplicates')
    for c in rows:
        if (c['fiscal_start'],c['fiscal_end'],c['price_date'],c['equity_begin_date'])!=('2025-04-01','2026-03-31','2026-03-31','2025-03-31'):raise ValueError('Unmatched fiscal/price dates')
        if c['treasury_shares']<0 or c['issued_shares']<=c['treasury_shares'] or c['weighted_average_shares']<=0:raise ValueError('Invalid share counts')
        if c['disclosed_date']<=c['price_date']:raise ValueError('Retrospective disclosure flag inconsistent')
    return rows

def metrics(p,issued,treasury,weighted,n,e0,e1):
    if p<=0 or issued<=treasury or treasury<0 or weighted<=0:raise ValueError('Invalid price/shares')
    shares=issued-treasury;eps=n/weighted;bps=e1/shares;eps_end=n/shares;roe_avg=ratio(n,(e0+e1)/2);roe_end=ratio(n,e1)
    return dict(price=p,issued=issued,treasury=treasury,shares=shares,weighted=weighted,profit=n,equity_begin=e0,equity_end=e1,market_cap=p*shares,eps=eps,bps=bps,per=ratio(p,eps),pbr=ratio(p,bps),roe_average=roe_avg,roe_end=roe_end,eps_end=eps_end,per_end=ratio(p,eps_end))

def calculate():
    out=[]
    for c in load():
        p,raw=price(c['code']);r=metrics(p,c['issued_shares'],c['treasury_shares'],c['weighted_average_shares'],c['profit_million_yen']*1e6,c['equity_begin_million_yen']*1e6,c['equity_end_million_yen']*1e6)
        r.update(code=c['code'],name=c['name'],industry=c['industry'],price_raw_api=raw,source=c['source'],reported_eps=float(c['reported_eps_yen']),reported_bps=float(c['reported_bps_yen']),forecast_per=None,price_date=c['price_date'],fiscal_end=c['fiscal_end'],disclosed_date=c['disclosed_date'])
        r['eps_vs_reported']=r['eps']-r['reported_eps'];r['bps_vs_reported']=r['bps']-r['reported_bps']
        # One displayed sen plus max one-million-yen input reporting unit / denominator.
        if abs(r['eps_vs_reported'])>=.01+1e6/r['weighted'] or abs(r['bps_vs_reported'])>=.01+1e6/r['shares']:raise ValueError('Published per-share facts not reconciled within stated precision')
        out.append(r)
    base=metrics(1000,100000000,0,100000000,10000000000,100000000000,100000000000)
    issued=metrics(1000,120000000,0,120000000,10000000000,120000000000,120000000000)
    split=metrics(500,200000000,0,200000000,10000000000,100000000000,100000000000)
    buyback=metrics(1000,100000000,20000000,80000000,10000000000,80000000000,80000000000)
    return dict(review_date='2026-11-07',price_date='2026-03-31',fiscal_start='2025-04-01',fiscal_end='2026-03-31',currency='JPY',retrospective_not_point_in_time=True,companies=out,examples=dict(price_cap=[dict(company='A',price=100,shares=1000000000,market_cap=100000000000),dict(company='B',price=1000,shares=10000000,market_cap=10000000000)],per=[dict(price=1000,eps=eps,per=ratio(1000,eps)) for eps in (100,50,20,0,-50)],pbr=[dict(price=1000,bps=bps,pbr=ratio(1000,bps)) for bps in (500,1000,2000,0,-500)],profit_halved=dict(price=1000,eps_before=100,eps_after=50,per_before=10,per_after=20),base=base,split=split,issue=issued,buyback=buyback,issue_existing_owner_before=.01,issue_existing_owner_after=1000000/120000000),growth=[dict(growth=g,points=[dict(year=y,eps=100*(1+g)**y,per=1000/(100*(1+g)**y)) for y in range(6)]) for g in (0,.1,.2)],identity=[dict(per=per,points=[dict(roe=r/100,pbr=per*r/100) for r in range(1,21)]) for per in (10,15,20)])

def number(v,unit='',scale=1,digits=2):return '算定対象外' if v is None else f'{v/scale:,.{digits}f}'+unit
def table(caption,heads,rows):
    return '<p class="small">表は左右にスクロールできます。</p><div class="table-wrap" role="region" tabindex="0" aria-label="'+caption+'"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th scope="col">'+html.escape(h)+'</th>' for h in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(('<th scope="row">'+html.escape(str(v))+'</th>') if i==0 else '<td>'+html.escape(str(v))+'</td>' for i,v in enumerate(row))+'</tr>' for row in rows)+'</tbody></table></div>'
def tables(r):
    compare=[[x['name']+' '+x['code'],x['industry'],number(x['price'],'円'),number(x['market_cap'],'億円',1e8),number(x['per'],'倍'),number(x['pbr'],'倍'),number(x['roe_average']*100 if x['roe_average'] is not None else None,'%'),'未掲載'] for x in r['companies']]
    facts=[[x['name'],number(x['profit'],'百万円',1e6,0),number(x['equity_begin'],'百万円',1e6,0),number(x['equity_end'],'百万円',1e6,0),number(x['eps'],'円'),number(x['bps'],'円'),x['disclosed_date']] for x in r['companies']]
    shares=[[x['name']]+[number(x[k],'株',1,0) for k in ('issued','treasury','shares','weighted')] for x in r['companies']]
    consistent=[[x['name'],number(x['eps_end'],'円'),number(x['per_end'],'倍'),number(x['roe_end']*100 if x['roe_end'] is not None else None,'%'),number(x['pbr'],'倍')] for x in r['companies']]
    e=r['examples'];cases=[['A社',100,1000000000,100000000000],['B社',1000,10000000,10000000000]]
    structures=[[label]+[number(e[key][k],unit,scale,digits) for k,unit,scale,digits in [('price','円',1,2),('shares','株',1,0),('market_cap','億円',1e8,2),('eps','円',1,2),('bps','円',1,2),('per','倍',1,2),('roe_end','%',.01,2)]] for key,label in [('base','基準'),('split','1対2分割'),('issue','2000万株増資'),('buyback','2000万株自己取得')]]
    return dict(COMPANIES=table('事後学習用・2026年3月末株価と同月終了年度の実績',['企業・コード','業種','3月末終値','自己株控除時価総額','実績PER','PBR','通期/平均自己資本ROE','予想PER'],compare),FACTS=table('公開百万単位からの独自再計算・親会社帰属の連結全体利益',['企業','純利益','期首自己資本','期末自己資本','計算EPS・平均株数','計算BPS・期末株数','短信公表日'],facts),SHARES=table('分母となる株式数：2026年3月末と年度平均',['企業','発行済総数','控除する自己株','期末控除後','期中平均'],shares),IDENTITY=table('恒等式説明用：期末株式数・期末自己資本へ統一した参考値',['企業','期末株数EPS','期末株数PER','期末資本ROE','PBR'],consistent),PRICECAP=table('架空のA/B社：株価と規模は別',['企業','株価（円）','株式数（株）','時価総額（円）'],[[x[0]]+[f'{v:,}' for v in x[1:]] for x in cases]),PER=table('架空：株価1000円を固定',['EPS（円）','PER'],[[str(x['eps']),number(x['per'],'倍')] for x in e['per']]),PBR=table('架空：株価1000円を固定',['BPS（円）','PBR'],[[str(x['bps']),number(x['pbr'],'倍')] for x in e['pbr']]),STRUCTURE=table('架空：税・費用・追加利益なし、自己取得/増資は1000円で期首に実施と仮定',['状態','株価','自己株控除後株数','時価総額','EPS','BPS','PER','期末資本ROE'],structures))
def outputs():
    r=calculate();text=ARTICLE.read_text()
    for key,v in tables(r).items():
        a='<!-- '+key+':START -->';b='<!-- '+key+':END -->'
        if text.count(a)!=1 or text.count(b)!=1:raise ValueError('Missing markers')
        text=text[:text.index(a)+len(a)]+'\n'+v+'\n'+text[text.index(b):]
    files={'results.json':json.dumps(r,ensure_ascii=False,indent=2)+'\n'}
    for name in ('analyze_stock_metrics.py','audit_stock_metrics.py'):files[name+'.txt']=(ROOT/'scripts'/name).read_text()
    return files,text

def plots():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article13','font.size':12});r=calculate();art=[]
    def save(fig,name,source):
        fig.text(.01,.007,source,fontsize=8);fig.tight_layout(rect=[0,.065,1,1])
        for ext in ('svg','png'):
            p=DATA/(name+'.'+ext);fig.savefig(p,dpi=160,metadata={'Date':None} if ext=='svg' else None)
            if ext=='svg':p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n')
            art.append(dict(file=p.name,sha256=sha(p.read_bytes())))
        plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(8.5,5));axes[0].bar(['A','B'],[100,1000],color=['#176b57','#a56a16']);axes[0].set(title='Share price',ylabel='JPY / share');axes[1].bar(['A','B'],[1000,100],color=['#176b57','#a56a16']);axes[1].set(title='Equity market cap',ylabel='JPY 100m');save(fig,'price-cap','Hypothetical A: JPY100 x 1bn shares; B: JPY1000 x 10m shares | no treasury shares')
    fig,ax=plt.subplots(figsize=(8.5,5));ax.bar([x['code'] for x in r['companies']],[x['pbr'] for x in r['companies']],color='#176b57');ax.axhline(1,color='#a56a16',ls='--');ax.set(title='Historical PBR | not a buy ranking',ylabel='Price / calculated BPS');save(fig,'companies','Price 2026-03-31; FY2026 issuer facts (published May) | Yahoo / issuer reports | retrospective')
    fig,axes=plt.subplots(2,1,figsize=(8.5,7),sharex=True)
    for x in r['growth']:
        axes[0].plot(range(6),[p['eps'] for p in x['points']],label=f'EPS growth {x["growth"]:.0%}');axes[1].plot(range(6),[p['per'] for p in x['points']],label=f'{x["growth"]:.0%}')
    axes[0].set(title='Same share price, different assumed EPS growth',ylabel='EPS JPY');axes[1].set(xlabel='Years',ylabel='PER (times)')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    save(fig,'growth','Hypothetical initial EPS100, price1000 held constant, annual growth0/10/20% | not forecast')
    fig,ax=plt.subplots(figsize=(8.5,5))
    for x in r['identity']:ax.plot([p['roe']*100 for p in x['points']],[p['pbr'] for p in x['points']],label=f'PER {x["per"]}')
    ax.set(title='PBR = PER x ROE | matched definitions',xlabel='ROE on end equity (%)',ylabel='PBR (times)');ax.legend();ax.grid(alpha=.2);save(fig,'identity','Hypothetical: same positive profit and end shares/equity | ROE as fraction in multiplication')
    fig,axes=plt.subplots(1,2,figsize=(8.5,5));axes[0].bar(['Before','After 1:2'],[1000,500],color='#176b57');axes[0].set(title='Theoretical share price',ylabel='JPY');axes[1].bar(['Before','After 1:2'],[1000,1000],color='#a56a16');axes[1].set(title='Unchanged market cap',ylabel='JPY 100m');save(fig,'split','Hypothetical100m -> 200m shares; no new cash/profit | real price may vary')
    (DATA/'graph-audit.json').write_text(json.dumps(dict(results_sha256=sha((DATA/'results.json').read_bytes()),artifacts=art),indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--plots',action='store_true');a=p.parse_args();files,text=outputs();files[ARTICLE.name]=text
    for name,value in files.items():
        path=ARTICLE if name==ARTICLE.name else DATA/name
        if a.check:
            if not path.exists() or path.read_text()!=value:raise SystemExit('Stale output: '+name)
        else:path.write_text(value)
    if a.plots:plots()
    print('Article13 outputs verified' if a.check else 'Article13 generated')
if __name__=='__main__':main()
