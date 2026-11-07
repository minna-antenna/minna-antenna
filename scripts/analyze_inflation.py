"""Frozen monthly purchasing-power comparison; stdlib analysis, optional plots."""
import argparse,csv,datetime as dt,hashlib,io,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/inflation';ARTICLE=ROOT/'articles/gold-bitcoin-stocks-inflation.html'
ASSETS={'gld':('金ETF GLD','gld_adjusted_usd'),'btc':('BTC','btc_close_usd'),'spy':('株式ETF SPY','spy_adjusted_usd')}
MODES=['usd_nominal','usd_real','jpy_nominal','jpy_real']

def read_csv(name):return list(csv.DictReader(io.StringIO((DATA/name).read_text())))
def load():
    manifest=json.loads((DATA/'sources.json').read_text())
    for file,digest in manifest['input_sha256'].items():
        if hashlib.sha256((DATA/file).read_bytes()).hexdigest()!=digest:raise ValueError('Input checksum mismatch: '+file)
    monthly=read_csv('monthly.csv');daily=read_csv('daily.csv')
    months=[f'{2016+(8+i)//12:04d}-{(8+i)%12+1:02d}' for i in range(121)]
    if [r['month'] for r in monthly]!=months:raise ValueError('Missing or duplicate calendar month')
    if [r['date'] for r in daily]!=sorted({r['date'] for r in daily}):raise ValueError('Daily dates not unique/increasing')
    for r in monthly+daily:
        for k in ['gld_adjusted_usd','btc_close_usd','spy_adjusted_usd','usd_jpy']:
            if not math.isfinite(float(r[k])) or float(r[k])<=0:raise ValueError('Invalid price or FX')
    if [r['month'] for r in monthly if not r['us_cpi']]!=['2025-10']:raise ValueError('Unverified US CPI gap')
    for r in monthly:
        if r['date'][:7]!=r['month'] or float(r['jp_cpi'])<=0 or (r['us_cpi'] and float(r['us_cpi'])<=0):raise ValueError('CPI month/value mismatch')
        last=max(d['date'] for d in daily if d['date'][:7]==r['month'])
        if r['date']!=last:raise ValueError('Not last common observed date')
    return monthly,daily

def paths(rows,key):
    first=rows[0];p0=float(first[key]);fx0=float(first['usd_jpy']);us0=float(first['us_cpi']);jp0=float(first['jp_cpi']);result={m:[] for m in MODES}
    for r in rows:
        usd=float(r[key])/p0;jpy=usd*float(r['usd_jpy'])/fx0
        for k,v in [('usd_nominal',usd),('usd_real',usd/(float(r['us_cpi'])/us0) if r['us_cpi'] else None),('jpy_nominal',jpy),('jpy_real',jpy/(float(r['jp_cpi'])/jp0))]:result[k].append(v)
    return result

def mdd(dates,values):
    peak=0;worst=0.;pair=(0,0)
    for i,v in enumerate(values):
        if v>values[peak]:peak=i
        dd=v/values[peak]-1
        if dd<worst:worst=dd;pair=(peak,i)
    return dict(drawdown=worst,peak_date=dates[pair[0]],trough_date=dates[pair[1]])

def calculate():
    monthly,daily=load();periods=[]
    for years,start in [(10,0),(5,60)]:
        rows=monthly[start:];first,last=rows[0],rows[-1];n=len(rows)-1
        if n!=years*12:raise ValueError('CAGR interval mismatch')
        for asset,(label,key) in ASSETS.items():
            wealth=paths(rows,key);metrics={mode:dict(total_return=values[-1]-1,cagr=values[-1]**(12/n)-1) for mode,values in wealth.items()}
            periods.append(dict(years=years,asset=asset,start=first['date'],end=last['date'],metrics=metrics,us_inflation=float(last['us_cpi'])/float(first['us_cpi'])-1,jp_inflation=float(last['jp_cpi'])/float(first['jp_cpi'])-1,fx_ratio=float(last['usd_jpy'])/float(first['usd_jpy']),ending_jpy_nominal=math.floor(wealth['jpy_nominal'][-1]*1000000+.5),ending_jpy_real=math.floor(wealth['jpy_real'][-1]*1000000+.5)))
    annual=[];dec={r['month'][:4]:r for r in monthly if r['month'].endswith('-12')}
    for year in range(2017,2027):
        start=dec[str(year-1)];end=dec[str(year)] if year<=2025 else monthly[-1]
        us=float(end['us_cpi'])/float(start['us_cpi'])-1;jp=float(end['jp_cpi'])/float(start['jp_cpi'])-1
        row=dict(year=year,label=str(year) if year<=2025 else '2026年1–9月',full_calendar_year=year<=2025,us_inflation=us,jp_inflation=jp,us_high=us>=.04 if year<=2025 else None,jp_high=jp>=.02 if year<=2025 else None,start=start['date'],end=end['date'],assets={})
        for asset,(_,key) in ASSETS.items():row['assets'][asset]={k:v[-1]-1 for k,v in paths([start,end],key).items()}
        annual.append(row)
    risk=[]
    for years,start in [(10,'2016-09-30'),(5,'2021-09-30')]:
        rows=[r for r in daily if r['date']>=start];dates=[r['date'] for r in rows]
        for asset,(_,key) in ASSETS.items():
            usd=[float(r[key]) for r in rows];jpy=[float(r[key])*float(r['usd_jpy']) for r in rows]
            risk.append(dict(years=years,asset=asset,observations=len(rows),usd=mdd(dates,usd),jpy=mdd(dates,jpy)))
    chart=dict(months=[r['month'] for r in monthly],price_dates=[r['date'] for r in monthly],wealth={a:paths(monthly,k) for a,(_,k) in ASSETS.items()},cpi_us=[float(r['us_cpi']) if r['us_cpi'] else None for r in monthly],cpi_jp=[float(r['jp_cpi']) for r in monthly])
    return dict(periods=periods,annual=annual,risk=risk,chart=chart,missing_us_cpi=['2025-10'],regime_rule='Full calendar years 2017–2025 only: US December/December CPI >=4%; Japan >=2%. Ex-post classification; 2026 partial excluded.')

