# Googleインデックス毎日監視：設定・使い方

対象: https://minna-antenna.github.io/minna-antenna/ 。仕様調査: 2026-11-07。

## 現在できること／まだできないこと

実装・オフラインテスト・公開sitemap実取得は認証なしで検証できる。Googleのインデックス状況とGoogle側sitemap取得履歴は、下記のユーザー設定後に初めて実確認できる。未設定で接続成功とは報告しない。

毎日 **日本時間08:17（UTC前日23:17）ごろ**、mainの `Monitor Google indexing` が動く。GitHub都合で遅延・取りこぼしの可能性があり、厳密な定時保証ではない。公開リポジトリは60日間活動がないと定期実行が無効になることもある。Actions一覧で最終実行を確認する。

公開sitemap.xmlの `articles/` 配下HTMLを重複排除して取得するため、新記事の自動生成sitemapに反映されれば監視にも自動追加される。現行のurlset形式を対象とし、将来sitemapindexへ変わった場合は明示エラーになる（黙って対象を減らさない）。

APIはGoogleが保持する情報の照会のみ。ライブ検査・インデックス登録申請・Google Indexing API呼び出しは行わない。登録や検索順位は保証しない。

## 1. Search Consoleの所有権・権限を確認（ユーザー操作）

1. https://search.google.com/search-console を開き、監視に使うGoogleアカウントでログイン。
2. 左上のプロパティ選択から `https://minna-antenna.github.io/minna-antenna/` を選ぶ。なければ「プロパティを追加」→「URLプレフィックス」へこのURLを入力し、画面に従って所有権を確認する。既存の検証ファイル・Pages設定は削除しない。
3. 「設定」→「ユーザーと権限」で自分が所有者またはフルユーザーであることを確認。別アカウントなら所有者に必要な権限付与を依頼する。Codexは権限追加を行わない。
4. 左の「サイトマップ」で `sitemap.xml` の送信・取得状況を確認。未送信なら、ユーザーが必要性を確認した上で送信する。本システムは送信しない。公開HTTP取得の成功とGoogleによる取得成功は別々に記録する。

URLプレフィックスの末尾 `/`、https、パスを一致させる。別の既存プロパティを使う場合は後述の `GSC_SITE_URL` を設定する。

## 2. Google CloudでAPIとOAuthクライアントを準備（ユーザー操作）

1. https://console.cloud.google.com/ を開く。上部プロジェクト選択→「新しいプロジェクト」で専用プロジェクトを作るか、管理権限のある既存プロジェクトを選ぶ。
2. 左メニュー「APIとサービス」→「ライブラリ」で **Google Search Console API** を検索→「有効にする」。Google Indexing APIではない。API利用制限画面も確認する。
3. 「Google Auth Platform」（画面によって「OAuth同意画面」）→「ブランディング」でアプリ名・サポートメール・連絡先を自分の管理する情報で設定。
4. 「対象」（Audience）でアカウント種別に適した内部／外部を設定。外部のテスト段階では監視アカウントをテストユーザーに追加する。
5. 「データアクセス」（旧「スコープ」）で次だけを追加:
   `https://www.googleapis.com/auth/webmasters.readonly`
   書込可能なwebmastersスコープ、Drive等の権限は追加しない。
6. 毎日継続する場合は、外部アプリの公開ステータスを「本番環境」（In production）にする必要性を確認する。**Testingで発行したrefresh tokenは、このスコープでは通常7日で失効する**。本番への切替後は必要に応じ再同意・再発行する。Googleが確認・審査を求めた場合は公式手続きに従う。本番にすることはGoogleによる検証済みを意味せず、無期限稼働も保証しない。ポリシーや組織制限を回避しない。
7. 「クライアント」→「クライアントを作成」→種類「ウェブアプリケーション」。名前を入力し、承認済みリダイレクトURIに以下を追加して保存:
   `https://developers.google.com/oauthplayground`
8. クライアントIDとクライアントシークレットは自分の端末上で安全に扱う。チャット・Issue・PR・スクリーンショット・Gitに貼らない。APIキーだけでは認証できない。Cloudプロジェクトの編集権限とSearch Consoleプロパティ権限は別物。

