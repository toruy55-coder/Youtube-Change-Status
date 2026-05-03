# YouTube ドラフト → 非公開＋指定アカウント共有 一括変換スクリプト

YouTube Studio のドラフト動画を自動操作し、公開状況を「非公開」にしたうえで、指定した Google アカウントだけに共有する Playwright スクリプト。

## 動作環境

- macOS
- Python 3.9+
- Google Chrome（`/Applications/Google Chrome.app`）
- Playwright

## セットアップ（初回のみ）

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## 実行方法

全ドラフトを処理:

```bash
python3 youtube_draft_to_unlisted.py
```

1本だけ処理するテストモード:

```bash
python3 youtube_draft_to_unlisted.py --test
```

または:

```bash
python3 youtube_draft_to_unlisted.py --limit 1
```

確認待ちを省略:

```bash
python3 youtube_draft_to_unlisted.py --skip-confirm
```

## 共有先 Google アカウント

非公開動画は以下の5アカウントに共有します。

- `toruy56@gmail.com`
- `mei1218y@gmail.com`
- `m.reveson.mi@gmail.com`
- `rihoho1020@gmail.com`
- `memory.yoshie55@gmail.com`

## 仕様

### 認証

- `chrome_profile/` ディレクトリに Chrome セッションを保存
- 初回のみ手動ログインが必要
- 2回目以降はログイン済み状態で起動
- 実行前に YouTube Studio のアカウント確認用 Enter 待ちを行う

### 処理フロー

```text
起動
 └─ YouTube Studio ダッシュボードへ移動
     └─ 正しいアカウントであることをユーザーが確認してEnter
         └─ URL からチャンネルIDを自動取得
             └─ /channel/{id}/videos へ移動
                 └─ ytcp-video-row を取得
                     └─ 行テキストに「ドラフト」が含まれる行を検出
                         └─ 「ドラフトを編集」をクリック
                             └─ 公開設定タブへ移動
                                 └─ 「非公開」を選択
                                     └─ 「非公開で共有」ダイアログを開く
                                         └─ 指定5メールアドレスを追加
                                             └─ 保存
                                                 └─ 一覧に戻って「非公開」反映を確認
                                                     └─ 次のドラフトへ
```

### 保存確認

保存後は以下を確認します。

- 保存完了メッセージ（例: `保存しました`）の表示
- コンテンツ一覧に戻った後、対象動画の行に `非公開` が含まれ、`ドラフト` が残っていないこと

一覧で確認できない場合は失敗として停止し、ターミナルに理由を表示します。

### テストモード

`--test` は `--limit 1` と同じです。YouTube Studio の画面構成は変わることがあるため、セレクター修正後はまず1本だけ処理して確認してください。

## セレクター方針

YouTube Studio の DOM は変更されやすいため、1つの固定セレクターではなく、候補を順に試します。

| 対象 | 主な候補 |
|------|----------|
| 動画行 | `ytcp-video-row` |
| ドラフト判定 | 行テキストに `ドラフト` が含まれるか |
| 編集ボタン | `text=ドラフトを編集`, `a[href*='video_id']` |
| 公開設定 | `button#step-badge-3`, `[data-tab-id='3']`, `text=公開設定` |
| 非公開ラジオ | `tp-yt-paper-radio-button[name='PRIVATE']`, `text=非公開` |
| 非公開共有 | `text=動画を非公開で共有`, `text=非公開で共有` |
| 保存 | `ytcp-button#save-button`, `text=保存` |

## 注意事項

- 実行中は Chrome を手動操作しないでください
- `chrome_profile/` はログイン情報を含むため `.gitignore` で除外しています
- 非公開共有ダイアログの構造が変わった場合、メール入力欄や保存ボタンのセレクター修正が必要です

## ファイル構成

```text
Youtube-Change-Status/
├── youtube_draft_to_unlisted.py   # メインスクリプト
├── chrome_profile/                # Chromeセッション保存（.gitignore対象）
├── README.md                      # 仕様書
└── .gitignore
```
