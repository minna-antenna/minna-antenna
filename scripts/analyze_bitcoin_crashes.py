"""Frozen Bitstamp USD daily-close analysis; network only in the separate fetcher."""
import argparse,csv,datetime as dt,hashlib,io,json
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'articles/data/bitcoin-crash';ARTICLE=ROOT/'articles/bitcoin-crash-history.html'
WINDOWS=[('2013–2015','2013-01-01','2015-12-31'),('2017–2018','2017-01-01','2018-12-31'),('2020年1–3月','2020-01-01','2020-03-31'),('2021–2022','2021-01-01','2022-12-31'),('2024–2026','2024-01-01','2026-11-05')]
HALVINGS=[('2012-11-28',210000),('2016-07-09',420000),('2020-05-11',630000),('2024-04-20',840000)]
D=Decimal

def load():
    manifest=json.loads((DATA/'sources.json').read_text());raw=(DATA/'observations.csv').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['input_sha256']:raise ValueError('Observation checksum mismatch')
    rows=list(csv.DictReader(io.StringIO(raw.decode())))
    expected=[(dt.date(2013,1,1)+dt.timedelta(days=i)).isoformat() for i in range(5057)]
    if [r['date'] for r in rows]!=expected:raise ValueError('Missing, duplicated or reordered calendar observations')
    for r in rows:
        if dt.datetime.fromtimestamp(int(r['timestamp']),dt.timezone.utc).date().isoformat()!=r['date'] or int(r['timestamp'])%86400:raise ValueError('UTC label mismatch')
        if not D(r['close']).is_finite() or not D(r['volume']).is_finite() or D(r['close'])<=0 or D(r['volume'])<0:raise ValueError('Invalid price/volume')
        if not D(r['low'])<=min(D(r['open']),D(r['close']))<=max(D(r['open']),D(r['close']))<=D(r['high']):raise ValueError('Invalid OHLC')
    return rows

