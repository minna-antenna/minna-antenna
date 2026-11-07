"""Article 11: frozen JPY NAV comparison and explicit cost/cash models."""
import html
import argparse,csv,datetime as dt,gzip,hashlib,io,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/etf-funds';ARTICLE=ROOT/'articles/etf-vs-mutual-funds.html'
ASSETS={'slim':'eMAXIS Slim 米国株式（S&P500）','etf':'国内ETF 2633'}
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(name):
    p=DATA/'raw'/(name+'.csv.gz');b=p.read_bytes();m=json.loads((DATA/'sources.json').read_text())
    if sha(b)!=m['input_sha256']['raw/'+p.name]:raise ValueError('Raw checksum mismatch')
    return gzip.decompress(b).decode('cp932')
def read():
    slim={}
    for r in csv.DictReader(io.StringIO(raw('slim'))):
        d=dt.datetime.strptime(r['年月日'],'%Y年%m月%d日').date().isoformat();div=float(r['分配金'] or 0)
        if div:raise ValueError('Unreviewed Slim cash distribution')

        if d in slim:raise ValueError('Duplicate fund date')
        slim[d]=dict(date=d,nav=float(r['基準価額(円)']),total=float(r['基準価額(円)']),distribution=div)
    text=raw('etf')
    if '2023年12月8日' not in text or '分割の影響を受けないよう調整' not in text:raise ValueError('Unverified split-adjustment declaration')
    etf={}
    for r in csv.reader(io.StringIO(text)):
        if not r or len(r[0])!=8 or not r[0].isdigit():continue
        d=dt.datetime.strptime(r[0],'%Y%m%d').date().isoformat()
        if d in etf:raise ValueError('Duplicate ETF date')
        etf[d]=dict(date=d,nav=float(r[3]),total=float(r[6]),distribution=float(r[4]))
    if not slim or not etf:raise ValueError('Missing observations')
    for series in (slim,etf):
        if list(series)!=sorted(series):raise ValueError('Non-increasing dates')
        for r in series.values():
            if any(not math.isfinite(r[k]) or r[k]<=0 for k in ('nav','total')):raise ValueError('Invalid NAV')
    return dict(slim=slim,etf=etf)
def annuity(monthly,annual,years):
    if annual<=-1 or years<0:raise ValueError('Invalid rate')
    if annual==0:return monthly*12*years
    m=math.expm1(math.log1p(annual)/12);return monthly*math.expm1(years*math.log1p(annual))/m
def cashflows():
    a=b=c=d=1000000.;cash_a=cash_d=0.;out=[]
    for y in range(21):
        out.append(dict(year=y,etf_cash_asset=a,etf_cash_received=cash_a,etf_reinvest=b,fund_internal=c,fund_sale_asset=d,fund_sale_received=cash_d))
        cash_a+=a*.03;a*=1.03;b*=1.06;c*=1.06;cash_d+=d*.03;d=d*1.06-d*.03
    return out
def calculate():
    data=read();common=sorted(set(data['slim'])&set(data['etf']));dates=[d for d in common if '2021-09-30'<=d<='2026-09-30']
    if not dates or (dates[0],dates[-1])!=('2021-09-30','2026-09-30'):raise ValueError('Missing common endpoints')
    months={d[:7]:d for d in dates}
    if len(months)!=61:raise ValueError('Incomplete calendar months')
    metrics=[];curves={};annual=[]
    for s,series in data.items():
        first,last=series[dates[0]],series[dates[-1]];ratio=last['total']/first['total'];values=[series[d]['total'] for d in dates];peak=0;worst=0;pair=(0,0)
        for i,v in enumerate(values):
            if v>values[peak]:peak=i
            dd=v/values[peak]-1
            if dd<worst:worst=dd;pair=(peak,i)
        monthly=[series[d]['total'] for d in months.values()];changes=[monthly[i]/monthly[i-1]-1 for i in range(1,len(monthly))]
        metrics.append(dict(asset=s,start=dates[0],end=dates[-1],observations=len(dates),total_return=ratio-1,cagr=ratio**.2-1,nav_only_return=last['nav']/first['nav']-1,mdd=worst,peak=dates[pair[0]],trough=dates[pair[1]],annualized_volatility=statistics.stdev(changes)*math.sqrt(12)))
        curves[s]=[dict(date=d,wealth=series[d]['total']/first['total']*100) for d in months.values()]
        for y in range(2022,2027):
            start=max(d for d in common if d[:7]==f'{y-1}-12');end=max(d for d in common if d[:7]==(f'{y}-12' if y<2026 else '2026-09'));annual.append(dict(asset=s,year=y,partial=y==2026,start=start,end=end,return_value=series[end]['total']/series[start]['total']-1))
    # Official NAV total series uses reinvestment at ex-distribution NAV.
    rows=list(data['etf'].values());factor=1.;error=0
    for previous,current in zip(rows,rows[1:]):
        factor*=(current['nav']+current['distribution'])/previous['nav'];error=max(error,abs(factor/(current['total']/rows[0]['total'])-1))
    if error>1e-9:raise ValueError('Official ETF reinvestment reconstruction mismatch')
    return dict(currency='JPY',nav_not_market_price=True,common_dates=dates,metrics=metrics,curves=curves,annual=annual,reinvestment_max_relative_error=error,
        accumulation=[dict(monthly=p,years=y,annual=r,principal=p*y*12,final=round(annuity(p,r,y)),gain=round(annuity(p,r,y))-p*y*12) for p in (10000,30000,50000) for y in (10,20,30) for r in (0,.03,.05,.07)],
        costs=[dict(monthly=p,years=y,gross_annual=.05,cost=c,net_annual=(1.05)*(1-c)-1,principal=p*y*12,final=round(annuity(p,1.05*(1-c)-1,y)),no_cost_final=round(annuity(p,.05,y)),cost_impact=round(annuity(p,.05,y))-round(annuity(p,1.05*(1-c)-1,y))) for p in (10000,30000,50000) for y in (10,20,30) for c in (.0005,.001,.002,.005,.01)],cashflows=cashflows())
