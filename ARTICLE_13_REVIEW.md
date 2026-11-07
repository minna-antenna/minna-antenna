# 第13号 株式データ・品質監査

調査2026-11-07。6社：トヨタ7203、ソニー6758、任天堂7974、MUFG8306、NTT9432、日本製鉄5401。
2026-03-31株価/期末株数/資本、2025-04-01〜2026-03-31利益、期首資本2025-03-31。
5月公表の決算を使う事後学習用で、当時既知の投資シグナルや最新価格ランキングではない。
全6社の公式短信・株価原本・株数/自己株/期中平均を照合、入力と原本SHA256を保全。

市場規模は自己株控除後の期末株数。基本EPSは期中平均、BPSは期末株数、ROEは2点平均資本。
恒等式は期末株数EPS/PERと期末資本ROEへ統一した参考表を別掲。予想PERは同時点EPS未確認で省略。
Sonyは非継続含む全体損失326865百万円を使用しPER対象外、継続利益1030893と混同しない。
公開百万円入力からのEPS/BPS差は全社1銭未満。日本製鉄BPS1058.196881と公表1058.19の端数処理は厳密未確認、独自計算値を明示して使用。
価格はJPY/銘柄/日付/出来高を検証、配当調整adjclose不使用、基準日後の分割があれば停止。

独立Fraction/Decimal372照合合格。架空A/B、EPS/BPS差、利益半減、1対2分割、増資、自己取得、成長/恒等式を再計算。
Python102テスト（既存90+株式10+WAF検証2）、HTML完全17ページ0エラー、外部26リンクと内容照合、内部リンク/SEO/JSON-LDを検証。
HTTP202のJPX系算出ページはAWS WAF確認画面だった。アクセス制限へ正しく分類する検証と回帰テストを追加。
本文根拠は取得できるJPX公式PER/PBR用語集へ置換。失敗を成功扱いしない。計算基準は独自定義として明示。
グラフ5点SVG/PNG、図の元JSONとSHAを照合。PC/スマホ4画面幅、関連記事5本、RSS表示を確認。
一覧/sitemapは既存build_site.pyで13記事/17URLを自動生成。既存本文は関連リンクのみ追加。
RSSデータ/更新スクリプト/ワークフロー/3時間cron/Pages/保護設定を変更しない。
AdSense導入なし。公開後に13記事全体を読取中心で監査し、別途改善提案を報告する。

全入力・公表日・基準/限界・原本と出典・再現コードはarticles/data/stock-metrics/。

## 変更ファイル

- `ARTICLE_13_REVIEW.md`
- `articles/bitcoin-vs-stocks-long-term.html`
- `articles/data/stock-metrics/METHOD.md`
- `articles/data/stock-metrics/analyze_stock_metrics.py.txt`
- `articles/data/stock-metrics/audit_stock_metrics.py.txt`
- `articles/data/stock-metrics/calculation-audit.json`
- `articles/data/stock-metrics/companies.json`
- `articles/data/stock-metrics/companies.png`
- `articles/data/stock-metrics/companies.svg`
- `articles/data/stock-metrics/financial-evidence.json`
- `articles/data/stock-metrics/graph-audit.json`
- `articles/data/stock-metrics/growth.png`
- `articles/data/stock-metrics/growth.svg`
- `articles/data/stock-metrics/identity.png`
- `articles/data/stock-metrics/identity.svg`
- `articles/data/stock-metrics/link-checks.json`
- `articles/data/stock-metrics/price-cap.png`
- `articles/data/stock-metrics/price-cap.svg`
- `articles/data/stock-metrics/raw/price_5401.json.gz`
- `articles/data/stock-metrics/raw/price_6758.json.gz`
- `articles/data/stock-metrics/raw/price_7203.json.gz`
- `articles/data/stock-metrics/raw/price_7974.json.gz`
- `articles/data/stock-metrics/raw/price_8306.json.gz`
- `articles/data/stock-metrics/raw/price_9432.json.gz`
- `articles/data/stock-metrics/results.json`
- `articles/data/stock-metrics/source-evidence.json`
- `articles/data/stock-metrics/sources.json`
- `articles/data/stock-metrics/split.png`
- `articles/data/stock-metrics/split.svg`
- `articles/dividend-vs-index-investing.html`
- `articles/etf-vs-mutual-funds.html`
- `articles/market-cap-per-pbr-guide.html`
- `articles/new-nisa-beginners-guide.html`
- `articles/sp500-vs-all-country.html`
- `index.html`
- `scripts/analyze_stock_metrics.py`
- `scripts/audit_stock_metrics.py`
- `scripts/check_external_links.py`
- `sitemap.xml`
- `tests/test_external_links.py`
- `tests/test_stock_metrics.py`
