"""Article 10: frozen ETF history and explicit hypothetical cash-flow models."""
import argparse,csv,datetime as dt,gzip,hashlib,io,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/dividends';ARTICLE=ROOT/'articles/dividend-vs-index-investing.html'
ASSETS=('VYM','SPY')
def sha(b):return hashlib.sha256(b).hexdigest()
def read():
    m=json.loads((DATA/'sources.json').read_text());result={}
    for s in ASSETS:
        b=(DATA/'raw'/f'{s}.json.gz').read_bytes()
        if sha(b)!=m['input_sha256'][f'raw/{s}.json.gz']:raise ValueError('Raw checksum mismatch')
        r=json.loads(gzip.decompress(b))['chart']['result'][0];q=r['indicators']['quote'][0]['close'];a=r['indicators']['adjclose'][0]['adjclose'];dates=[dt.datetime.fromtimestamp(t,dt.timezone.utc).date().isoformat() for t in r['timestamp']]
        if dates!=sorted(set(dates)):raise ValueError('Invalid observation order')
        if r.get('events',{}).get('splits'):raise ValueError('Unreviewed split events')
        rows=[dict(date=d,close=float(p),adjusted=float(v)) for d,p,v in zip(dates,q,a) if p is not None and v is not None]
        if any(not math.isfinite(v) or v<=0 for x in rows for k,v in x.items() if k!='date'):raise ValueError('Invalid prices')
        div={dt.datetime.fromtimestamp(x['date'],dt.timezone.utc).date().isoformat():x['amount'] for x in r['events']['dividends'].values()}
        result[s]=(rows,div)
    if [x['date'] for x in result['VYM'][0]]!=[x['date'] for x in result['SPY'][0]]:raise ValueError('Unmatched dates')
    return result

def annuity(monthly,rate,years):
    if rate<=-1 or years<0:raise ValueError('Invalid rate/years')
    r=(1+rate)**(1/12)-1
    return monthly*years*12 if rate==0 else monthly*math.expm1(years*math.log1p(rate))/r

def cashflows(initial=1000000,total=.06,distribution=.03,years=20):
    if initial<0 or distribution<0 or total<=-1 or distribution>1+total:raise ValueError('Invalid cash flow')
    reinvest=initial;cash_asset=initial;cash_total=0.;sell_asset=initial;sell_total=0.;rows=[]
    for year in range(years+1):
        rows.append(dict(year=year,reinvested=reinvest,distributed_asset=cash_asset,distributed_cash=cash_total,withdrawal_asset=sell_asset,withdrawal_cash=sell_total))
        payment=cash_asset*distribution;cash_total+=payment;cash_asset*=1+total-distribution
        sale=sell_asset*distribution;sell_total+=sale;sell_asset=sell_asset*(1+total)-sale
        reinvest*=1+total
    return rows

def drawdown(rows):
    peak=rows[0];worst=0.;pair=(peak['date'],peak['date'])
    for r in rows:
        if r['adjusted']>peak['adjusted']:peak=r
        d=r['adjusted']/peak['adjusted']-1
        if d<worst:worst=d;pair=(peak['date'],r['date'])
    return dict(value=worst,peak=pair[0],trough=pair[1])

def calculate():
    history=read();periods=[];curves={};distribution_checks=[];annual=[]
    for s,(allrows,div) in history.items():
        # A backward dividend factor should reconstruct adjusted-close ratios.
        factor=1.;errors=[]
        for i in range(1,len(allrows)):
            prev=allrows[i-1];r=allrows[i]
            factor*=1-div.get(r['date'],0)/prev['close']
            adjusted_ratio=(r['adjusted']/r['close'])/(allrows[0]['adjusted']/allrows[0]['close'])
            errors.append(abs(adjusted_ratio*factor-1))
        error=max(errors)
        if error>1e-5:raise ValueError('Dividend adjustment reconstruction failed')
        distribution_checks.append(dict(asset=s,max_relative_error=error,split_events=0,events=len(div)))
        for years,start in [(10,'2016-09-30'),(5,'2021-09-30')]:
            rows=[r for r in allrows if start<=r['date']<='2026-09-30'];first,last=rows[0],rows[-1]
            if first['date']!=start or last['date']!='2026-09-30':raise ValueError('Endpoint missing')
            ratio=last['adjusted']/first['adjusted'];price=last['close']/first['close'];dividend=sum(v for d,v in div.items() if '2025-09-30'<d<='2026-09-30')
            monthly=[]
            for r in rows:
                if monthly and monthly[-1]['date'][:7]==r['date'][:7]:monthly[-1]=r
                else:monthly.append(r)
            if len(monthly)!=years*12+1:raise ValueError('Month missing')
            changes=[monthly[i]['adjusted']/monthly[i-1]['adjusted']-1 for i in range(1,len(monthly))]
            periods.append(dict(asset=s,years=years,start=start,end=last['date'],observations=len(rows),total_return=ratio-1,cagr=ratio**(1/years)-1,price_return=price-1,mdd=drawdown(rows),annualized_volatility=statistics.stdev(changes)*math.sqrt(12),trailing_12m_distributions=dividend,trailing_yield=dividend/last['close']))
            if years==10:curves[s]=[dict(date=r['date'],wealth=100*r['adjusted']/first['adjusted']) for r in monthly]
        for year in range(2017,2027):
            start=max(r['date'] for r in allrows if r['date'][:7]==f'{year-1}-12');end=max(r['date'] for r in allrows if r['date'][:7]==(f'{year}-12' if year<2026 else '2026-09'))
            a=next(r for r in allrows if r['date']==start);b=next(r for r in allrows if r['date']==end)
            annual.append(dict(asset=s,year=year,partial=year==2026,start=start,end=end,total_return=b['adjusted']/a['adjusted']-1))
    return dict(currency='USD',start='2016-09-30',end='2026-09-30',periods=periods,annual=annual,curves=curves,distribution_checks=distribution_checks,
        accumulation=[dict(years=y,rate=r,principal=30000*y*12,final=round(annuity(30000,r,y)),gain=round(annuity(30000,r,y))-30000*y*12) for y in (10,20,30) for r in (0,.03,.05,.07)],
        income=[dict(initial=p,yield_rate=r,annual=p*r,monthly_average=p*r/12) for p in (1000000,3000000,5000000,10000000) for r in (.02,.03,.04,.05)],cashflows=cashflows())

