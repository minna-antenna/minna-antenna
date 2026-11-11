# topic-kichi.comへのURL移行

移行元: https://minna-antenna.github.io/minna-antenna/  
移行先（正規URL）: https://topic-kichi.com/  
調査日: 2026-11-11（日本時間）

## 変更範囲

トップ、独自13記事、about/privacy/contactの計17ページのcanonical、OG URL、OG画像URL、Article構造化データ内の自サイトURLを新ルートへ統一する。記事のタイトルや本文の説明・数値は変更せず、自サイトの絶対URLだけ置き換える。相対リンクは新しいルートでも同じファイル構成で解決するため維持する。記事から`../#news`へのリンク先は、RSS停止・公式サイト案内のセクションとして維持する。

`build_site.py`のBASE、sitemapの全17 URL、robotsのSitemap指定とAllowパスを更新する。再生成・再実行でも旧ドメインへ戻らないようテストする。公開成果物全体に旧ドメインが残らないことを検証した。

読み取り専用の`monitor_indexing.py`もBASEとURLの許可ホストを更新し、新サイトと`sc-domain:topic-kichi.com`のみ対象とする。旧プロパティ設定はネットワークアクセス前に拒否する。Search Consoleの登録、プロパティ追加、所有権確認、サイトマップ送信、AdSense登録は今回行わない。GitHub変数GSC_SITE_URLの現設定はAPIが403となり確認できなかった。必要なら利用者が新サイトの権限を確認して別途変更する。旧プロパティを自動的に書き換えることはしない。

過去のレビュー記録、非公開用の旧トップ複製・配布ZIPには当時の旧URLを残す。移行検証の旧URLや否定テストも意図的に保持する。これらをPagesへ公開する変更はしない。

## GitHub Pagesの設定維持

読み取りAPIで以下を確認した。

- build_type: workflow
- Custom domain: topic-kichi.com
- 証明書: approved。対象はtopic-kichi.comとwww.topic-kichi.com、有効期限2027-02-09
- RSS更新workflow: disabled_manually
- HTTPS強制: **false（未有効）**

Custom domainとDNSの設定は既に完了しているため変更しない。GitHub Actions公開の場合、CNAMEファイルは不要で無視されると[GitHub公式ドキュメント](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)にある。CNAMEファイルを追加して設定維持を保証する方法は採らず、Pages workflowで既存のbuild_typeとcnameを読み取って確認する。ドメインがtopic-kichi.comでなければ公開前に停止し、設定を書き換えない。既存のconfigure-pages/upload/deploy構成を維持する。

今回の作業はブランチとドラフトPRだけに保存し、mainへのマージやデプロイ、Pages設定変更、DNS操作を行わない。

## 公開サイトへの実測と残件

[HTTP検証の記録](../reports/domain-migration-2026-11-11/http-checks.json)を参照。

| 対象 | 実測結果 |
|---|---|
| https://topic-kichi.com/ と13記事・固定3ページ | 全17 URLで200。HTTPS接続の証明書検証を有効にして取得 |
| https://www.topic-kichi.com/ と半減期記事 | 301でhttps://topic-kichi.com/の対応パスへ転送、最終200 |
| http://topic-kichi.com/ と半減期記事 | リダイレクトせずHTTPのまま200 |
| http://www.topic-kichi.com/ と半減期記事 | 301でhttp://topic-kichi.com/の対応パスへ転送、最終200 |
| 旧github.ioの全17 URL | 301で新ドメインの対応パスへ転送し、全件200。ただし転送先は現在HTTP |

**残件: Enforce HTTPSの有効化。** HTTPSページ自体は動くが、HTTPからHTTPSへの統一はまだ完了していない。GitHub側で返す旧URLのLocationも現在はHTTPなので、canonicalの変更だけではこの転送応答をHTTPSへ変更できない。ユーザーの確認後にSettings → Pages → Enforce HTTPSを有効にし、HTTP・www・旧URLから最終的に新ドメインのHTTPSへ到達することを再確認する。これは既存の設定を確認したうえで行う別の本番操作で、今回勝手に有効化しない。JavaScriptやmeta refreshによる代替転送は追加しない。

今確認した200は新ドメインで既存ページを開けるという実測であり、このPRのcanonical・sitemap変更が本番に反映済みという意味ではない。

## 検証と反映後の確認

- 全139テスト通過。既存の内部リンク・fragment、Article/OG/canonical、独自計算・RSS停止を維持。新たに新ドメインの全URL一致、旧ホストの監視対象除外、Pagesドメイン不一致時の公開停止を検証。
- 13記事はベースmainのHTMLから旧自サイトURLを新URLへ置換したものと一致し、本文の改変なし。
- build_siteの再実行、公開用ステージング後の全ファイルで旧ドメイン残存なし。news.jsonは公開成果物にない。
- PC・スマートフォンでローカル公開成果物の17ページを表示し、画像・相対リンク・canonical・RSS停止表示を確認する。新URLの画像を確認する際もローカル成果物へルーティングし、本番の新メタデータ反映と混同しない。
- 承認後のマージ・公開時には、新URLのcanonical・OG・構造化データ、公開sitemap.xmlの17 URL、ルートrobots.txt、RSS JSONの404を本番で再確認する。
- HTTPS強制を有効化した場合にはHTTP/www/旧URLの転送を再検証する。Search Console・AdSenseへの登録操作はこのPRの作業に含まない。

## 維持するもの

13記事の説明・データ、既存の相対リンクと記事内目次、サイトマップのページ構成とlastmod、RSS停止workflow・空のnews.json・取得採点コード・再開用UIを維持する。RSSの自動取得・見出し再公開は再開しない。

最終ブラウザ検証も完了: 390px/1440pxで全17ページ、画像の読み込み、canonical値、13記事への導線、#newsの移動先を確認。JavaScriptエラー・HTTPエラーなし。RSS/ニュースJSONの自動取得なし。公開用成果物のnews.jsonは404。