## 3. 公式OAuth Playgroundで一度だけ同意してrefresh tokenを取得

1. https://developers.google.com/oauthplayground/ を開く。
2. 右上の歯車を開き、**Use your own OAuth credentials** をオンにして、自分のクライアントID・シークレットを入力。Playground共用クライアントのまま取得しない（トークンが短期間で失効する）。
3. OAuth flowがServer-side、Access typeがOffline、承認プロンプトがConsentであることを確認。表示名は更新される場合がある。
4. Step 1のスコープ入力欄へ上記readonlyスコープだけを入力し「Authorize APIs」。Search Console権限があるGoogleアカウントを選び、要求スコープと自分のアプリを確認して同意する。想定外のアプリ・権限・警告なら中止して設定を見直す。
5. Step 2で「Exchange authorization code for tokens」。表示された **Refresh token** をGitHub Secret用に保管する。Access tokenは短期なのでSecretへ保存しない。
6. refresh tokenが出ない場合、offline/consentと自分のクライアント設定を確認。再認可が必要になる場合がある。発行を何度も繰り返すと古いトークンが失効することがある。
7. 設定後はPlaygroundの自動更新を止め、共有端末・録画等へ認証情報が残らないようにする。JSONダウンロードやリポジトリへの保存は不要。

パスワード変更・アカウントからの取消・組織ポリシー・トークン期限等で認証が失効する場合は再設定する。失効時は監視が赤い失敗となり「確認不能」を保存する。

## 4. GitHub Secretsへ登録（ユーザー操作）

1. https://github.com/minna-antenna/minna-antenna/settings/secrets/actions を開く。
2. 「New repository secret」を押し、次の3件をそれぞれ別々に追加。名前は正確に、Valueには自分が取得した値のみを貼る。

| Secret名 | Value |
|---|---|
| `GSC_CLIENT_ID` | OAuthクライアントID |
| `GSC_CLIENT_SECRET` | 同じクライアントのシークレット |
| `GSC_REFRESH_TOKEN` | 同じクライアント・監視ユーザー・readonly同意で発行したrefresh token |

3. 通常 `GSC_SITE_URL` は未設定でよい。プロパティがホスト全体のURLプレフィックスやDomainの場合のみ、同画面「Variables」→「New repository variable」で設定。対応値は `https://minna-antenna.github.io/` または `sc-domain:minna-antenna.github.io`。それらの所有権を実際に持つ場合に限る。Cloud側の設定やGitHub変数だけで所有権は付与されない。
4. Secretsの値をログへ表示して検証しない。不明なPR・forkのコードへSecretsを渡さない。このワークフローはPRイベントでは動かずmainのみ、contents:read、checkout認証保持なし。

## 5. 初回実行と毎日の見方

1. GitHubリポジトリの「Actions」→ **Monitor Google indexing** を選ぶ。
2. 「Run workflow」→ Branch **main** →「Run workflow」。これは監視の実行であり、登録申請・Pages公開ではない。
3. 実行を開き **Summary** を見る。登録済み／未登録／取得エラー／確認不能の件数、Googleの理由、最終クロール（UTC/ISO8601）、canonical、Google側sitemap最終ダウンロード等が確認できる。
4. ページ下部「Artifacts」から `google-index-status-実行ID-試行番号` をダウンロード。
   - `index-status.json`: 実行・公開HTTP取得・Google側sitemap情報と全記事の詳細。
   - `index-status.csv`: 記事ごとの結果。Excel向けUTF-8 BOM、セル式注入防止。
   - `summary.md`: 実行Summaryと同じ一覧・未登録記事の手動検査候補。
5. 未登録一覧の記事URLをコピーし、表示されたSearch Consoleリンクを開いて上部の「URL検査」に貼る。理由と実ページを確認し、必要なら「インデックス登録をリクエスト」を**手動**実施。UIに出ない操作や権限不足ならGoogleの案内に従う。申請にも回数制限があり、再申請の連打はしない。
6. 一度設定した後は毎日自動実行。認証の更新・失効時だけユーザーの再操作が必要。GitHubの通知設定でActions失敗通知を受け取れるが、本実装はメール等を勝手に送信しない。