def table(caption,heads,rows):
    return '<p class="small">横に収まらない表は左右にスクロールできます。</p><div class="table-wrap" role="region" tabindex="0" aria-label="'+caption+'"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(('<th scope="row">'+str(v)+'</th>') if i==0 else '<td>'+str(v)+'</td>' for i,v in enumerate(row))+'</tr>' for row in rows)+'</tbody></table></div>'
def pct(v):return f'{v*100:,.2f}%'
def tables(r):
    performance=[[f'{x["asset"]}・{x["years"]}年',pct(x['price_return']),pct(x['total_return']),pct(x['cagr']),pct(x['mdd']['value']),x['mdd']['peak']+'→'+x['mdd']['trough'],pct(x['annualized_volatility'])] for x in r['periods']]
    annual=[]
    for y in range(2017,2027):
        a=[x for x in r['annual'] if x['year']==y];annual.append([str(y)+('年1〜9月' if y==2026 else '年'),a[0]['start']+'→'+a[0]['end']]+[pct(x['total_return']) for x in a])
    income=[[f'{x["initial"]//10000}万円',pct(x['yield_rate']),f'{x["annual"]:,.0f}円',f'{x["monthly_average"]:,.2f}円'] for x in r['income']]
    flows=[[str(x['year'])+'年',*[f'{x[k]:,.0f}円' for k in ['reinvested','distributed_asset','distributed_cash']],f'{x["distributed_asset"]+x["distributed_cash"]:,.0f}円',f'{x["withdrawal_asset"]:,.0f}円',f'{x["withdrawal_cash"]:,.0f}円'] for x in r['cashflows'] if x['year'] in (0,10,20)]
    return {'HISTORY':table('USD・個人課税前の共通期間比較',['ETF・期間','価格だけの騰落率','分配金調整後累積','CAGR','最大下落率','高値→底値','月次標本標準偏差×√12'],performance),
      'ANNUAL':table('年別の分配金調整後リターン（USD）',['年','観測端点','VYM','SPY'],annual),
      'ACCUMULATION':table('月末3万円・実効年率の仮定計算',['期間','仮定年率','元本','評価額','元本との差'],[[str(x['years'])+'年',pct(x['rate'])]+[f'{x[k]:,}円' for k in ['principal','final','gain']] for x in r['accumulation']]),
      'INCOME':table('仮定利回りによる税引前収入・月平均は年額÷12',['投資額','仮定配当利回り','年額','月平均'],income),
      'FLOWS':table('100万円・総収益6%・分配3%・税費用ゼロの年末モデル',['経過','全額再投資','受取型運用残高','受取累計','残高＋受取累計','売却型運用残高','売却受取累計'],flows)}
def outputs():
    r=calculate();files={'results.json':json.dumps(r,ensure_ascii=False,indent=2)+'\n'}
    for n in ('analyze_dividends.py','audit_dividends.py'):files[n+'.txt']=(ROOT/'scripts'/n).read_text()
    text=ARTICLE.read_text()
    for key,value in tables(r).items():
        a='<!-- '+key+':START -->';b='<!-- '+key+':END -->'
        if text.count(a)!=1 or text.count(b)!=1:raise ValueError('Missing generation marker')
        text=text[:text.index(a)+len(a)]+'\n'+value+'\n'+text[text.index(b):]
    return files,text