def pct(v):return f'{v*100:,.2f}%'
def table(caption,heads,rows):
    return '<p class="small">横に収まらない表は左右にスクロールできます。</p><div class="table-wrap" role="region" aria-label="'+caption+'" tabindex="0"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in heads)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(('<th scope="row">'+html.escape(str(v))+'</th>') if i==0 else '<td>'+html.escape(str(v))+'</td>' for i,v in enumerate(row))+'</tr>' for row in rows)+'</tbody></table></div>'
def tables(r):
    rows=[[ASSETS[x['asset']],pct(x['nav_only_return']),pct(x['total_return']),pct(x['cagr']),pct(x['mdd']),x['peak']+'→'+x['trough'],pct(x['annualized_volatility'])] for x in r['metrics']]
    annual=[]
    for y in range(2022,2027):
        a=[x for x in r['annual'] if x['year']==y];annual.append([str(y)+('年1〜9月' if y==2026 else '年'),a[0]['start']+'→'+a[0]['end']]+[pct(x['return_value']) for x in a])
    flows=[[str(x['year'])+'年']+[f'{x[k]:,.0f}円' for k in ['etf_cash_asset','etf_cash_received','etf_reinvest','fund_internal','fund_sale_asset','fund_sale_received']] for x in r['cashflows'] if x['year'] in (0,10,20)]
    return dict(HISTORY=table('円建て・基準価額・共通5年比較',['商品','分配を足さないNAV変化','分配再投資累積','CAGR','最大下落率','高値→底値','月次標本変動率×√12'],rows),ANNUAL=table('円建て・分配再投資の年別騰落率',['年','共通端点','Slim','ETF2633'],annual),
        ACCUMULATION=''.join(table(f'月末{p//10000}万円：税・費用控除前の仮定計算',['期間','仮定実効年率','積立元本','評価額','元本との差'],[[str(x['years'])+'年',pct(x['annual'])]+[f'{x[k]:,}円' for k in ['principal','final','gain']] for x in r['accumulation'] if x['monthly']==p]) for p in (10000,30000,50000)),
        COSTS=table('月末3万円・総収益年5%を固定した費用モデル',['期間','年コスト','費用控除後年率','評価額','費用ゼロとの差'],[[str(x['years'])+'年',pct(x['cost']),f'{x["net_annual"]*100:.4f}%']+[f'{x[k]:,}円' for k in ['final','cost_impact']] for x in r['costs'] if x['monthly']==30000]),
        FLOWS=table('100万円・総収益6%・分配/売却3%・税費用ゼロ',['経過','A:ETF受取残高','A:現金累計','B:ETF再投資','C:投信内部再投資','D:売却後残高','D:受取累計'],flows))
def outputs():
    r=calculate();files={'results.json':json.dumps(r,ensure_ascii=False,indent=2)+'\n'}
    for n in ('analyze_etf_funds.py','audit_etf_funds.py'):files[n+'.txt']=(ROOT/'scripts'/n).read_text()
    text=ARTICLE.read_text()
    for key,value in tables(r).items():
        a='<!-- '+key+':START -->';b='<!-- '+key+':END -->'
        if text.count(a)!=1 or text.count(b)!=1:raise ValueError('Missing markers')
        text=text[:text.index(a)+len(a)]+'\n'+value+'\n'+text[text.index(b):]
    return files,text

