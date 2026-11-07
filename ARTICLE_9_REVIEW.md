# 第9号：制作・データ監査・公開前検証

記事：金・ビットコイン・株式、インフレに強い資産はどれ？過去データと実質リターンで徹底比較

予定公開URL： https://minna-antenna.github.io/minna-antenna/articles/gold-bitcoin-stocks-inflation.html
本文約10,600文字（空白・目次・参考文献等を除く）。公開予定日2026-11-07（日本時間）。
数値取得2026-11-06 UTC（日本時間11月7日）、出典本文・到達性再確認2026-11-07。

## 比較対象・期間

金の代理はGLD、株式の代理はSPY、BTCはBitstamp現物BTC/USD終値。
GLD/SPYの市場価格・分配金等はYahoo Finance、商品の定義・経費は運用会社で確認。
10年2016-09-30〜2026-09-30、5年2021-09-30〜2026-09-30。月次121点/61点、共通日次2,485点。
月次は各月の最後の共通観測日。USD名目・米国CPI調整USD実質・JPY名目・日本CPI調整JPY実質を別に計算。
FXはFederal Reserve H.10のNY正午、ETF引け/BTC翌UTC00:00とは同時でない。日付を揃えた事後比較で実際の同時約定成績ではない。

## 主要結果（累積、%）

|期間|対象|USD名目|USD実質|JPY名目|JPY実質|
|---|---|---:|---:|---:|---:|
|10年|GLD|203.12|117.19|370.96|303.68|
|10年|BTC|13,638.65|9,744.17|21,245.74|18,196.35|
|10年|SPY|312.86|195.83|541.46|449.82|
|5年|GLD|131.91|88.80|227.06|186.10|
|5年|BTC|90.63|55.20|168.85|135.18|
|5年|SPY|90.00|54.69|167.97|134.40|

CAGR、全年度結果、DDのピーク/底は記事自動生成表とresults.jsonへ掲載。
10年USD名目CAGR：GLD11.73%、BTC63.60%、SPY15.23%。実質CAGRはそれぞれ8.06%、58.24%、11.46%。
10年最大DD（共通観測日・名目）：USDはGLD−26.40%、BTC−83.13%、SPY−33.72%。JPYは−24.39%、−82.98%、−33.74%。
全暦日のBTCの最大DDとは異なる。土日・FX欠測日を含めず、第8号との条件差を明記。

### 100万円を各対象へ別々に一括投資（円）

|期間|対象|JPY名目評価額|開始月の日本の購買力|
|---|---|---:|---:|
|10年|GLD|4,709,577|4,036,780|
|10年|BTC|213,457,408|182,963,493|
|10年|SPY|6,414,592|5,498,222|
|5年|GLD|3,270,637|2,861,007|
|5年|BTC|2,688,514|2,351,792|
|5年|SPY|2,679,653|2,344,041|

将来予測ではない。追加積立・引出し・為替ヘッジ・個人税/売買費用なし。数量の端数を許し、整数口数購入時の残余現金は再現しない。実質評価額は引出可能な現金額ではない。

## CPI・分配金・欠測監査

米国CPIはFRED CPIAUCNSとBLS原系列CUUR0000SA0を133か月分照合。
2025-10はFRED空欄/BLS「-」。政府閉鎖のBLS説明を確認し、補間しない。USD実質/CPI図はnullで途切れる。
端点・年末CPIは観測でき、当該期間全体の計算は可能。欠測月を推定入力していない。
日本CPIはe-Stat全国総合の2025年基準公式長期接続指数。旧基準を無調整で接続しない。
旧FRED日本系列は終了/404のため不採用。CPIは暦月に対応させ、公表前に知って売買できたと扱わない。
公表指数の丸めにより公式前年比表記とわずかな差はあり得る。

SPY40回の分配金を直前終値から別実装で再構成し、全日調整係数相対誤差1e-5未満（最大約6.07e-7）。
GLD分配金0、両ETFとも対象期間に分割なし。公式現在経費率GLD0.40%/SPY0.0945%。
過去の費用は市場価格等に内包されるため二重控除せず、現在費率が全期間不変とも仮定しない。
配当込み指数・現物金価格・日本の投資信託・個人の税引後収益とは同一視しない。

## 独立検証・解釈

本体のfloat計算から独立したDecimal45桁でCAGR・実質・為替・円評価額・年別・DDを検算。
元JSON/CSV/FRB表から日次全列・月末の選択・CPI月対応・図入力まで23,148項目を照合。
年別は前年12月最終共通観測日から年末、2026年は1〜9月途中経過。
高インフレ年は完全な2017〜2025年に限定し、米国12月CPI前年比>=4%、日本>=2%を編集上の基準とした事後分類。
年平均物価上昇やリアルタイムの売買ルールとは違う。2022年は全対象USD実質マイナスだがGLDのJPY実質はプラス。
長期購買力維持・短期連動・急落耐性・為替を分け、相関/インフレサプライズ/因果寄与率や最適配分を推計したとはしない。

## 出典・表示・SEO・AdSense点検

19 URLをGET・本文確認。元のGLDページ403は削除と断定せず、同じ費用・目的を確認できる運用会社SSGAページへ差替え。
JSDAのPDFは対象商品/外貨枠換算/再投資の資料として使用。外国税の直接説明はSBI証券の自社取扱FAQで確認し、個別税額は計算しない。
URL・取得日時・SHA256・採用した主張はsource-evidence.jsonとsources.jsonへ保存。

