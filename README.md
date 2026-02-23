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

## データ更新

`data/index.json` と `data/entries/*.json` を更新すると、表示内容が反映されます。

## GitHub Pages 有効化

1. Repo Settings → Pages
2. Source: **GitHub Actions** を選択
3. `pages.yml` が自動デプロイ
