"""Article 6: frozen ETF proxy analysis, no network; matplotlib only for --plots."""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import statistics

if __package__:
    from .analyze_long_term import metrics, table, pct
    from .simulate_nisa import future_value, yen
else:
    from analyze_long_term import metrics, table, pct
    from simulate_nisa import future_value, yen
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'articles/data/sp500-all-country'
ARTICLE=ROOT/'articles/sp500-vs-all-country.html'
START,END='<!-- EQUITY:START -->','<!-- EQUITY:END -->'
LABEL={'spy':'SPY（S&P500連動ETF）','acwi':'ACWI（全世界株式ETF）'}


def load_data():
    manifest=json.loads((DATA/'sources.json').read_text())
    payload=(DATA/'observations.csv').read_bytes()
    if hashlib.sha256(payload).hexdigest()!=manifest['input_sha256']: raise ValueError('CSV hash mismatch')
    rows=list(csv.DictReader(io.StringIO(payload.decode())))
    if [r['date'] for r in rows]!=sorted({r['date'] for r in rows}): raise ValueError('Invalid dates')
    for row in rows:
        dt.date.fromisoformat(row['date'])
        for k,v in row.items():
            if k!='date' and v and (not math.isfinite(float(v)) or float(v)<=0): raise ValueError('Invalid value')
    common=[r for r in rows if all(r.values())]
    if common[0]['date']!='2016-09-30' or common[-1]['date']!='2026-09-30' or len(common)<2400: raise ValueError('Missing window')
    return common


def month_ends(rows):
    ends={}
    for row in rows: ends[row['date'][:7]]=row
    return list(ends.values())


def analyze():
    rows=load_data();primary=json.loads((DATA/'primary-facts.json').read_text())
    result=dict(start=rows[0]['date'],end=rows[-1]['date'],common_dates=len(rows),windows={},annual=[],historical_monthly={},hypothetical=[])
    for years,start in [(5,'2021-09-30'),(10,'2016-09-30')]:
        subset=[r for r in rows if r['date']>=start]
        if subset[0]['date']!=start: raise ValueError('Window baseline missing')
        dates=[r['date'] for r in subset]
        window=dict(start=start,end=dates[-1],observations=len(subset),assets={})
        for key in LABEL:
            usd=[float(r[key+'_adjusted_usd']) for r in subset]
            jpy=[float(r[key+'_adjusted_usd'])*float(r['usd_jpy']) for r in subset]
            month_rows=month_ends(subset)
            prices=[float(r[key+'_adjusted_usd'])*float(r['usd_jpy']) for r in month_rows]
            changes=[b/a-1 for a,b in zip(prices,prices[1:])]
            asset=dict(usd=metrics(dates,usd),jpy=metrics(dates,jpy),final_jpy=1e6*jpy[-1]/jpy[0],
                       monthly_volatility_jpy=statistics.stdev(changes)*math.sqrt(12),monthly_returns_count=len(changes),
                       official_market_cagr_percent=primary[key]['official_market_cagr_percent'][str(years)])
            asset['difference_from_official_percentage_points']=asset['usd']['cagr']*100-asset['official_market_cagr_percent']
            window['assets'][key]=asset
        result['windows'][str(years)]=window
    base=0
    for year in range(2016,2027):
        end=max(i for i,r in enumerate(rows) if r['date'][:4]==str(year))
        record=dict(year=year,start=rows[base]['date'],end=rows[end]['date'],partial=year in (2016,2026),returns={})
        for key in LABEL:
            record['returns'][key]={ccy:float(rows[end][key+'_adjusted_usd'])/float(rows[base][key+'_adjusted_usd'])*(float(rows[end]['usd_jpy'])/float(rows[base]['usd_jpy']) if ccy=='jpy' else 1)-1 for ccy in ['usd','jpy']}
        result['annual'].append(record);base=end
    ends=month_ends(rows)[1:]
    if len(ends)!=120: raise ValueError('Expected 120 month-end contributions')
    for key in LABEL:
        units=sum(30000/(float(r[key+'_adjusted_usd'])*float(r['usd_jpy'])) for r in ends)
        final=units*float(rows[-1][key+'_adjusted_usd'])*float(rows[-1]['usd_jpy'])
        result['historical_monthly'][key]=dict(contributions=120,first_date=ends[0]['date'],last_date=ends[-1]['date'],principal_yen=3600000,final_yen=round(final),gain_yen=round(final)-3600000)
    for years in [10,20,30]:
        for rate in [0,3,5,7]:
            final=yen(future_value(30000,rate,years*12));principal=30000*years*12
            result['hypothetical'].append(dict(years=years,annual_percent=rate,principal_yen=principal,final_yen=final,gain_yen=final-principal))
    return result,rows,primary