Artifactsは90日保持。以後も必要なら期限前にダウンロードする。Git履歴へ追記しないので、RSSのpushやPages公開と競合しない。公開リポジトリのActions Summary/成果物はGitHubアクセス権・公開範囲に従って閲覧される。公開URLとGoogleの診断だけを含み、認証情報・他プロパティは出力しない。Search Console診断の公開を避けたい場合は、ユーザー判断で監視用の非公開リポジトリを用意してから使う。

## 分類・失敗の意味

| status | 表示 | 判定 |
|---|---|---|
| indexed | 登録済み | indexStatusResult.verdict = PASS |
| not_indexed | 未登録 | FAIL / NEUTRAL（Googleの未登録・除外。coverageStateを理由として保存） |
| fetch_error | 取得エラー | APIのネットワーク・HTTP・応答形式の取得失敗 |
| unverifiable | 確認不能 | 認証未設定/失効、権限不足、quota、結果欠落、未定義verdict、検査停止分等 |

`lastCrawlTime` がGoogle応答にないときは空欄。推測で補完しない。`pageFetchState` のNOT_FOUND等はGoogleが記録したクロール診断であり、本スクリプトの通信障害とは別。登録済みでもGoogle canonicalが自分のURLと違う場合は表の情報を確認する。Googleの情報はリアルタイムとは限らない。

未登録という正当な監視結果だけならジョブは成功し、一覧に明示される。**認証・通信・不明状態・Google側sitemapのpending/errorがあれば終了コード2でジョブ失敗**、ただし既に取得した結果・CSV・Summaryは保存する。Google側sitemap 404は未送信やプロパティ不一致の可能性があり、公開ファイル404と混同しない。例外の生レスポンスやOAuthトークンをログに出さないため、認証失敗の詳細はGoogle側の設定画面で確認する。

## 利用制限と安全設計

公式URL Inspection quotaは1サイトあたり2,000件/日、600件/分（調査時点）。本監視は直列、URL間0.25秒待機、最大200記事/回。HTTP429/5xxは最大3試行、Retry-After秒を尊重し長すぎる場合は停止。401/403/429が続いた時は残りを確認不能として停止し、他のGoogle利用へ負荷をかけない。200件超過時は黙って一部だけ検査せず、全件確認不能・失敗として知らせる。今後規模拡大時は同じプロパティの他ツール・手動実行分も含めてquotaを設計し直す。現行13記事なら最大試行を含めても十分小さい。

日次ワークフローはschedule/workflow_dispatchのみ。既存RSSの3時間cron、既存Pages・記事生成ワークフローは変更しない。新ワークフロー名はPagesのworkflow_run対象外で、監視が失敗してもRSSやPagesのトリガーには影響しない。追加PRのmain反映時は既存site.ymlのscripts/testsパス条件により通常ビルド・Pagesが一度走るが、サイト生成物は変わらない。

ローカルで認証なし確認:

```sh
python -m unittest discover -s tests -v
python scripts/monitor_indexing.py --output /tmp/index-monitor-check
```

後者は公開sitemapのみ実取得し、認証なしなら全記事「確認不能」、終了コード2となる。それが正しい未設定時の動作。Google成功を装うダミーデータは実運用で使わない。認証情報をシェルの引数・履歴・コミットへ書かない。

## 公式資料

- OAuth認可: https://developers.google.com/webmaster-tools/v1/how-tos/authorizing
- URL Inspection API: https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- 結果とverdict: https://developers.google.com/webmaster-tools/v1/urlInspection.index/UrlInspectionResult
- Google側sitemap照会: https://developers.google.com/webmaster-tools/v1/sitemaps/get
- API制限: https://developers.google.com/webmaster-tools/limits
- OAuth offline/refresh: https://developers.google.com/identity/protocols/oauth2/web-server
- token失効・Testing期限: https://developers.google.com/identity/protocols/oauth2#expiration
- 手動再クロール申請: https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl
- GitHub定期実行の制約: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