def plots():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article10','font.size':12});r=calculate();art=[]
    def save(fig,name,source):
        fig.text(.015,.006,source,fontsize=8);fig.tight_layout(rect=[0,.06,1,1])
        for ext in ('svg','png'):
            path=DATA/(name+'.'+ext);fig.savefig(path,metadata={'Date':None} if ext=='svg' else None,dpi=160)
            if ext=='svg':path.write_text('\n'.join(x.rstrip() for x in path.read_text().splitlines())+'\n')
            art.append(dict(file=path.name,sha256=sha(path.read_bytes())))
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.5,5));
    for s,color in zip(ASSETS,['#176b57','#a56a16']):ax.plot([dt.date.fromisoformat(x['date']) for x in r['curves'][s]],[x['wealth'] for x in r['curves'][s]],label=s,color=color)
    ax.set(title='ETF adjusted-close wealth | USD',ylabel='2016-09-30 = 100');ax.legend();ax.grid(alpha=.2);save(fig,'wealth','2016-09-30 to 2026-09-30 | Yahoo Finance | distributions adjusted, before personal tax')
    for name,key,title in [('returns','total_return','Cumulative adjusted return (%)'),('drawdowns',None,'Daily adjusted-close maximum drawdown (%)')]:
        fig,ax=plt.subplots(figsize=(8.5,5))
        for i,s in enumerate(ASSETS):
            ps=[next(x for x in r['periods'] if x['asset']==s and x['years']==y) for y in (5,10)];vals=[x[key]*100 if key else x['mdd']['value']*100 for x in ps];ax.bar([i*.32+x for x in (0,1)],vals,width=.3,label=s,color=['#176b57','#a56a16'][i])
        ax.set_xticks([.16,1.16],['5 years','10 years']);ax.set(title=title,ylabel='% USD');ax.legend();save(fig,name,'End 2026-09-30 | Yahoo Finance | 5y from 2021-09-30; 10y from 2016-09-30')
    fig,ax=plt.subplots(figsize=(8.5,5))
    for rate in (0,.03,.05,.07):ax.plot(range(31),[annuity(30000,rate,y)/10000 for y in range(31)],label=f'{rate:.0%}')
    ax.set(title='JPY 30,000 monthly | hypothetical',xlabel='Years',ylabel='JPY 10,000');ax.legend();ax.grid(alpha=.2);save(fig,'accumulation','Model: effective annual rate, month-end contribution | no tax / trading fees / FX | not a forecast')
    fig,ax=plt.subplots(figsize=(8.5,5));ax.bar(['2%','3%','4%','5%'],[20,30,40,50],color='#176b57');ax.set(title='JPY 10m | assumed annual cash distributions',ylabel='JPY 10,000 / year');save(fig,'income','Hypothetical yield x principal | before tax | distributions and principal are not guaranteed')
    flows=r['cashflows']
    fig,ax=plt.subplots(figsize=(8.5,5))
    for k,label in [('reinvested','Reinvested asset'),('distributed_asset','Cash-taking asset'),('distributed_cash','Cash cumulative'),('combined','Asset + cash')]:ax.plot(range(21),[(x['distributed_asset']+x['distributed_cash'] if k=='combined' else x[k])/10000 for x in flows],label=label)
    ax.set(title='Reinvest versus take cash | hypothetical',xlabel='Years',ylabel='JPY 10,000');ax.legend();ax.grid(alpha=.2);save(fig,'reinvestment','Initial JPY 1m | annual total 6% = price 3% + distribution 3% | cash earns 0%, tax/fees 0')
    fig,axes=plt.subplots(2,1,figsize=(8.5,7),sharex=True)
    for ax,a,b,title in [(axes[0],'distributed_asset','withdrawal_asset','Remaining assets'),(axes[1],'distributed_cash','withdrawal_cash','Cumulative cash')]:
        ax.plot(range(21),[x[a]/10000 for x in flows],label='Distribution',lw=3);ax.plot(range(21),[x[b]/10000 for x in flows],label='Sale',ls='--');ax.set(title=title,ylabel='JPY 10,000');ax.legend();ax.grid(alpha=.2)
    axes[1].set_xlabel('Years');save(fig,'withdrawal','Same 6% total return; pay/sell 3% of beginning-year assets | no tax / fees | identical gross cash flow')
    (DATA/'graph-audit.json').write_text(json.dumps(dict(results_sha256=sha((DATA/'results.json').read_bytes()),artifacts=art),indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--plots',action='store_true');a=p.parse_args();files,text=outputs();files[ARTICLE.name]=text
    for n,v in files.items():
        path=ARTICLE if n==ARTICLE.name else DATA/n
        if a.check:
            if not path.exists() or path.read_text()!=v:raise SystemExit('Stale generated output: '+n)
        else:path.write_text(v)
    if a.plots:plots()
    print('Article 10 generated outputs verified' if a.check else 'Article 10 generated')
if __name__=='__main__':main()
