# 第8号：制作・データ監査・公開前検証

調査日：2026-11-06 UTC。第8号のみを制作。第9号以降は未着手。

## 記事

ビットコインはなぜ暴落する？過去の下落原因と回復までの期間を徹底比較

予定URL： https://minna-antenna.github.io/minna-antenna/articles/bitcoin-crash-history.html
本文約9,300字（空白・目次・参考文献等を除く）。公開後にも実URLで文字数と内容を確認する。

## データ条件・制約

Bitstamp公式BTC/USD現物日足OHLC。UTC日付2013-01-01〜2026-11-05、取得2026-11-06。
closeはUTC日足終了時、API日付は区間開始ラベル。翌日00:00 UTC/09:00 JST境界。
日中high/low・他取引所価格・円価格と混合しない。全リクエストURL・取得日時・SHA256を公開。
CSV5,057暦日を元応答と全フィールド照合。元応答6個の943重複は完全一致を確認して排除。
出来高ゼロ2015-01-06/07/08を実取引終値として除外し、5,054日を分析。図は欠測として補間しない。

5つの明示的な期間の各日のrunning maximumに対する最大下落を採用。最初の同値を採る。
回復は底の後に選定ピーク以上へ戻る最初の有効終値。抽出期間終了後もデータ最終日まで探索。
局所高値を使う2020年と長期局面は基準が異なる。全史上の網羅的な順位・独立した5標本とは主張しない。
未回復はnullで保持し、経過日数を確定回復日数に置き換えない。

| 対象期間 | 下落率 | 回復日 | ピーク→回復 | 底→回復 |
|---|---:|---|---:|---:|
|2013–2015|-84.86%|2017-02-23|1,177日|771日|
|2017–2018|-83.43%|2020-11-30|1,080日|716日|
|2020年1–3月|-53.28%|2020-07-27|164日|137日|
|2021–2022|-76.66%|2024-03-04|847日|469日|
|2024–2026|-53.08%|未回復|395日経過・未回復|未回復|

100万円モデルは為替固定、費用・税金なし。底の評価額は順に151,421/165,707/467,160/233,366/469,230円。
実際の日本円投資成績ではない。価格比率は丸めず、最終金額だけ1円四捨五入（half-up）。

## 独立検算

本体Decimalの走査とは別に、整数セント/Fractionの全過去候補探索でピーク・底・回復・日数・率・円モデルを監査。
元データ5,057行、独立83項目を照合。ピーク/底/回復/最終日の15点を公式APIに個別再照会し一致。
2013-12-04/2020-03-12/2026-11-05は24時間足の最終終値とも一致。応答はraw/point-*に保存。
データ変更、不正な日付、回復日の後付け変更、根拠のない円評価額等はテストで拒否。

## 一次資料と解釈

公式資料13件をGET・本文確認。URL・日時・ハッシュと確認した主張をsource-evidence.jsonへ保存。
Bitstamp APIと2015年再開発表、MtGox管財人報告、CME先物上場通知、CFTC注意喚起、
FRBの2020年/2022年声明と研究、シカゴ連銀研究、SEC2022年提訴・2024年ETP声明、Bitcoin.org、金融庁。

FRBの利上げ開始・FTX等の信用問題・市場変化という事実と、下落の原因に関する解釈を区別。
単独原因・寄与率・清算総額・大口売却者・特定地政学事件との因果・株式相関係数は未推計と明記。
確認できない2025–2026年の「理由」は作らず価格観測に限定。重要な数値・公表事実に未解決の不一致なし。
過去の回復を将来の保証にしない。研究者の見解と規制当局の公式決定を区別。

## グラフ・SEO・品質

長期USD終値（対数）、対象5期間の下落率、ピークから回復の日数、100万円の下落モデル、半減期と暴落の時系列の5図。
SVG/PNGと入力JSON、ハッシュ記録を保存。未回復バーは斜線とNOT RECOVEREDで区別。
表・図に通貨・単位・対象期間・出典・制約を記載。拡大リンク・数値表・代替テキストも提供。

title/meta description/canonical/OGP/Article JSON-LD/H1–H3/目次/FAQ/著者・調査日・更新日を実装。
既存の緑ヘッダー・白本文を維持。外部ライブラリ・広告コードは追加しない。
運営者情報・編集訂正方針・プライバシー・問い合わせの導線を保持。誇大な金融表現や架空の監修なし。
AdSense申請・広告有効化・合格保証は行わない。

## 検証結果

- 全Python54件合格。既存45件を維持し、新規9件でデータ・数値・回復・図・掲載・資料を検証。
- HTML12ページで構文エラー0。内部リンク・アンカー・SEO・構造化データも回帰合格。
- 外部13 URLはGET成功。ソフト404・PDF代替HTML・アクセス制限・通信失敗を成功扱いしない。
- Chromium 320/375/768/1280pxで本文・5図・表スクロール・関連記事相互遷移・RSS描画、例外なし。
- 既存build_site.pyのみで一覧8件・サイトマップ12 URLへ生成。第8号各1件、既存7記事保持。
- 第1/2/3/4/7号は関連記事リンク追加だけ。第1号は半減期、第2号は4年周期という既存の対応を維持。
- news.yml/site.yml/pages.yml、update_news.py、data/news.json、既存記事データは無変更。
- actionlint・git diff --check合格。最新mainから専用ブランチで実装。
- 必須CI成功・競合なし・差分確認後にのみマージ。その後Pages成功と実URL検証を行う。