def plots():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article11','font.size':12});r=calculate();art=[]
    def save(fig,name,source):
        fig.text(.01,.007,source,fontsize=8);fig.tight_layout(rect=[0,.065,1,1])
        for ext in ('svg','png'):
            p=DATA/(name+'.'+ext);fig.savefig(p,metadata={'Date':None} if ext=='svg' else None,dpi=160)
            if ext=='svg':p.write_text('\n'.join(x.rstrip() for x in p.read_text().splitlines())+'\n')
            art.append(dict(file=p.name,sha256=sha(p.read_bytes())))
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(8.5,5))
    for s,color,label in [('slim','#176b57','eMAXIS Slim S&P500'),('etf','#a56a16','ETF 2633')]:ax.plot([dt.date.fromisoformat(x['date']) for x in r['curves'][s]],[x['wealth'] for x in r['curves'][s]],label=label,color=color)
    ax.set(title='JPY NAV total-return wealth | common month ends',ylabel='2021-09-30 = 100');ax.legend();ax.grid(alpha=.2);save(fig,'wealth','2021-09-30 to 2026-09-30 | Nomura AM / association fund library | before personal tax')
    fig,axes=plt.subplots(1,2,figsize=(8.5,5))
    for ax,key,title in [(axes[0],'total_return','5-year total return'),(axes[1],'mdd','Daily NAV maximum drawdown')]:ax.bar(['Slim','ETF2633'],[x[key]*100 for x in r['metrics']],color=['#176b57','#a56a16']);ax.set(title=title,ylabel='% JPY')
    save(fig,'returns','2021-09-30 to 2026-09-30 | official ETF NAV / association NAV | distributions reinvested')
    fig,ax=plt.subplots(figsize=(8.5,5))
    for rate in (0,.03,.05,.07):ax.plot(range(31),[annuity(30000,rate,y)/10000 for y in range(31)],label=f'{rate:.0%}')
    ax.set(title='JPY 30,000 monthly | hypothetical gross rates',xlabel='Years',ylabel='JPY 10,000');ax.legend();ax.grid(alpha=.2);save(fig,'accumulation','Month-end contributions | effective annual 0/3/5/7% | no tax or cost | not a forecast')
    fig,ax=plt.subplots(figsize=(8.5,5))
    for cost in (.0005,.001,.002,.005,.01):ax.plot(range(31),[annuity(30000,1.05*(1-cost)-1,y)/10000 for y in range(31)],label=f'cost {cost:.2%}')
    ax.set(title='Same gross 5% | cost sensitivity',xlabel='Years',ylabel='JPY 10,000');ax.legend();ax.grid(alpha=.2);save(fig,'costs','JPY30,000 month-end | annual net factor = 1.05 x (1-cost) | no personal tax / trading cost')
    fig,ax=plt.subplots(figsize=(8.5,5));ax.bar(['ETF2633 headline','Slim maximum'],[.066,.0814],color=['#a56a16','#176b57']);ax.set(title='Published management fee rates | not total cost',ylabel='% per year, tax included');save(fig,'fees','2026-11-07 checked | Nomura monthly 2026-10-30 / Slim prospectus effective 2026-07-25')
    fig,axes=plt.subplots(2,1,figsize=(8.5,7),sharex=True);flows=r['cashflows']
    for k,label in [('etf_cash_asset','A: ETF cash asset'),('etf_reinvest','B: ETF reinvest'),('fund_internal','C: Internal reinvest'),('fund_sale_asset','D: Partial sale asset')]:axes[0].plot(range(21),[x[k]/10000 for x in flows],label=label,ls='--' if k in ('fund_internal','fund_sale_asset') else '-')
    for k,label in [('etf_cash_received','A: ETF cash cumulative'),('fund_sale_received','D: Sale cash cumulative')]:axes[1].plot(range(21),[x[k]/10000 for x in flows],label=label,ls='--' if k.startswith('fund') else '-')
    for ax in axes:ax.set_ylabel('JPY 10,000');ax.legend();ax.grid(alpha=.2)
    axes[0].set_title('Distribution / reinvest / internal / sale | hypothetical');axes[1].set_xlabel('Years');save(fig,'cashflows','Initial JPY1m | total 6%, cash/sale 3% of year-start assets | annual, tax/cost 0 | cash earns 0')
    (DATA/'graph-audit.json').write_text(json.dumps(dict(results_sha256=sha((DATA/'results.json').read_bytes()),artifacts=art),indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--plots',action='store_true');a=p.parse_args();files,text=outputs();files[ARTICLE.name]=text
    for n,v in files.items():
        path=ARTICLE if n==ARTICLE.name else DATA/n
        if a.check:
            if not path.exists() or path.read_text()!=v:raise SystemExit('Stale output: '+n)
        else:path.write_text(v)
    if a.plots:plots()
    print('Article11 outputs verified' if a.check else 'Article11 generated')
if __name__=='__main__':main()
