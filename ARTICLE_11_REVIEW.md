# 第11号：金融データ・制度・品質監査

ETFと投資信託の違いとは？新NISAではどっちがおすすめ？手数料・分配金・長期リターンを徹底比較

調査2026-11-07、本文12,470文字（空白・日付・目次・参考資料・関連記事を除く）。
専用ブランチfeat/article-11-etf、既存10記事とRSSを保持。

## 採用条件と主要結果

eMAXIS Slim米国株式(S&P500)と国内ETF2633。ともにS&P500配当込みの円換算・ヘッジなし。
Slim2018-07-03、2633は2021-03-29設定。共通10年実績は存在せず掲載しない。
共通5年2021-09-30〜2026-09-30、円建てNAV、個人課税前・ファンド内費用控除後。
共通日次1222件、月末61点。ETF市場価格・個人売買成績ではない。

|商品|5年累積|CAGR|最大下落率|高値→底|
|---|---|---|---|---|
|Slim|162.23%|21.26%|−24.08%|2025-01-24→2025-04-09|
|2633|161.03%|21.15%|−24.07%|2025-01-24→2025-04-09|

Slimは資産運用業協会の登録データCSV、ETFは野村AM公式CSV。
運用会社の直接Slimページ/CSVは403で、直接照合済みとは表現しない。
運用会社作成の2026-07-25目論見書はJTG証券公式配布版で本文確認。
取得原本・時刻・SHA256、コード・結果JSON・再現方法を公開。
2633は2023-12-08分割調整済み。公式再投資NAVを現金分配から独立再構成、
最大相対誤差2.2e-12未満（許容1e-9）。100口当たりPDFと1口CSVを混同しない。
Slim取得全履歴の分配はゼロ、将来の無分配を保証しない。

## 費用・制度監査

2633基本信託報酬0.066%税込、別途監査費年0.04%等があるため総費用ではない。
Slim基本上限0.08140%税込、純資産額別の段階料率を確認。現在料率を過去実績から再控除しない。
商品購入単位、通貨、設定日、分配方針、個人取引費と設定/交換費の違いを確認。
金融庁2026-10-23つみたて一覧、協会上場/非上場成長枠Excelの実登録行を確認・原本保存。
Slim03311187は両枠、2633（リスト上26330）は成長枠、つみたて非対象。
上場Excel最終列の非対象はつみたて資格であって、成長枠一覧への登録と混同しない。
JPX資料基準日は2026-02-27と明記し、現在の協会リスト/運用会社情報で補強。

成人2026年適用制度と、2027年1月開始の未成年者つみたて拡充を区別。
金融庁案内・JSDA2026年9月Q&A（2026-04-01公布法令等に基づく）のQ2/3等を照合。
将来適用制度を現行として使わず、検討段階案を試算に織り込まない。
国内ETFの株式数比例配分方式、分配再投資の新規枠消費、国内投信の元本払戻金をJSDAで照合。
国税庁1330/1463/1240（2026-04-01法令等）で配当・売却益・外国税額控除の条件を確認。
NISA日本非課税と外国税は別。証券会社FAQは実務補足。外国税率/個人手取りを一律断定しない。

## 独自モデル

- 月末1/3/5万円、実効年率0/3/5/7%、10/20/30年、36ケース。税費用前。
- 総実効年率5%、年コスト0.05/0.10/0.20/0.50/1%、3金額×3期間、45ケース。
  年純倍率1.05×(1-cost)、月倍率はその1/12乗。実際の日割り/段階費用とは別の仮定。
- 初期100万円、総収益年6%、年初残高3%を年末分配/売却、20年、全条件同一・税費用ゼロ。
  ETF現金受取=A、再投資=B、内部再投資=C、定期売却=D。A=D、B=Cを独立に照合。
  配当3%を総収益6%へ足さず、運用残高と受取累計を分ける。
- 同じNISA枠内で全モデルが実現する保証ではない。月5万円30年1800万円の元本は、
  2633成長枠だけの保有限度1200万円を売却等なしで超えると注意書き。

## 限界（非計測値を捏造しない）

- 統計的tracking errorは未算出：同頻度・同時点の完全な指数系列を取得できていない。
  2633の10月末月報3年101.0%対指数103.0%は別期間・公表丸め値による追跡差でありTEではない。