6図：USD長期推移、JPY100万円モデル、USD/JPY実質推移、年別リターン、最大DD、CPIと資産の別パネル。
加えて高インフレ年比較表。図に単位・期間・出典・欠測と尺度の制約、拡大リンクを掲載。
緑ヘッダー/白本文/日本語フォントを維持。H1–H3、目次、FAQ、比較表、編集者、調査/公開/更新日を実装。
title、meta description、canonical、OGP、Article JSON-LDを確認。薄い記事の量産・架空の専門家・保証表現なし。
運営者情報・編集方針・プライバシー・お問い合わせへの既存導線を維持。広告コード/申請/配置変更なし。
AdSenseの合格や順位/収益を保証しない。個別のNISA商品適格性・取扱いは記事で認定しない。

## テスト・既存機能

- Python全63件合格（既存54件＋新規9件）。資料欠落、入力改変、不正CAGR/実質/為替、未完全年の扱い等を検証。
- 欠月の負例テストは実一時ファイルで再現。模擬read_bytes/read_textの不整合を修正し、欠月を拒否する期待は維持。
- HTML13ページ構文エラー0、内部リンク・アンカー・SEO/構造化データ・既存記事回帰が合格。
- 外部資料19 URLの到達性合格。ソフト404・アクセス制限・PDF代替HTML・一時障害を区別。
- Chromium320/375/768/1280px、6図、表の局所スクロール、関連記事相互遷移、RSS描画正常、ブラウザー例外なし。
- build_site.pyのみで一覧9記事/サイトマップ13 URLへ生成。第9号は各1件、既存8記事保持。
- 既存第4/5/6/7/8号は関連記事追加のみ。既存の分析データ・RSS/Pages設定・ワークフロー・更新コードは変更なし。
- 最新mainの既存RSS更新をfast-forwardで保持。news.ymlは3時間cron有効、直近RSS/Pages実行成功を確認。
- actionlint、git diff --check合格。PR必須CIと競合・差分確認後のみマージし、Pagesと実URLを検証する。

## 再現と出典

数値CSV・圧縮原応答・結果・コード・図・監査記録：`articles/data/inflation/`。
コマンドと制約：`articles/data/inflation/METHOD.md`。計算再現はネットワーク不要。

主要出典：
- https://fred.stlouisfed.org/series/CPIAUCNS
- https://www.bls.gov/cpi/questions-and-answers.htm
- https://www.bls.gov/cpi/additional-resources/2025-federal-government-shutdown-impact-cpi-faq.htm
- https://www.stat.go.jp/data/cpi/1.html
- https://www.e-stat.go.jp/stat-search/file-download?fileKind=1&statInfId=000040482943
- https://www.federalreserve.gov/releases/h10/hist/dat00_ja.htm
- https://www.ssga.com/us/en/individual/etfs/spdr-gold-shares-gld
- https://www.ssga.com/us/en/intermediary/etfs/state-street-spdr-sp-500-etf-trust-spy
- https://www.bitstamp.net/api/

## 変更ファイル一覧

以下は第9号に必要な追加・変更の全ファイル。RSSデータはmain更新を保持し、本PRの編集対象に含めない。

- `ARTICLE_9_REVIEW.md`
- `articles/bitcoin-crash-history.html`
- `articles/bitcoin-vs-stocks-long-term.html`
- `articles/crypto-tax-japan-guide.html`
- `articles/data/inflation/METHOD.md`
- `articles/data/inflation/analyze_inflation.py.txt`
- `articles/data/inflation/annual-returns.png`
- `articles/data/inflation/annual-returns.svg`
- `articles/data/inflation/audit_inflation.py.txt`
- `articles/data/inflation/calculation-audit.json`
- `articles/data/inflation/cpi-and-assets.png`
- `articles/data/inflation/cpi-and-assets.svg`
- `articles/data/inflation/cpi.csv`
- `articles/data/inflation/daily.csv`
- `articles/data/inflation/drawdowns.png`
- `articles/data/inflation/drawdowns.svg`
- `articles/data/inflation/graph-audit.json`
- `articles/data/inflation/link-checks.json`
- `articles/data/inflation/million-yen.png`
- `articles/data/inflation/million-yen.svg`
- `articles/data/inflation/monthly.csv`
- `articles/data/inflation/prepare_inflation_data.py.txt`
- `articles/data/inflation/raw/BTC.gz`
- `articles/data/inflation/raw/FX.gz`
- `articles/data/inflation/raw/GLD.gz`
- `articles/data/inflation/raw/JP_OFFICIAL.gz`
- `articles/data/inflation/raw/SPY.gz`
- `articles/data/inflation/raw/USCPI.gz`
- `articles/data/inflation/raw/bls2015.gz`
- `articles/data/inflation/raw/bls2025.gz`
- `articles/data/inflation/real-wealth.png`
- `articles/data/inflation/real-wealth.svg`
- `articles/data/inflation/results.json`
- `articles/data/inflation/source-evidence.json`
- `articles/data/inflation/sources.json`
- `articles/data/inflation/usd-wealth.png`
- `articles/data/inflation/usd-wealth.svg`
- `articles/gold-bitcoin-stocks-inflation.html`
- `articles/new-nisa-beginners-guide.html`
- `articles/sp500-vs-all-country.html`
- `index.html`
- `scripts/analyze_inflation.py`
- `scripts/audit_inflation.py`
- `scripts/prepare_inflation_data.py`
- `sitemap.xml`
- `tests/test_inflation.py`
