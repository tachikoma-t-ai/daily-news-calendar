# Daily News Calendar

毎日のニュース要約をカレンダー形式で見返せる静的サイトです。

## 特徴

- GitHub Pagesで公開できる静的サイト
- 日付ごとにニュース要約エントリを表示
- GitHub Actionsで毎日自動更新（1日1エントリ追加）

## 構成

- `index.html` / `styles.css` / `app.js`: フロントエンド
- `data/index.json`: 日付→エントリファイルの索引
- `data/entries/YYYY-MM-DD.json`: 日次エントリ
- `scripts/add_daily_entry.py`: RSSから当日のニュース記事エントリを生成

## ローカル確認

```bash
python3 scripts/add_daily_entry.py
python3 -m http.server 8080
# http://localhost:8080 を開く
```

## GitHub Pages 有効化

1. Repo Settings → Pages
2. Source: **GitHub Actions** を選択
3. `pages.yml` が自動デプロイ

## 毎日更新

- `.github/workflows/daily-update.yml` が毎日 00:30 JST に実行
- 新規エントリがあれば自動コミット＆push

## 注意

- ニュースはRSSベースで当日公開記事を優先して収集します。