- 実績の為替寄与を厳密分解していない。1.10×0.90−1=−1%は仮定例と明記。
- 共通5年の結果は上場形態だけの因果効果でも、今後の優劣でもない。
- NAV評価時刻等の差があり、個人が同時点で約定できる価格ではない。

## 検証

- Python82テスト（既存73＋新規9）合格。異常CAGR/MDD日付、費用率計算、二重配当、
  不正原本・未審査分配を拒否する負例、実ExcelによるNISA枠照合も含む。
- 独立Decimal45桁等1998照合合格。CAGR、全日次の接頭最大MDD、
  月次標本変動率、毎月積上げ、費用倍率、現金保存を別コードで検算。
- HTML完全15ページ0エラー、全記事の内部リンク・目次・SEO・Article JSON-LD正常。
  Google所有権確認ファイルはHTML文書ではないため変更しない。
- 外部19URL実GET200・内容対応確認。403直接運用会社CSVは到達済みとせず採用出典から除外。
- 6グラフ、SVG/PNG12ファイルとJSONのハッシュ照合、仕組み図・特徴/費用/NISA比較表。
- Chromium320/375/768/1280pxで全体横はみ出しなし、6図読込、表だけ横スクロール。
  既存5記事との往復・運営/プライバシー/連絡・ニュース描画正常。モバイル画像を目視。
- 既存build_site.pyで11記事・15サイトマップURL、再生成が同一、一覧/サイトマップ手動編集なし。
- actionlint合格。RSS一時ファイル実取得：10フィード成功、60件、0エラー。
- 3時間cron `7 */3 * * *`、ニュース原本、更新スクリプト、ワークフロー/Pages設定は未変更。
- 出典・編集/訂正・連絡先・リスクを掲載。架空資格/監修・誇大な金融表現なし。
  AdSense申請・広告追加・第12号以降制作なし。

## 公開条件

PR必須CI成功、競合なし、意図しない差分なしを確認してから通常マージ。
保護設定を緩めず、既存のPages自動公開を利用。公開後HTTP200、本文/図/原本の一致、
一覧1件、サイトマップ1件、既存10記事、関連記事、4画面幅、RSSを実URLで検証。

## 変更ファイル一覧

- `ARTICLE_11_REVIEW.md`
- `articles/bitcoin-vs-stocks-long-term.html`
- `articles/data/etf-funds/METHOD.md`
- `articles/data/etf-funds/accumulation.png`
- `articles/data/etf-funds/accumulation.svg`
- `articles/data/etf-funds/analyze_etf_funds.py.txt`
- `articles/data/etf-funds/audit_etf_funds.py.txt`
- `articles/data/etf-funds/calculation-audit.json`
- `articles/data/etf-funds/cashflows.png`
- `articles/data/etf-funds/cashflows.svg`
- `articles/data/etf-funds/costs.png`
- `articles/data/etf-funds/costs.svg`
- `articles/data/etf-funds/fees.png`
- `articles/data/etf-funds/fees.svg`
- `articles/data/etf-funds/graph-audit.json`
- `articles/data/etf-funds/link-checks.json`
- `articles/data/etf-funds/nisa-evidence.json`
- `articles/data/etf-funds/nisa-tsumitate-list.txt`
- `articles/data/etf-funds/raw/etf.csv.gz`
- `articles/data/etf-funds/raw/fsa_list.pdf.gz`
- `articles/data/etf-funds/raw/growth_listed.xlsx.gz`
- `articles/data/etf-funds/raw/growth_unlisted.xlsx.gz`
- `articles/data/etf-funds/raw/slim.csv.gz`
- `articles/data/etf-funds/results.json`
- `articles/data/etf-funds/returns.png`
- `articles/data/etf-funds/returns.svg`
- `articles/data/etf-funds/source-evidence.json`
- `articles/data/etf-funds/sources.json`
- `articles/data/etf-funds/wealth.png`
- `articles/data/etf-funds/wealth.svg`
- `articles/dividend-vs-index-investing.html`
- `articles/etf-vs-mutual-funds.html`
- `articles/gold-bitcoin-stocks-inflation.html`
- `articles/new-nisa-beginners-guide.html`
- `articles/sp500-vs-all-country.html`
- `index.html`
- `scripts/analyze_etf_funds.py`
- `scripts/audit_etf_funds.py`
- `sitemap.xml`
- `tests/test_etf_funds.py`
