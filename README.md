# みんなのアンテナ — RSS自動更新版

## 何を実装したか
- 公開RSS（NHK、BBC日本語、Googleニュースのジャンル別検索）から**見出し、出典、公開時刻、URL**を取得します。本文・画像の転載はしません。
- 72時間以内の候補をスコア順表示し、各ニュースに「根拠」ボタンを付けています。
- 取得元・取得エラー・採点内訳を表示します。「急上昇」「SNS話題度」などの実測を装いません。
- 同じ見出しの異なる媒体は媒体数として加点します。これは厳密な同一事件判定ではありません。
- GitHub Actionsによる**3時間ごとの自動更新**を設定しています。GitHubのスケジュール実行には遅延・スキップの可能性があります。

## GitHubで自動運転開始
1. このフォルダの全ファイル（隠しフォルダ `.github` を含む）を新しいGitHubリポジトリのルートにアップロード。
2. Settings > Actions > General で workflow permissions に **Read and write permissions** を設定（リポジトリ設定によっては制限されます）。
3. Actions > **Update news RSS** > Run workflow を押して最初の取得を実行。
4. `data/news.json` の `generated_at` が入ったことを確認。
5. この更新版では Settings > Pages > Source を **GitHub Actions** にします。既存のブランチ公開からの移行順序は **DEPLOYMENT.md** を確認してください。
6. 以後、3時間ごとのワークフローが `data/news.json` を更新。訪問者はページ表示時と更新ボタンで新しいJSONを取得。

注: サイトは**GitHub PagesなどHTTPサーバー経由で閲覧**してください。`index.html` をローカルでダブルクリックすると `fetch('./data/news.json')` が失敗するブラウザがあります。

## ローカルで試す
```bash
python scripts/update_news.py
python -m http.server 8000
```
その後 http://localhost:8000 を開く。ネット接続なしではRSS収集できません。

## 掲載スコアの意味
- 新しさ: 公開から0〜72時間で 60点 → 0点に線形減衰
- 同一の正規化見出しを持つ異なる媒体: 追加1社につき15点、最大30点
- NHK/BBC RSSの掲載: 10点
- ジャンルごと最大10本、全体最大60本。重複はタイトル正規化で判定。各取得元に偏りがあり、一般的な「世間の注目度」を定量化したものではありません。
- `data/news.json` に毎回の成功・失敗した取得元と日時を保存します。

## 注意
- Googleニュースの検索RSSなどの提供条件・取得可能性は変動します。RSS配信元の利用条件を確認してください。
- 自動更新を開始するには公開先の設定と最初のワークフロー実行が必要です。ZIPをダウンロードしただけでは3時間ごとに動きません。
- 既存の掲示板スレッドはサンプルのままです。コメントは訪問者間では共有されません。
- GitHub Actionsの実行枠やPagesの利用条件は各契約で確認してください。

## 独自記事の自動登録（追加実装）
`articles/` 内にHTMLを追加してmainへ反映すると、**Build article index and sitemap** が記事一覧と `sitemap.xml` を生成・コミットします。サブフォルダーにも対応します。HTMLには次を記載してください。

```html
<h1>記事のタイトル</h1>
<meta name="description" content="記事の内容を説明する固有の要約">
<meta property="article:published_time" content="2026-11-06">
<meta property="article:modified_time" content="2026-11-06">
```

既存記事のArticle構造化データや「公開：2026年11月4日」表記も読み取ります。公開日・更新日が不正な記事はエラーにして生成物を維持します。更新日を省略した場合はGitの最終コミット日を利用します。本文・参考資料・ナビゲーションは各HTMLで用意してください。生成マーカー `ARTICLES:START/END` の内側は自動生成のため直接編集しません。

```bash
python -m unittest discover -s tests -v
python scripts/build_site.py
python -m http.server 8000
```

## 公開設定（初回のみ）
既存サイトの正確な移行順序と復旧手順は **DEPLOYMENT.md** を参照してください。公開元の切り替えはmainへのマージ前に行います。
1. 修正一式を既存リポジトリに反映します。既存ファイルへの上書きと新規ファイルの追加で、記事や `data/news.json` を削除する必要はありません。
2. Settings → Actions → General で、ワークフローによるリポジトリ書き込みを許可します。
3. Settings → Pages → Build and deployment → Source を **GitHub Actions** に変更します。
4. Actions → **Build article index and sitemap** → Run workflow を実行します。続いて **Deploy GitHub Pages** が実行されることを確認します。
5. **Update news RSS** を手動実行し、成功後に公開ページの更新時刻を確認します。以後のcronは従来どおりUTCの3時間ごと7分（JST 0:07、3:07、6:07、9:07、12:07、15:07、18:07、21:07の予定。遅延あり）です。

今回確認したリモートでは、既存のRSS更新後にGitHub標準の `pages build and deployment` が成功しています。新構成では記事ビルドとRSS更新の成功後に専用の公開ワークフローを使います。既存方式との重複公開を避けるため、本番導入時はPages Sourceを **GitHub Actions** へ切り替えてから専用ワークフローを使用してください。公開用成果物には現行ページ・記事・ニュースJSON・サイトマップ・Google確認ファイルのみを含め、古いトップページの複製や配布ZIPは公開しません。元のリポジトリ内のファイルは保持します。

記事とRSSの書き込みワークフローは同じconcurrencyグループで実行を直列化します。PRの検証はPRごとの別グループで実行し、RSS更新の待機枠と分離します。RSSの書き込みはmainだけで実行し、公開は同一リポジトリのmainの正常終了したpush・schedule・手動実行に限定します（PR完了では公開しません）。手動のコミットと競合したpushは失敗として表示されます。その場合は最新mainでワークフローを再実行してください。

## RSS障害時の挙動
- 全取得失敗または有効な記事0件：前回の記事と成功日時を保持し、失敗情報を保存してActionsを失敗にします。
- 一部取得失敗：成功したフィードを更新し、失敗したフィードの記事は保持します。古い記事を含む可能性は選定ルールにも記載しています。
- JSON書き込みは一時ファイルを置換する方式です。取得・書き込み途中のJSON公開を避けます。
- ブラウザで再読み込みに失敗した場合、表示済みニュースは保持します。

AdSense・品質確認と残課題は `QUALITY_REVIEW.md` を参照してください。

## 本番前の追加検証
記事数が3本以上になると固定件数テストが失敗する不具合を修正しました。3〜5本の記事を持つ一時コピーで全テストと生成処理を確認しています。既存2記事の本文・相互リンクも保持されます。公開ワークフローはSourceがGitHub Actionsでない場合に公開前に停止します。

### RSS採点・編集方針

発行主体と取得フィードを分けた採点、提供元の利用条件の確認状況、広告掲載対象の考え方は [RSSニュースの採点・表示・広告掲載方針](docs/rss-editorial-review.md) を参照してください。実データの旧新比較は [検証結果](reports/rss-publishers-2026-11-10/validation.json) に記録しています。
