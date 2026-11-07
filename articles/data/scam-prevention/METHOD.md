# 第12号 制作・安全性監査・再現手順

調査日2026-11-07。金融数値のシミュレーション記事ではなく、防犯情報の公式資料照合。
被害件数/額/返金率の統計は使用せず、手口の誘い文句・フローは編集部の説明例と表示。

```
python scripts/build_scam_guide.py --check
python -m unittest discover -s tests -v
python scripts/build_site.py
python scripts/check_external_links.py --article articles/crypto-scam-prevention.html --output articles/data/scam-prevention/link-checks.json
```

再生成は --checkを外す。図PNG/SVGはMatplotlib3.10.8：
`MPLCONFIGDIR=/tmp/article12-mpl python scripts/build_scam_guide.py --diagram`。
編集データguide.jsonから14種×7項目、チェック12項目、初動A-H、相談先6枠を生成。
トップページとsitemapは既存build_site.pyで生成、手編集しない。

## 出典監査

sources.jsonに取得URL・最終URL・UTC時刻・SHA256。
source-evidence.jsonは20資料の内容対応と、窓口の番号を取得本文へ照合した記録。
HTTP200だけで根拠十分とせず、電話・役割・時間や資料の対象時点を読んで照合。
金融庁の一覧は2026-09-30現在、取得Nov7。登録は利益・安全の保証ではない。
仲介業と交換業の区分、登録番号流用、URL欄がない一覧での独立確認を説明。

受付条件を混同しない：#9110は地域差（愛知9-17は地域例のみ）、188は自治体接続。
188ページのバックアップ相談の10-16を全体の時間としない。
FSA詐欺専用0570-050588/IP03-6206-6066と一般0570-016811/IP03-5251-6811を区別。
いずれも確認した電話受付は平日10-17。Web24時間受付は即時対応ではない。
110は緊急対応、被害金回収を自動的に依頼する番号ではない。

Gov-online相談時間ページ403はアクセス制限、旧MetaMask承認説明404はURL不在。
別の現行公式ページ本文に置換し、元の失敗記録を保存。失敗を成功へ読み替えない。

## 防御手順の限界

秘密鍵/復元フレーズとログインパスワード、接続解除と承認取消を区別。
同じ復元フレーズの別口座を新しい安全な財布と呼ばない。
Kraken/MetaMaskの公式防御手順を基に安全な端末・新フレーズの利用を案内。
自動流出が疑われる財布へガス代を繰り返し足させず、公式支援へ独立確認。
不審承認の取消にも危険や費用があり、過去送金の回復や全権限取消を保証しない。
各ネットワーク/製品で手順が異なるため、個人資産の救出代行コードは掲載しない。

## UI・安全性ゲート

- 入力はcheckbox12個とtype=buttonの解除ボタンだけ。form/textarea/text/hidden入力なし。
- チェック状態はメモリ内表示だけ、JSにfetch/XHR/送金SDK/ウォレット接続/Storage/cookieなし。
- 0選択も安全判定しない、複数選択も詐欺確定スコアにしない。理由と対処は常時表示。
- JavaScript無効でも全文・チェック項目・初動・連絡先が読める。
- 実ブラウザでキーボード操作・解除・再読込、外向き要求なし、4画面幅で図と表を検証。
- 原データ変更の負例テスト、JS通信処理の静的検査、出典対応・リンク/SEOも検証。
- RSSニュースデータ/スクリプト、3時間cron、Pages/保護設定は変更しない。

本サイトから相談窓口への連絡・情報提供は実行せず、読者の私的情報も収集しない。
