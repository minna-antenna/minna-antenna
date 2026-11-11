# トピック基地 — 独自解説中心・RSS一時停止中

RSSの自動取得・見出し再表示・ニュースJSON公開は停止する構成です。取得・採点処理とテストは保持しています。停止の有効化、履歴上の見出しデータ、許諾確認後の再開手順は [RSS一時停止と残存データの扱い](docs/rss-pause.md) を参照してください。

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

## 公開とRSS停止

Pages SourceはGitHub Actionsを使用します。公開ワークフローは記事ビルド後に実行し、ニュースJSONを公開成果物へ含めません。RSS更新workflowにはscheduleを設定せず、手動実行のジョブも停止しています。過去のRSS開始手順を使って無断で再開しないでください。

AdSense・品質確認と残課題は `QUALITY_REVIEW.md` を参照してください。

## 本番前の追加検証
記事数が3本以上になると固定件数テストが失敗する不具合を修正しました。3〜5本の記事を持つ一時コピーで全テストと生成処理を確認しています。既存2記事の本文・相互リンクも保持されます。公開ワークフローはSourceがGitHub Actionsでない場合に公開前に停止します。

### RSS採点・編集方針

発行主体と取得フィードを分けた採点、提供元の利用条件の確認状況、広告掲載対象の考え方は [RSSニュースの採点・表示・広告掲載方針](docs/rss-editorial-review.md) を参照してください。実データの旧新比較は [検証結果](reports/rss-publishers-2026-11-10/validation.json) に記録しています。