def days(a,b):return (dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days

def episode(rows,label,start,end):
    usable=[r for r in rows if D(r['volume'])>0];window=[r for r in usable if start<=r['date']<=end]
    if len(window)<2:raise ValueError('Insufficient window')
    peak=window[0];worst=D(0);pair=None
    for r in window:
        if D(r['close'])>D(peak['close']):peak=r  # earliest equal high wins
        dd=D(r['close'])/D(peak['close'])-1
        if dd<worst:worst=dd;pair=(peak,r)  # earliest equal trough wins
    if pair is None:raise ValueError('No decline')
    peak,trough=pair
    recovery=next((r for r in usable if r['date']>trough['date'] and D(r['close'])>=D(peak['close'])),None)
    last=usable[-1]
    return dict(label=label,window_start=start,window_end=end,peak_date=peak['date'],peak_usd=peak['close'],trough_date=trough['date'],trough_usd=trough['close'],drawdown_pct=str(worst*100),peak_to_trough_days=days(peak['date'],trough['date']),recovery_date=recovery['date'] if recovery else None,peak_to_recovery_days=days(peak['date'],recovery['date']) if recovery else None,trough_to_recovery_days=days(trough['date'],recovery['date']) if recovery else None,unrecovered_days=days(peak['date'],last['date']) if recovery is None else None,model_principal_jpy=1000000,model_trough_jpy=int((D(1000000)*(1+worst)).quantize(D(1),rounding=ROUND_HALF_UP)),required_rebound_pct=str((D(peak['close'])/D(trough['close'])-1)*100))

def calculate(rows=None):
    rows=load() if rows is None else rows;events=[episode(rows,*w) for w in WINDOWS];valid=[r for r in rows if D(r['volume'])>0];last=valid[-1];recent=events[-1]
    return dict(provider='Bitstamp',currency='USD',price_field='close',utc_interval_label='start date; close boundary next day 00:00 UTC / 09:00 JST',period_start=rows[0]['date'],period_end=rows[-1]['date'],calendar_rows=len(rows),trading_rows=len(valid),excluded_zero_volume_dates=[r['date'] for r in rows if D(r['volume'])==0],selection='Five explicitly declared windows, not a complete non-overlapping all-time crash ranking. Recovery searches all subsequent valid closes through cutoff.',events=events,ranking=sorted([e['label'] for e in events],key=lambda label:D(next(e['drawdown_pct'] for e in events if e['label']==label))),last_close_usd=last['close'],last_drawdown_from_recent_peak_pct=str((D(last['close'])/D(recent['peak_usd'])-1)*100),halvings=[dict(date=d,height=h) for d,h in HALVINGS])

def percent(v):return f'{D(v):.2f}%'
def table(result):
    rows=[]
    for e in result['events']:
        recovery=e['recovery_date'] or '未回復'
        duration=f"{e['peak_to_recovery_days']:,}日" if e['recovery_date'] else f"{e['unrecovered_days']:,}日経過・未回復"
        bottom=f"{e['trough_to_recovery_days']:,}日" if e['recovery_date'] else '未回復'
        rows.append(f"<tr><th scope=\"row\">{e['label']}</th><td>{e['peak_date']}<br>${D(e['peak_usd']):,.2f}</td><td>{e['trough_date']}<br>${D(e['trough_usd']):,.2f}</td><td>{percent(e['drawdown_pct'])}</td><td>{e['peak_to_trough_days']:,}日</td><td>{recovery}</td><td>{duration}</td><td>{bottom}</td></tr>")
    summary='<div class="table-wrap" role="region" tabindex="0" aria-label="5期間の終値ベース最大下落と回復"><table><caption>Bitstamp BTC/USD日足終値：事前に定めた5期間の比較</caption><thead><tr><th scope="col">抽出期間</th><th scope="col">ピーク・USD</th><th scope="col">底・USD</th><th scope="col">最大下落率</th><th scope="col">ピーク→底</th><th scope="col">最初の回復日</th><th scope="col">ピーク→回復</th><th scope="col">底→回復</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
    ranking='<ol>'+''.join(f"<li>{label}：{percent(next(e['drawdown_pct'] for e in result['events'] if e['label']==label))}</li>" for label in result['ranking'])+'</ol>'
    simulation='<div class="table-wrap simulation-table" role="region" tabindex="0" aria-label="100万円の下落率連動モデル"><table><caption>為替固定・コスト税金なしの仮定。実際の円建て運用実績ではない</caption><thead><tr><th scope="col">期間</th><th scope="col">当初元本</th><th scope="col">底の評価額</th><th scope="col">元本との差</th><th scope="col">元値へ必要な上昇率</th></tr></thead><tbody>'+''.join(f"<tr><th scope=\"row\">{e['label']}</th><td>1,000,000円</td><td>{e['model_trough_jpy']:,}円</td><td>{e['model_trough_jpy']-1000000:,}円</td><td>{percent(e['required_rebound_pct'])}</td></tr>" for e in result['events'])+'</tbody></table></div>'
    return dict(CRASH=summary,RANKING=ranking,LOSS=simulation)

def chart_data(rows,result):
    return dict(source_csv_sha256=hashlib.sha256((DATA/'observations.csv').read_bytes()).hexdigest(),long_price=[[r['date'],r['close'] if D(r['volume'])>0 else None] for r in rows],events=result['events'],halvings=result['halvings'])

def outputs():
    rows=load();result=calculate(rows);files={'results.json':json.dumps(result,ensure_ascii=False,indent=2)+'\n','chart-data.json':json.dumps(chart_data(rows,result),ensure_ascii=False,indent=2)+'\n'}
    for name in ['analyze_bitcoin_crashes.py','audit_bitcoin_crashes.py','fetch_bitcoin_crashes.py']:files[name+'.txt']=(ROOT/'scripts'/name).read_text()
    text=ARTICLE.read_text()
    for key,value in table(result).items():
        a=f'<!-- {key}:START -->';b=f'<!-- {key}:END -->'
        if text.count(a)!=1 or text.count(b)!=1:raise ValueError('Missing generation marker')
        text=text[:text.index(a)+len(a)]+'\n'+value+'\n'+text[text.index(b):]
    return files,text

def plots():
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter
    plt.rcParams.update({'svg.fonttype':'none','svg.hashsalt':'article8','font.size':12})
    data=json.loads((DATA/'chart-data.json').read_text());ev=data['events'];labels=['2013–15','2017–18','2020 Q1','2021–22','2024–26'];colors=['#176b57','#296da3','#a66a12','#764b83','#943c39'];artifacts=[]
    def save(fig,name,description):
        fig.text(.01,.005,'Source: Bitstamp BTC/USD daily close | UTC 2013-01-01 to 2026-11-05',fontsize=8)
        fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(DATA/(name+'.svg'),metadata={'Date':None,'Description':description});fig.savefig(DATA/(name+'.png'),dpi=160);plt.close(fig)
        for ext in ['svg','png']:artifacts.append(dict(file=name+'.'+ext,sha256=hashlib.sha256((DATA/(name+'.'+ext)).read_bytes()).hexdigest()))
    fig,ax=plt.subplots(figsize=(9,5.4));ax.plot([dt.date.fromisoformat(r[0]) for r in data['long_price']],[float(r[1]) if r[1] is not None else float('nan') for r in data['long_price']],color=colors[0],linewidth=1)
    ax.set(yscale='log',ylabel='USD per BTC (log scale)',title='Long-term daily close | zero-volume days omitted');ax.grid(alpha=.2);save(fig,'long-price','Daily closes; gaps for three zero-volume dates. Log axis.')
    fig,ax=plt.subplots(figsize=(9,5.4));vals=[float(D(e['drawdown_pct'])) for e in ev];bars=ax.barh(labels,vals,color=colors)
    for bar,v in zip(bars,vals):ax.text(v+.8,bar.get_y()+bar.get_height()/2,f'{v:.2f}%',va='center',color='white',fontweight='bold')
    ax.set(xlim=(-100,0),xlabel='Peak-to-trough change (%)',title='Five selected windows | not an exhaustive ranking');ax.grid(axis='x',alpha=.2);save(fig,'drawdowns','Maximum close-to-close drawdown within each fixed window.')
    fig,ax=plt.subplots(figsize=(9,5.4));vals=[e['peak_to_recovery_days'] if e['recovery_date'] else e['unrecovered_days'] for e in ev];bars=ax.barh(labels,vals,color=colors)
    for bar,e,v in zip(bars,ev,vals):
        text=f'{v} days' if e['recovery_date'] else f'{v}+ days | NOT RECOVERED';ax.text(v+12,bar.get_y()+bar.get_height()/2,text,va='center',fontsize=10)
        if not e['recovery_date']:bar.set_hatch('//')
    ax.set(xlim=(0,1600),xlabel='Calendar days from peak',title='Time to first close at or above previous peak');ax.grid(axis='x',alpha=.2);save(fig,'recovery-days','Unrecovered episode is right-censored, not a completed recovery.')
    fig,ax=plt.subplots(figsize=(9,5.4));vals=[e['model_trough_jpy']/10000 for e in ev];bars=ax.bar(labels,vals,color=colors);ax.axhline(100,color='#657b83',ls='--',label='Initial JPY 1m')
    for bar,v in zip(bars,vals):ax.text(bar.get_x()+bar.get_width()/2,v+2,f'{v:.1f}',ha='center')
    ax.set(ylim=(0,112),ylabel='JPY 10,000 (FX fixed; no costs/taxes)',title='JPY 1m hypothetical drawdown model');ax.legend();save(fig,'million-yen','Historical USD price ratios applied to JPY 1m with constant FX; not actual JPY returns.')
    fig,ax=plt.subplots(figsize=(9,5.4))
    for i,(label,e,color) in enumerate(zip(labels,ev,colors)):
        p=dt.date.fromisoformat(e['peak_date']);t=dt.date.fromisoformat(e['trough_date']);r=dt.date.fromisoformat(e['recovery_date'] or '2026-11-05');ax.plot([p,t],[i,i],color=color,lw=8);ax.plot([t,r],[i,i],color=color,lw=3,ls='--');ax.scatter([p,t],[i,i],color=color,s=30)
    for date,height in HALVINGS:
        d=dt.date.fromisoformat(date);ax.axvline(d,color='#657b83',lw=1,alpha=.8);ax.text(d,4.6,str(d.year),rotation=90,ha='right',fontsize=10)
    ax.set(yticks=range(5),yticklabels=labels,ylim=(-.6,5.7),xlim=(dt.date(2012,7,1),dt.date(2027,1,1)),title='Halvings and selected drawdowns | timing is not causation');ax.xaxis.set_major_formatter(DateFormatter('%Y'));save(fig,'halving-timeline','Solid: peak to trough. Dashed: recovery or cutoff. Vertical: actual halving dates (Bitcoin.org).')
    manifest=dict(chart_data_sha256=hashlib.sha256((DATA/'chart-data.json').read_bytes()).hexdigest(),artifacts=artifacts)
    (DATA/'graph-audit.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--plots',action='store_true');args=ap.parse_args();files,text=outputs()
    if args.check:
        if ARTICLE.read_text()!=text or any((DATA/k).read_text()!=v for k,v in files.items()):raise SystemExit('Stale analysis, tables or downloadable code')
        print('Five windows, chart inputs and article tables reproduce')
    else:
        ARTICLE.write_text(text)
        for k,v in files.items():(DATA/k).write_text(v)
    if args.plots:plots()
