# Daily News Calendar

毎日のニュース要約をカレンダー形式で見返せる静的サイトです。

## 特徴

- GitHub Pagesで公開できる静的サイト
- 日付ごとにニュース要約エントリを表示
- 公開リポジトリには表示に必要な静的アセットとJSONデータのみ配置

## 構成

- `index.html` / `styles.css` / `app.js`: フロントエンド
- `data/index.json`: 日付→エントリファイルの索引
- `data/entries/YYYY-MM-DD.json`: 日次エントリ

## データ生成パイプライン

ニュース収集・生成ロジックは private repository で管理しています。

- Private: `tachikoma-t-ai/daily-news-calendar-generator`
- Public (このrepo): `tachikoma-t-ai/daily-news-calendar`

private repo の GitHub Actions が日次でJSONを生成し、このpublic repoへ `data/*` を同期します。

## GitHub Pages 有効化

1. Repo Settings → Pages
2. Source: **GitHub Actions** を選択
3. `pages.yml` が自動デプロイ
