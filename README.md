# YouTube ドラフト → 限定公開 一括変換スクリプト

YouTube Studio のドラフト動画をすべて自動で「限定公開」に変更する Playwright スクリプト。

## 概要

YouTube Studio のコンテンツページを自動操作し、ステータスが「ドラフト」の動画を一括で「限定公開」に変更します。

## 動作環境

- macOS
- Python 3.9+
- Google Chrome（`/Applications/Google Chrome.app`）

## セットアップ（初回のみ）

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## 実行方法

```bash
python3 youtube_draft_to_unlisted.py
```

1. Chrome が自動で起動し、YouTube Studio ダッシュボードが開く
2. ログインが必要な場合は手動でログイン
3. 正しいアカウントであることを確認したらターミナルで **Enter**
4. ドラフト動画を自動検出して順に「限定公開」へ変更
5. すべて完了すると「🎉 完了！合計 〇 本を限定公開に変更しました。」と表示

## 仕様

### 認証
- `chrome_profile/` ディレクトリに Chrome セッションを保存
- **初回のみ**手動でログインが必要。2回目以降はログイン済み状態で起動

### 処理フロー

```
起動
 └─ YouTube Studio ダッシュボードへ移動
     └─ URL からチャンネルID を自動取得
         └─ /channel/{id}/videos へ移動
             └─ ytcp-video-row を全件取得
                 └─ 行テキストに「ドラフト」が含まれる行を検出
                     └─ 「ドラフトを編集」をクリック
                         └─ 公開設定タブへ移動
                             └─ 「限定公開」ラジオボタンを選択・保存
                                 └─ コンテンツ一覧に戻り繰り返し
```

### セレクター

| 対象 | セレクター |
|------|-----------|
| 動画行 | `ytcp-video-row` |
| ドラフト判定 | 行テキストに「ドラフト」が含まれるか |
| 編集ボタン | `text=ドラフトを編集` |
| 公開設定タブ | `button#step-badge-3, [data-tab-id='3']` |
| 限定公開ラジオ | `tp-yt-paper-radio-button[name='UNLISTED']` |
| 保存ボタン | `ytcp-button#save-button` |

### 注意事項

- YouTube Studio の画面構成が変更された場合、セレクターの修正が必要になる場合があります
- 実行中は Chrome を手動操作しないでください
- `chrome_profile/` はログイン情報を含むため `.gitignore` で除外しています

## ファイル構成

```
Youtube-Change-Status/
├── youtube_draft_to_unlisted.py   # メインスクリプト
├── chrome_profile/                # Chromeセッション保存（.gitignore対象）
├── README.md                      # 本ドキュメント
└── .gitignore
```
