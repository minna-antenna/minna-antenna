# AdSenseサイト接続コード

対象: https://topic-kichi.com/ 。パブリッシャーID: `ca-pub-8155299200535467`。

[Google公式の設置案内](https://support.google.com/adsense/answer/9274516?hl=ja)と[サイト追加・確認の案内](https://support.google.com/adsense/answer/12169212?hl=ja)に従い、次のコードをhead内へ1件ずつ配置する。

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-8155299200535467" crossorigin="anonymous"></script>
```

## 対象と維持する内容

トップ、articles配下の独自13記事、about/privacy/contactの計17ページを対象とする。Google Search Consoleの所有権確認用HTMLは単なる確認文字列のファイルでheadを持たないため、内容を変更しない。旧トップの複製・ZIP・資料類はPages公開対象でなく、今回コードを追加しない。

変更は上記scriptのみ。記事本文、title/description、canonical、OG、構造化データ、サイトマップ、robots、記事内リンクを維持する。RSS停止workflow、停止JSON、再開用コード、Pagesの公開用ファイル選定、Custom domain設定も変更しない。

このscriptはAdSenseの共通ライブラリを読み込む。広告枠のins要素、広告枠ID、push呼び出し、自動広告の有効化設定は追加しない。AdSense管理画面の設定操作も行わない。配信の挙動はGoogle側のアカウント・サイト設定にも依存するため、このコードだけを「確認専用で外部通信を行わないタグ」や「広告が一切表示されない保証」として説明しない。

## 自動生成での維持

`build_site.py`の`ensure_adsense_code`が、記事一覧の生成と合わせて対象ページを処理する。公式エンドポイントの既存loaderを重複・誤ったclient・body内配置から、指定IDのhead内1件へそろえる。既に正しい1件がある場合はソースを変更しない。広告表示用のコードは生成しない。

新規記事は単一のheadを持つ完全なHTMLとして作成する。コード未設置の新規記事や固定ページにもビルド時に補う。HTML・メタ情報の検証を終えてから書き込み、headが不正な場合は生成物を書き換える前にエラーにする。Google確認ファイルやデータファイルへ挿入しない。

## 検証

- 全144テスト通過（既存139件を含む）。既存の「広告コードなし」や外部scriptの許可リストのテストは、今回依頼された正確なloaderだけを許可し、広告枠・自動広告設定の禁止、RSS停止の検査を維持するよう調整した。
- 対象17ページでHTMLを解析し、head内に指定ID・async・crossorigin=anonymousのscriptが1件だけあることを確認。
- 重複・body内配置・異なるclient IDの整理、新規記事への挿入、再ビルドの冪等性、不正なhead時の書き込み防止を検証。
- Pages workflowの実際のステージングコマンドを実行し、公開用成果物の17ページにも同じコードが1件ずつ含まれることを確認。ニュースJSONは成果物にない。
- 17ページのソースはベースmainから当該scriptだけを追加したものと一致。既存のGoogle確認ファイルは変更なし。

```sh
python -m unittest discover -s tests -v
python scripts/build_site.py
```

今回の変更はドラフトPRで提示する。mainへのマージ、Pages公開、AdSense管理画面での確認・審査リクエストは行わない。承認後に公開されたHTMLソースを確認し、その後利用者がAdSense側で確認する。コードの配置検証は、Googleでの所有権確認完了や審査通過を意味しない。

ブラウザでも公開用成果物の17ページでhead内のloaderを確認し、390px/1440px幅でトップと13記事への導線、RSS停止表示を確認した。検証時はAdSenseライブラリを空のテスト応答に置き換え、実際の広告リクエストやGoogle側の所有権確認は実行していない。この検証はページ側の配置・読み込み先を確認するもので、Googleの実ライブラリの配信挙動を保証しない。
