# 第12号 防犯情報・安全性・公開監査

仮想通貨詐欺の見抜き方とは？よくある手口と安全対策を徹底解説【2026年版】

調査日2026-11-07、本文11,250文字（空白・日付・目次・参考資料・関連記事を除く）。
専用ブランチfeat/article-12-scam-prevention。既存11記事とRSS機能を保持。

## 調査・実用内容

警察庁、金融庁、消費者庁、国民生活センター、IPA、Ethereum/ウォレット公式、
第二東京弁護士会、SECの20出典を実取得し内容照合。時刻/URL/SHA256/主張対応を保存。

14手口×接触/誘い文句/兆候/仕組み/予防/初動：SNS投資、著名人、偽グループ、
偽取引所/アプリ、フィッシング、秘密情報窃取、偽配布/NFT、悪意ある承認、
ラグプル、ポンジ、ロマンス、AIなりすまし、出金追加費用、回収二次詐欺。
誘い文句とフローは編集部整理・説明例で、実事件の引用や統計ではないと表示。
被害額/件数/逮捕/返金率を創作せず、SNS詐欺全体と暗号資産だけの統計も混同しない。

実用UI：理由と対処付き12チェック、状況別初動A-H、相談先6枠、SNSの流れ、
登録確認フロー、ウォレット対策、二次被害確認表、初動SVG/PNG。

## 相談先・登録監査

- #9110は非緊急相談、110は緊急の事件・身体の危険等。全国一律の受付時間を保証しない。
- 受付の地域例は現在の愛知県警公式案内で平日9-17、祝日/年末年始除くと確認。
- 188は地域の相談窓口接続、相談無料/接続後通話料あり。バックアップ相談の時間を188全体にしない。
- FSA詐欺専用0570-050588/IP03-6206-6066と一般0570-016811/IP03-5251-6811を区別。
  公式の平日10-17電話受付、Web24時間受付と即時応対の違いを確認。
- 7番号（2組のIP番号含む）を取得本文の正規化数字へ照合。source-evidence.jsonに保存。
  当初の単純な「6番号」テスト期待は相談先6枠との混同だったため、根拠の7番号集合を直接検証する形に修正。
- 一般相談室はあっせん/仲介/調停なし、金融機関や警察も回収保証としない。
- 取得した交換業者一覧の基準日2026-09-30と取得Nov7を区別。公式入口から最新一覧を探す案内。
  一覧にURL欄があると決めつけず、掲載連絡先等から独立確認。仲介業と交換業を区別。
  登録番号流用に注意、登録は安全・利益・価値保証ではないと明記。

Gov-online相談時間403はアクセス制限、旧MetaMask承認URL404は不在として記録。
現在到達でき本文を確認した県警/MetaMask公式資料へ差し替え、失敗の成功扱いなし。

## 防御手順の監査

ログイン情報と秘密鍵/シード、接続解除と承認取消を分けた。
Kraken/MetaMask公式に基づき、安全な端末と新しい復元フレーズ、旧シード継続禁止を説明。
同じシードで口座追加しても安全でない。自動流出が疑われる財布へガス資金を繰り返し足させない。
承認取消にも署名/費用があり、取消で過去送金や全権限が戻ると説明しない。
ハードウェアウォレット/パスキー/少額テストの限界を記載し、完全安全の保証を避ける。
不審アプリ端末を切り離し、別の安全な端末で保護。記録保全と被害拡大防止を両立。
銀行/取引所へ公式経路で迅速連絡、TXID等の記録。秘密情報を提出記録へ含めさせない。
被害者を責めず、回収保証・前払い・偽支援への注意を掲載。
危険サイト直リンク、攻撃コード、資産窃取手順、救済代行/自動移転なし。

## UI・コードの安全性

入力はcheckbox12個のみ。フォーム/テキスト/秘密情報/hidden入力/iframe等なし。
JSはチェック状態に応じたtextContent表示と解除のみ。送金SDK/ウォレット接続/
fetch/XHR/WebSocket/beacon/Storage/cookie/eval/innerHTML等の処理なし。
点数判定なし、0選択も安全と認定しない。全項目の理由・対処は常時表示。
キーボード操作、解除、選択中の通信ゼロ、JS無効時も本文・窓口等可読と確認。
公式窓口への連絡/提出・読者データ収集は実行しない。

## 検証結果

- Python90テスト（既存82＋新規8）合格。欠落/重複/未確認出典/未監査統計の負例を拒否。
- HTML完全16ページ0エラー、内部リンク/アンカー/全記事SEO/Article構造化データ正常。
  Google所有権確認ファイルはHTML文書ではなく変更しない。
- 出典20URL実GET200、主張・相談先の内容対応確認。
- 初動図SVG/PNGのハッシュとguide.json、コードコピー/HTML表・チェックリスト同期。
- Chromium320/375/768/1280px：全体横溢れなし、図読込、表の横スクロール、
  チェックのキーボード操作/選択解除/非送信、関連記事5本往復、ニュース描画が正常。
  スマホのチェックカードと初動図を目視。JS無効でも全重要情報あり。
- build_site.pyで12記事・16URL、再生成の冪等性、一覧/サイトマップ手動編集なし。
- actionlint成功。RSS別出力テスト10フィード/60件/0エラー。
- 作業中のscheduled RSS実行42335684763が成功、mainはa213bb6へ進行。
  変更はdata/news.jsonのみ。未コミットの第12号を保持してfast-forward取り込み済み。
- ニュースJSON/スクリプト/3時間cron `7 */3 * * *`、既存ワークフロー/Pages/保護設定は変更しない。
- 既存5記事は関連記事リンク追加のみ、分析本文/元データを保持。
- AdSense申請/広告コード/第13号制作なし。運営者・訂正方針と整合。

## 公開条件

必須CI合格、競合なし、意図しない変更なしを確認して通常マージ。
既存Pages公開完了後、実URLで本文/図/データの一致、一覧1件、sitemap1件、
既存11記事、チェックリスト操作/非送信/4画面幅/JS無効時、関連記事、RSSを再検証。

## 変更ファイル一覧

- `ARTICLE_12_REVIEW.md`
- `articles/bitcoin-crash-history.html`
- `articles/bitcoin-vs-stocks-long-term.html`
- `articles/crypto-eth-sol-xrp-comparison.html`
- `articles/crypto-scam-prevention.html`
- `articles/crypto-tax-japan-guide.html`
- `articles/data/scam-prevention/METHOD.md`
- `articles/data/scam-prevention/build_scam_guide.py.txt`
- `articles/data/scam-prevention/checklist.js`
- `articles/data/scam-prevention/content-audit.json`
- `articles/data/scam-prevention/diagram-audit.json`
- `articles/data/scam-prevention/first-response.png`
- `articles/data/scam-prevention/first-response.svg`
- `articles/data/scam-prevention/guide.json`
- `articles/data/scam-prevention/link-checks.json`
- `articles/data/scam-prevention/source-evidence.json`
- `articles/data/scam-prevention/sources.json`
- `articles/gold-bitcoin-stocks-inflation.html`
- `index.html`
- `scripts/build_scam_guide.py`
- `sitemap.xml`
- `tests/test_scam_guide.py`