def render(result,primary):
    sections=[]
    for years,w in result['windows'].items():
        sections.append(table(f'過去約{years}年：{w["start"]}〜{w["end"]}、共通{w["observations"]}観測日',
          ['ETF代理系列','CAGR USD','CAGR JPY','100万円期末 JPY','最大DD JPY','月次変動率の年率換算 JPY'],
          [(LABEL[k],pct(a['usd']['cagr']),pct(a['jpy']['cagr']),f'{a["final_jpy"]:,.0f}円',pct(a['jpy']['maximum_drawdown']),f'{a["monthly_volatility_jpy"]*100:.2f}%') for k,a in w['assets'].items()]))
    sections.append('<h3 id="official-check">公式資料との照合</h3>')
    sections.append(table('公式公表値との照合：年率、米ドル建て、2026年9月30日終点',
      ['ETF','期間','公式Market Value/Price','独自の調整後終値計算','差（ポイント）'],
      [(k.upper(),years+'年',f'{a["official_market_cagr_percent"]:.2f}%',f'{a["usd"]["cagr"]*100:.2f}%',f'{a["difference_from_official_percentage_points"]:+.3f}') for years,w in result['windows'].items() for k,a in w['assets'].items()]))
    sections.append('<h3 id="annual-returns">年別騰落率と部分期間</h3>')
    sections.append(table('年別騰落率：配当等調整後、円換算。2016・2026年は部分期間',
      ['年','開始日','終了日','SPY','ACWI'],[(str(r['year'])+('（部分）' if r['partial'] else ''),r['start'],r['end'],pct(r['returns']['spy']['jpy']),pct(r['returns']['acwi']['jpy'])) for r in result['annual']]))
    sections.append('<h3 id="historical-saving">過去系列による月3万円の積立比較</h3>')
    sections.append(table('実際の過去10年系列で月3万円：2016年10月〜2026年9月の月末120回',
      ['代理ETF','積立元本','期末評価額','差額'],[(k.upper(),f'{a["principal_yen"]:,}円',f'{a["final_yen"]:,}円',f'{a["gain_yen"]:+,}円') for k,a in result['historical_monthly'].items()]))
    sections.append('<h3 id="assumed-saving">月3万円を10・20・30年：利回りを仮定した比較</h3>')
    sections.append(table('仮定計算：月3万円・月末積立。両指数に共通の計算であり予測ではない',
      ['期間','仮定実効年率','元本','想定評価額','増減額'],[(str(a['years'])+'年',str(a['annual_percent'])+'%',f'{a["principal_yen"]:,}円',f'{a["final_yen"]:,}円',f'{a["gain_yen"]:+,}円') for a in result['hypothetical']]))
    return '\n'.join(sections)


def render_composition(p):
    top=table('両ETFの上位10証券：2026年9月30日、発行会社資料の丸め値',
      ['順位','SPY 銘柄','比率','ACWI 銘柄','比率'],[(i+1,p['spy']['top10'][i][0],f'{p["spy"]["top10"][i][1]:.2f}%',p['acwi']['top10'][i][0],f'{p["acwi"]["top10"][i][1]:.2f}%') for i in range(10)])
    translations={'Information Technology':'情報技術','Financials':'金融','Communication Services':'コミュニケーション','Health Care':'ヘルスケア','Consumer Discretionary':'一般消費財','Industrials':'資本財・サービス','Consumer Staples':'生活必需品','Energy':'エネルギー','Utilities':'公益','Real Estate':'不動産','Materials':'素材','Other':'その他（内訳未確認）'}
    sectors=[]
    for key,label in translations.items():
        fmt=lambda a:f'{a:.2f}%' if a is not None else '個別内訳なし'
        sectors.append((label,fmt(p['spy']['sectors'].get(key)),fmt(p['acwi']['sectors'].get(key))))
    return top+'\n'+table('業種構成：2026年9月30日、ETF発行会社資料', ['業種','SPY','ACWI'],sectors)