def pct(x):return f'{x*100:.2f}%'
def wrap(caption,headers,rows):return '<div class="table-wrap" role="region" tabindex="0" aria-label="'+caption+'"><table><caption>'+caption+'</caption><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(('<th scope="row">'+str(v)+'</th>') if i==0 else '<td>'+str(v)+'</td>' for i,v in enumerate(row))+'</tr>' for row in rows)+'</tbody></table></div>'
def tables(result):
    summary=[]
    for p in result['periods']:
        m=p['metrics'];summary.append([str(p['years'])+'年・'+ASSETS[p['asset']][0]]+[pct(m[k]['total_return'])+'<br>年率 '+pct(m[k]['cagr']) for k in MODES]+[f"{p['ending_jpy_nominal']:,}円",f"{p['ending_jpy_real']:,}円"])
    annual=[];regimes=[]
    for y in result['annual']:
        annual.append([y['label'],pct(y['us_inflation']),pct(y['jp_inflation'])]+[pct(y['assets'][a]['usd_nominal'])+' / '+pct(y['assets'][a]['jpy_nominal']) for a in ASSETS])
        if y['full_calendar_year'] and (y['us_high'] or y['jp_high']):regimes.append([y['year'],'米国' if y['us_high'] else '—','日本' if y['jp_high'] else '—']+[pct(y['assets'][a]['usd_real'])+' / '+pct(y['assets'][a]['jpy_real']) for a in ASSETS])
    risk=[[str(p['years'])+'年・'+ASSETS[p['asset']][0],pct(p['usd']['drawdown']),p['usd']['peak_date']+' → '+p['usd']['trough_date'],pct(p['jpy']['drawdown']),p['jpy']['peak_date']+' → '+p['jpy']['trough_date'],p['observations']] for p in result['risk']]
    return dict(COMPARE=wrap('共通月次端点の累積リターン・CAGRと100万円モデル',['期間・資産','USD名目','米国CPI調整USD実質','JPY名目','日本CPI調整JPY実質','100万円：名目','100万円：開始月購買力'],summary),ANNUAL=wrap('年別騰落率：資産欄はUSD名目 / JPY名目',['年','米国CPI上昇','日本CPI上昇']+[ASSETS[a][0] for a in ASSETS],annual),REGIME=wrap('事後分類した高インフレ年：資産欄はUSD実質 / JPY実質',['年','米国≥4%','日本≥2%']+[ASSETS[a][0] for a in ASSETS],regimes),RISK=wrap('共通観測日ベースの最大ドローダウン：CPI調整前',['期間・資産','USD下落率','USDピーク→底','JPY下落率','JPYピーク→底','観測数'],risk))

def outputs():
    result=calculate();files={'results.json':json.dumps(result,ensure_ascii=False,indent=2)+'\n'}
    for name in ['analyze_inflation.py','audit_inflation.py','prepare_inflation_data.py']:files[name+'.txt']=(ROOT/'scripts'/name).read_text()
    text=ARTICLE.read_text()
    for key,value in tables(result).items():
        a='<!-- '+key+':START -->';b='<!-- '+key+':END -->'
        if text.count(a)!=1 or text.count(b)!=1:raise ValueError('Generation markers missing')
        text=text[:text.index(a)+len(a)]+'\n'+value+'\n'+text[text.index(b):]
    return files,text