## 主な一次資料URL

- https://www.bitstamp.net/api/
- https://blog.bitstamp.net/post/bitstamp-is-open-for-business-better-than-ever/
- https://www.mtgox.com/img/pdf/20140723_report_en.pdf
- https://www.cmegroup.com/notices/ser/2017/12/SER-8051R.html
- https://www.federalreserve.gov/newsevents/pressreleases/monetary20200315a.htm
- https://www.federalreserve.gov/newsevents/pressreleases/monetary20220316a.htm
- https://www.sec.gov/newsroom/press-releases/2022-219
- https://www.sec.gov/newsroom/speeches-statements/gensler-statement-spot-bitcoin-011023
- https://bitcoin.org/en/halving

## 変更ファイル一覧

以下はこのPRで追加・変更する全ファイル。index/sitemapは自動生成結果。

- `ARTICLE_8_REVIEW.md`
- `articles/bitcoin-crash-history.html`
- `articles/bitcoin-four-year-cycle.html`
- `articles/bitcoin-halving.html`
- `articles/bitcoin-vs-stocks-long-term.html`
- `articles/crypto-eth-sol-xrp-comparison.html`
- `articles/crypto-tax-japan-guide.html`
- `articles/data/bitcoin-crash/METHOD.md`
- `articles/data/bitcoin-crash/analyze_bitcoin_crashes.py.txt`
- `articles/data/bitcoin-crash/audit_bitcoin_crashes.py.txt`
- `articles/data/bitcoin-crash/calculation-audit.json`
- `articles/data/bitcoin-crash/chart-data.json`
- `articles/data/bitcoin-crash/drawdowns.png`
- `articles/data/bitcoin-crash/drawdowns.svg`
- `articles/data/bitcoin-crash/fetch_bitcoin_crashes.py.txt`
- `articles/data/bitcoin-crash/graph-audit.json`
- `articles/data/bitcoin-crash/halving-timeline.png`
- `articles/data/bitcoin-crash/halving-timeline.svg`
- `articles/data/bitcoin-crash/link-checks.json`
- `articles/data/bitcoin-crash/long-price.png`
- `articles/data/bitcoin-crash/long-price.svg`
- `articles/data/bitcoin-crash/million-yen.png`
- `articles/data/bitcoin-crash/million-yen.svg`
- `articles/data/bitcoin-crash/observations.csv`
- `articles/data/bitcoin-crash/point-checks.json`
- `articles/data/bitcoin-crash/raw/bitstamp-2013-01-01-2015-09-27.json`
- `articles/data/bitcoin-crash/raw/bitstamp-2015-09-28-2018-06-23.json`
- `articles/data/bitcoin-crash/raw/bitstamp-2018-06-24-2021-03-19.json`
- `articles/data/bitcoin-crash/raw/bitstamp-2021-03-20-2023-12-14.json`
- `articles/data/bitcoin-crash/raw/bitstamp-2023-12-15-2026-09-09.json`
- `articles/data/bitcoin-crash/raw/bitstamp-2026-09-10-2026-11-05.json`
- `articles/data/bitcoin-crash/raw/point-2013-12-04-daily.json`
- `articles/data/bitcoin-crash/raw/point-2013-12-04-hourly.json`
- `articles/data/bitcoin-crash/raw/point-2015-01-14-daily.json`
- `articles/data/bitcoin-crash/raw/point-2017-02-23-daily.json`
- `articles/data/bitcoin-crash/raw/point-2017-12-16-daily.json`
- `articles/data/bitcoin-crash/raw/point-2018-12-15-daily.json`
- `articles/data/bitcoin-crash/raw/point-2020-02-14-daily.json`
- `articles/data/bitcoin-crash/raw/point-2020-03-12-daily.json`
- `articles/data/bitcoin-crash/raw/point-2020-03-12-hourly.json`
- `articles/data/bitcoin-crash/raw/point-2020-07-27-daily.json`
- `articles/data/bitcoin-crash/raw/point-2020-11-30-daily.json`
- `articles/data/bitcoin-crash/raw/point-2021-11-08-daily.json`
- `articles/data/bitcoin-crash/raw/point-2022-11-21-daily.json`
- `articles/data/bitcoin-crash/raw/point-2024-03-04-daily.json`
- `articles/data/bitcoin-crash/raw/point-2025-10-06-daily.json`
- `articles/data/bitcoin-crash/raw/point-2026-06-30-daily.json`
- `articles/data/bitcoin-crash/raw/point-2026-11-05-daily.json`
- `articles/data/bitcoin-crash/raw/point-2026-11-05-hourly.json`
- `articles/data/bitcoin-crash/recovery-days.png`
- `articles/data/bitcoin-crash/recovery-days.svg`
- `articles/data/bitcoin-crash/results.json`
- `articles/data/bitcoin-crash/source-evidence.json`
- `articles/data/bitcoin-crash/sources.json`
- `index.html`
- `scripts/analyze_bitcoin_crashes.py`
- `scripts/audit_bitcoin_crashes.py`
- `scripts/fetch_bitcoin_crashes.py`
- `sitemap.xml`
- `tests/test_bitcoin_crashes.py`
