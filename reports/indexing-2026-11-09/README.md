# 独自記事13本の初回診断

実測: 2026-11-09 21:51 JST（12:51 UTC）。対象ソース: f30422520796111754e65385b4f0895721e31116。

| 分類 | 記事数 |
|---|---:|
| 登録済み | 0 |
| 未登録 | 0 |
| 取得不可 | 0 |
| 要確認 | 13 |

Search Console認証がこの実行環境に設定されていないため、Googleでの登録有無は未確認。未登録0件は、未登録が存在しないという意味ではない。

## 実測結果

- `articles/*.html` は13本。対象URLは [urls.txt](urls.txt)。
- 公開13記事はすべてHTTP 200、リダイレクトなし、自己参照canonicalが1件。
- 全記事でtitle/descriptionが存在し、対象記事間の重複なし。
- robots metaはindex,follow。X-Robots-Tagのnoindexは検出なし。
- 各記事に7〜14ページから内部被リンクあり（記事13本とルートHTMLの公開版を対象）。記事内の同一ホストリンク先もすべてHTTP 200。
- 公開/ローカルsitemap.xmlは正しいsitemap名前空間のurlset。全17URL、対象13記事をすべて掲載、重複なし。
- origin直下robots.txtは404。Googleの取扱いに基づきクロール許可として扱う。プロジェクト配下のrobots.txtはHTTP 200だが、Googleのrobots制御としては効力を持たない。

## 修正案と実施範囲

記事やsitemapに技術的な修正を要する問題は今回検出されなかった。未登録の原因や改善効果は認証なしに特定できないため、本文・公開URL・canonicalを根拠なく変更しない。

既存診断はサイトマップを起点としていたため、サイトマップ掲載漏れを対象から落とす問題があった。新しい診断はリポジトリの記事を起点にし、HTTP・メタ情報・内部リンク・robots・XML/掲載確認を行い、CSV/HTML/JSON/URL一覧を保存する。既存readonly OAuth処理を再利用し、認証が設定されればURL Inspectionで全対象を照会する。日次監視workflowの実行コマンドのみ新診断へ切替。RSS・Pages設定・記事本文・公開サイトは変更していない。main未反映。

既存のGoogle側sitemap受理状況照会は `scripts/monitor_indexing.py` に残る。新しい一括診断は公開/ローカルXML検証を行うが、Google側sitemap受理状況は照会しない。

## 検証

- 既存125テスト通過。
- 追加5テストを含む130テスト通過（サイトマップ掲載漏れでも記事を診断、robots 404、API 403、内部リンク404、XML拒否、レポート出力・HTMLエスケープ）。
- 実サイトへの読取診断で全13件の結果を出力。
- Chromium/PlaywrightでHTMLレポートの表示と13件の行を確認。
- 認証未設定につき診断終了コード2。想定した動作であり、Google登録成功を示さない。
- API認証成功経路は既存モックテストで検証済み。実アカウントでのAPI照会は未実施。

## 次に必要な確認

[認証手順](../../docs/search-console-monitor.md) に沿ってreadonly OAuth資格情報をGitHub Actions Secretsへ設定する。リポジトリのコード・ファイルには保存しない。手動の場合は [Search Console](https://search.google.com/search-console?resource_id=https%3A%2F%2Fminna-antenna.github.io%2Fminna-antenna%2F) を開き、urls.txtの各URLを上部のURL検査欄へ貼り付ける。

Googleの照会結果に未登録があれば、coverageState・Google canonical・最終クロール等と技術診断を突き合わせて原因を調べる。必要に応じて所有者が手動で再クロールを依頼する。自動登録・通常記事へのIndexing API利用は行わず、登録・順位も保証しない。

CSVはUTF-8 BOM。HTMLはダウンロードしてブラウザで開く。全検査値は各行の「検査値を見る」を展開するかCSV/JSONで確認できる。

## 記事番号付き・ワンクリックコピー用HTML

[manual-inspection-urls.html](manual-inspection-urls.html) をGitHubの「Download raw file」からダウンロードし、ブラウザで開くと、第1〜13号の番号・タイトル・URLを一覧できます。各行の「URLをコピー」を押し、Search Console上部のURL検査欄へ貼り付けてください。GitHubのソース表示画面ではコピー用ボタンは動きません。

タイトルは各記事のtitle要素からサイト名を除いたものです。記事番号は既存の号数に対応します。各URLは既存のurls.txtと照合済みです。

ブラウザのClipboard APIが制限される場合は従来のコピー処理へ切り替えます。両方が使えない場合はURLを選択し、Ctrl+C（Macは⌘C）によるコピーを案内します。コピーできた場合だけ成功を表示します。このファイルはURLをコピーするだけで、Googleへの登録申請やAPI呼び出しは行いません。

追加HTMLの検証: Chromium/Playwrightで13件の番号・タイトル・URLを照合し、各ボタンを1回クリックして実際のクリップボード内容が該当URLになることを全13件で確認。Clipboard API未提供時/拒否時の代替コピー、両方式失敗時のURL選択・手動案内、JavaScript無効時のURL表示、390px幅で横はみ出しがないことも確認しました。ページからの外部通信・JavaScriptエラーは検出されませんでした。