def plots():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article9','font.size':12})
    result=calculate();c=result['chart'];dates=[dt.date.fromisoformat(m+'-01') for m in c['months']];colors=['#a66a12','#176b57','#296da3'];labels=['GLD','BTC','SPY'];artifacts=[]
    def save(fig,name,desc):
        fig.text(.01,.005,'2016-09 to 2026-09 | Yahoo Finance / Bitstamp / Fed H.10 / BLS-FRED / Statistics Japan',fontsize=7.5)
        fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(DATA/(name+'.svg'),metadata={'Date':None,'Description':desc});fig.savefig(DATA/(name+'.png'),dpi=160);plt.close(fig)
        svg=DATA/(name+'.svg');svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
        for ext in ['svg','png']:artifacts.append(dict(file=name+'.'+ext,sha256=hashlib.sha256((DATA/(name+'.'+ext)).read_bytes()).hexdigest()))
    for name,mode,title,unit in [('usd-wealth','usd_nominal','USD nominal wealth | monthly, log scale','Index: 2016-09 = 100'),('million-yen','jpy_nominal','JPY 1m | nominal and real (dashed), log scale','JPY 10,000, initial 100')]:
        fig,ax=plt.subplots(figsize=(9,5.4))
        for a,color,label in zip(ASSETS,colors,labels):
            ax.plot(dates,[v*100 if v is not None else float('nan') for v in c['wealth'][a][mode]],label=label,color=color)
            if name=='million-yen':ax.plot(dates,[v*100 for v in c['wealth'][a]['jpy_real']],color=color,ls='--',lw=1)
        ax.set(yscale='log',title=title,ylabel=unit);ax.legend();ax.grid(alpha=.2);save(fig,name,title)
    fig,axes=plt.subplots(2,1,figsize=(9,7),sharex=True)
    for ax,mode,title in zip(axes,['usd_real','jpy_real'],['USD real | US CPI (2025-10 gap)','JPY real | Japan CPI']):
        for a,color,label in zip(ASSETS,colors,labels):ax.plot(dates,[v*100 if v is not None else float('nan') for v in c['wealth'][a][mode]],label=label,color=color)
        ax.set(yscale='log',title=title,ylabel='Initial = 100');ax.legend();ax.grid(alpha=.2)
    save(fig,'real-wealth','US and Japan purchasing power are separate; US real series gap at October 2025 is not interpolated.')
    fig,axes=plt.subplots(2,1,figsize=(9,7),sharex=True)
    for a,color,label in zip(ASSETS,colors,labels):
        for ax,mode in zip(axes,['usd_nominal','jpy_nominal']):ax.plot([y['year'] for y in result['annual']],[y['assets'][a][mode]*100 for y in result['annual']],marker='o',label=label,color=color)
    axes[0].set(title='Annual nominal return (%) | 2026 = Jan-Sep only',ylabel='USD (%)');axes[1].set(ylabel='JPY (%)');axes[0].legend();[a.axhline(0,color='#777',lw=.8) for a in axes];save(fig,'annual-returns','Full years 2017–2025; 2026 is partial Jan–Sep, not annualized.')
    fig,ax=plt.subplots(figsize=(9,5.4));risks=[r for r in result['risk'] if r['years']==10]
    for i,mode in enumerate(['usd','jpy']):ax.bar([j+(i-.5)*.3 for j in range(3)],[r[mode]['drawdown']*100 for r in risks],width=.28,label=mode.upper())
    ax.set(xticks=range(3),xticklabels=labels,ylabel='Drawdown (%)',title='10-year maximum drawdown | common observed dates');ax.legend();ax.grid(axis='y',alpha=.2);save(fig,'drawdowns','Nominal daily-common-date drawdown, not all-calendar-day BTC drawdown.')
    fig,axes=plt.subplots(2,1,figsize=(9,7),sharex=True)
    axes[0].plot(dates,[(v/c['cpi_us'][0])*100 if v else float('nan') for v in c['cpi_us']],label='US CPI',color='#943c39');axes[0].plot(dates,[v/c['cpi_jp'][0]*100 for v in c['cpi_jp']],label='Japan CPI',color='#764b83');axes[0].set(title='CPI and asset prices | gap in US CPI at 2025-10',ylabel='CPI: initial = 100');axes[0].legend()
    for a,color,label in zip(ASSETS,colors,labels):axes[1].plot(dates,[v*100 for v in c['wealth'][a]['usd_nominal']],label=label,color=color)
    axes[1].set(yscale='log',ylabel='USD assets: initial = 100');axes[1].legend();save(fig,'cpi-and-assets','Separate axes/panels avoid implying CPI level equals asset price. US CPI gap is not filled.')
    (DATA/'graph-audit.json').write_text(json.dumps(dict(results_sha256=hashlib.sha256((DATA/'results.json').read_bytes()).hexdigest(),artifacts=artifacts),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--plots',action='store_true');args=p.parse_args();files,text=outputs()
    if args.check:
        if ARTICLE.read_text()!=text or any((DATA/f).read_text()!=v for f,v in files.items()):raise SystemExit('Stale analysis/table/code outputs')
        print('All returns, CPI paths and article tables reproduce')
    else:
        ARTICLE.write_text(text)
        for f,v in files.items():(DATA/f).write_text(v)
    if args.plots:plots()
