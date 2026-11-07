# 第10号 品質・金融データ監査

記事：高配当株とインデックス投資はどっちが有利？配当金・20年後の資産・新NISAを徹底比較

調査日：2026-11-07。本文10,774文字（空白・日付・目次・参考資料・関連記事を除く）。
制作専用ブランチ feat/article-10-dividend。既存9記事・ニュースデータを保持。

## 分析・一次資料

VYM / SPY、USD、2016-09-30〜2026-09-30 と2021-09-30〜2026-09-30。
Yahoo Finance日次終値・調整後終値・現金分配の原本をgzipで凍結、SHA-256を保存。
取得時刻、原URL、計算コード、結果JSON、再現条件はarticles/data/dividends/。
VYMも指数投資であるため、高配当対指数は排他的分類ではないと説明。

|ETF|5年累積 / CAGR|10年累積 / CAGR|過去12か月分配利回り|
|---|---|---|---|
|VYM|73.43% / 11.64%|191.28% / 11.28%|2.37%|
|SPY|90.00% / 13.70%|312.86% / 15.23%|0.99%|

分配利回りは2025-09-30より後〜2026-09-30の分配金合計÷最終終値。
SEC利回りや予想配当、税引後の受取額ではない。
分配調整を前日終値と現金分配から再構成、両資産の最大相対誤差6e-7未満。
原本取得範囲に未審査分割があれば停止。MDDは日次調整後価格、変動率は月末標本。

### 公表値との区別

VYM発行会社9月末市場価格年率11.64/11.28%と小数第2位で一致。
SPY公表市場価格年率13.65/15.18%と当分析13.70/15.23%は約0.05ポイント異なる。
分配落ち遡及調整系列と発行会社市場価格リターンを同一視せず、原本と算定法の違いを明示。
差を消すための価格変更・期待値変更を行っていない。公式の再投資価格への厳密な一致は
未検証で、当分析をNAVや公式指数実績、個人手取りとして説明しない。
この小差から将来優劣や個別推奨を導かない。

### 税務・出典

2026-11-07確認、国税庁1330/1331/1463/1240は2026-04-01法令等。
国内上場配当の一般税率・課税方式と例外、譲渡益の取得費控除、外国税額控除の条件を区別。
金融庁、日本証券業協会2026年9月Q19-22/35-38でNISA枠・国内受取方式・再投資・元本払戻を照合。
外国課税はNISA日本非課税と別。外国税の一律税率・税引後個人試算を断定しない。
証券会社公式FAQは外国株実務の補足で、税法の代替ではない。
旧投資信託協会税金URLは200でも一般案内ページへ転送、根拠として除外しJSDAQ37-38を採用。
Vanguard動的ページも実数値が本文に無いため静的公式ファクトシートを採用。
HTTP到達性とは別にsource-evidence.jsonに内容・対象日・取得ハッシュを記録。

## 仮定モデル

月末3万円、実効年率0/3/5/7%、10/20/30年。税費用・FXなし、継続運用費控除後の仮定率。
100/300/500/1000万円×仮定分配利回り2/3/4/5%、月平均は年間÷12で支払頻度ではない。
初期100万円、総収益6%=価格3%+分配3%、20年、税費用なし、受取現金利息なし。
再投資と受取型は運用残高・累計現金・合計を分ける。配当を総収益へ二重加算しない。
売却型も年初残高3%を年末受取なら、同条件で残高と累計現金が一致。
税引後・固定生活費・安全な取り崩し率・将来予測のモデルではない。

## 品質検証

- Python 73テスト合格（既存63維持＋新規10）。異常CAGR、利回り、下落日、
  二重計上、月平均、元本、原本ハッシュ、未審査分割などの負例も拒否。
- 独立監査6,033照合：Decimal45桁、月ごとの積立、現金保存、
  全日次接頭最大によるMDD、CAGR、分配係数、年別・曲線を独立検算。
- HTML完全ページ14件0エラー。既存Google所有権確認ファイルはHTML文書ではないため変更しない。
- 全記事内部リンク・目次・Article JSON-LD・canonical/OGPを検証。
- 出典11URLが実GETで200・本文/資料の対応を確認。汎用200転送は根拠に使用しない。
- グラフ7点、SVG+PNG計14ファイルのハッシュと結果JSONを照合。
- Chromium320/375/768/1280px、7図読込、全体横はみ出しなし、表だけスクロール。
  4関連記事の往復、運営/プライバシー/連絡ページ、ニュース描画を確認。スクリーンショット目視。
- build_site.pyによる記事10件・サイトマップ14URL。再実行は同一、手動一覧編集なし。
- RSSを一時ファイルへ実取得：10フィード成功、0エラー、60件。
- actionlint合格。既存3時間cron `7 */3 * * *`、ワークフロー、更新スクリプト、news.json未変更。
- AdSense申請・コード追加なし。運営方針と訂正連絡先・出典を掲載、架空資格等なし。
- mainとの差分は記事・関連リンク・分析データ/コード・テスト・生成一覧・監査記録のみ。

## 自動公開条件

PR必須CI成功、競合なし、意図しないファイル変更なしを確認後にのみマージ。
保護/Pages設定/ワークフローは変更せず、既存自動公開を利用。
公開後にHTTP200、本文・7図・データのハッシュ、一覧1件、サイトマップ1件、
既存9件、関連記事、RSSの実描画と既存設定を確認する。

第11号以降は制作しない。

## 変更ファイル一覧

- `ARTICLE_10_REVIEW.md`
- `articles/bitcoin-vs-stocks-long-term.html`
- `articles/data/dividends/METHOD.md`
- `articles/data/dividends/accumulation.png`
- `articles/data/dividends/accumulation.svg`
- `articles/data/dividends/analyze_dividends.py.txt`
- `articles/data/dividends/audit_dividends.py.txt`
- `articles/data/dividends/calculation-audit.json`
- `articles/data/dividends/drawdowns.png`
- `articles/data/dividends/drawdowns.svg`
- `articles/data/dividends/graph-audit.json`
- `articles/data/dividends/income.png`
- `articles/data/dividends/income.svg`
- `articles/data/dividends/link-checks.json`
- `articles/data/dividends/raw/SPY.json.gz`
- `articles/data/dividends/raw/VYM.json.gz`
- `articles/data/dividends/reinvestment.png`
- `articles/data/dividends/reinvestment.svg`
- `articles/data/dividends/results.json`
- `articles/data/dividends/returns.png`
- `articles/data/dividends/returns.svg`
- `articles/data/dividends/source-evidence.json`
- `articles/data/dividends/sources.json`
- `articles/data/dividends/wealth.png`
- `articles/data/dividends/wealth.svg`
- `articles/data/dividends/withdrawal.png`
- `articles/data/dividends/withdrawal.svg`
- `articles/dividend-vs-index-investing.html`
- `articles/gold-bitcoin-stocks-inflation.html`
- `articles/new-nisa-beginners-guide.html`
- `articles/sp500-vs-all-country.html`
- `index.html`
- `scripts/analyze_dividends.py`
- `scripts/audit_dividends.py`
- `sitemap.xml`
- `tests/test_dividends.py`