def outputs():
    result,rows,primary=analyze()
    text=ARTICLE.read_text()
    for start,end,fragment in [(START,END,render(result,primary)),('<!-- COMPOSITION:START -->','<!-- COMPOSITION:END -->',render_composition(primary))]:
        if text.count(start)!=1 or text.count(end)!=1: raise ValueError('Markers missing/duplicated')
        text=text[:text.index(start)+len(start)]+'\n'+fragment+'\n'+text[text.index(end):]
    files={'results.json':json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'}
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(result['hypothetical'][0]),lineterminator='\n');writer.writeheader();writer.writerows(result['hypothetical']);files['hypothetical.csv']=buffer.getvalue()
    for name in ['analyze_equity_comparison.py','fetch_equity_comparison.py','audit_equity_comparison.py']:
        files[name+'.txt']=(ROOT/'scripts'/name).read_text()
    return files,text


def plots():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as md
    result,rows,p=analyze()
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article6-v1','font.size':12})
    dates=[dt.date.fromisoformat(r['date']) for r in rows]
    fig,(ax,dd)=plt.subplots(2,1,figsize=(9,7),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    for key,color in [('spy','#176b57'),('acwi','#a66a12')]:
        vals=[float(r[key+'_adjusted_usd'])*float(r['usd_jpy']) for r in rows];peak=vals[0];draw=[]
        for v in vals:peak=max(peak,v);draw.append((v/peak-1)*100)
        ax.plot(dates,[v/vals[0]*100 for v in vals],label=key.upper(),color=color,linewidth=1.4)
        dd.plot(dates,draw,color=color,linewidth=1)
    ax.set(title='ETF proxies: JPY 1,000,000 lump sum | 2016-09-30 to 2026-09-30',ylabel='Value (JPY 10,000)');ax.legend();dd.set(ylabel='Drawdown (%)',ylim=(-45,3));dd.xaxis.set_major_locator(md.YearLocator(2));dd.xaxis.set_major_formatter(md.DateFormatter('%Y'))
    for a in [ax,dd]:a.grid(alpha=.2);a.margins(x=0)
    fig.tight_layout();fig.savefig(DATA/'historical.svg',metadata={'Date':None});fig.savefig(DATA/'historical.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5.4))
    for rate in [0,3,5,7]:ax.plot([i/12 for i in range(361)],[float(future_value(30000,rate,i))/10000 for i in range(361)],label=f'{rate}% hypothetical',linewidth=2)
    ax.set(title='JPY 30,000/month | hypothetical constant effective annual rates',xlabel='Years',ylabel='Value (JPY 10,000)',xlim=(0,30),ylim=(0,None));ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(DATA/'hypothetical.svg',metadata={'Date':None});fig.savefig(DATA/'hypothetical.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5.4))
    sectors=['Information Technology','Financials','Industrials','Health Care','Consumer Discretionary']
    for offset,key,color in [(-.18,'spy','#176b57'),(.18,'acwi','#a66a12')]:ax.barh([i+offset for i in range(5)],[p[key]['sectors'][s] for s in sectors],height=.34,label=key.upper(),color=color)
    ax.set_yticks(range(5),sectors);ax.invert_yaxis();ax.set(xlabel='Weight (%)',title='ETF sector weights | 2026-09-30');ax.legend();ax.grid(axis='x',alpha=.2);fig.tight_layout();fig.savefig(DATA/'sectors.svg',metadata={'Date':None});fig.savefig(DATA/'sectors.png',dpi=160);plt.close(fig)

    for path in DATA.glob('*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--plots',action='store_true');a=parser.parse_args()
    files,text=outputs()
    if a.check:
        if ARTICLE.read_text()!=text or any((DATA/name).read_text()!=value for name,value in files.items()):raise SystemExit('Generated equity outputs are stale')
        print('Equity outputs reproduce exactly')
    else:
        ARTICLE.write_text(text)
        for name,value in files.items():(DATA/name).write_text(value)
    if a.plots:plots()


if __name__=='__main__':main()
