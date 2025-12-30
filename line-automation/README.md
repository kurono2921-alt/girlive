# LINE公式アカウント自動化システム

LINE公式アカウントの作成・設定作業を自動化するPythonデスクトップアプリケーション。

手作業で5〜10分かかる作業を、**1アカウントあたり約2〜3分**に短縮します。

## ✨ 主な機能

- **一括作成** - 複数のLINE公式アカウントをまとめて作成
- **自動設定** - Messaging API有効化、トークン発行、各種リンク取得
- **Google Sheets連携** - スプレッドシートでアカウント情報を管理・自動書き戻し
- **画像自動取得** - Dropbox共有リンクからアイコン画像をダウンロード
- **ボット検知回避** - Playwright Stealthによる人間らしい操作の再現

## 📋 動作環境

| 項目 | 要件 |
|------|------|
| Python | 3.10以上 |
| OS | macOS / Windows / Linux |
| ディスク | 約500MB |

### 必要なアカウント

- GCP アカウント（Sheets API用）
- LINE ビジネスアカウント

## 🚀 セットアップ

### 1. 仮想環境の作成

```bash
cd /path/to/LINE自動化

# 仮想環境を作成・有効化
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Google Sheets API の設定

1. [Google Cloud Console](https://console.cloud.google.com/) で新規プロジェクトを作成
2. 「APIとサービス」→「ライブラリ」で以下を有効化
   - Google Sheets API
   - Google Drive API
3. 「認証情報」→「サービスアカウント」を作成
4. 「キー」タブ → JSON形式でダウンロード
5. ダウンロードしたファイルを `config/google_credentials.json` として配置

```bash
mv ~/Downloads/your-project-xxxx.json config/google_credentials.json
```

### 4. スプレッドシートの共有設定

対象のGoogle Spreadsheetsを開き、サービスアカウントのメールアドレスを**編集者**として追加します。

```bash
# サービスアカウントのメールアドレス確認
cat config/google_credentials.json | grep client_email
```

### 5. 動作確認

```bash
python -c "import playwright; import PySide6; import gspread; print('✅ セットアップ完了')"
```

## 📱 使い方

### アプリの起動

```bash
source .venv/bin/activate  # 未起動の場合
python app.py
```

### 設定項目

#### ログイン情報

| 項目 | 説明 |
|------|------|
| メールアドレス | LINEビジネスアカウントのメール |
| パスワード | LINEビジネスアカウントのパスワード |

#### シート情報

| 項目 | 説明 |
|------|------|
| 連携先シートURL | Google SpreadsheetsのURL |
| 使用シート名 | プルダウンから選択 |

#### 列情報（A〜AZ列を指定）

| 項目 | 必須 | 説明 |
|------|:----:|------|
| 有効/無効の列 | ✅ | `TRUE`/`1`/`はい`で処理対象を判定 |
| 公式LINE名の列 | ✅ | 作成するアカウント名 |
| アイコン画像の列 | ✅ | Dropbox共有リンク |
| ベーシックIDの列 | | 書き戻し先 |
| アクセストークンの列 | | 書き戻し先 |
| 権限追加リンクの列 | | 書き戻し先 |
| 友達追加リンクの列 | | 書き戻し先 |

#### その他

| 項目 | 説明 |
|------|------|
| アイコン画像の保存先 | ローカルフォルダを選択 |
| ヘッドレスモード | ブラウザ非表示（初回はOFF推奨） |

### スプレッドシートの形式

- **1〜2行目**: ヘッダー（自動スキップ）
- **3行目以降**: データ行
- **有効判定**: `TRUE`, `1`, `はい`, `YES`, `有効`（大文字小文字不問）
- **上限**: 100件/回

## 🔄 処理フロー

```
Google Sheets読み込み
    ↓
Dropbox画像ダウンロード
    ↓
LINEアカウントマネージャーログイン
    ↓
アカウント作成 → アイコン設定 → Messaging API有効化
    ↓
権限追加リンク取得 → 友達追加リンク取得
    ↓
LINE Developers Consoleでトークン発行
    ↓
Google Sheetsへ書き戻し
```

## 🛡️ ボット検知回避技術

| 技術 | 説明 |
|------|------|
| Playwright Stealth | `navigator.webdriver`フラグの偽装 |
| ベジェ曲線マウス移動 | 人間の手の動きを数学的に再現 |
| ランダムディレイ | 操作間に500〜1500msの待機 |
| 1文字ずつタイピング | キーストローク間に20〜100msの遅延 |
| UA偽装 | 実際のChrome UAを使用 |
| 解像度ランダム化 | 一般的な解像度からランダム選択 |

## 🔐 セッション管理

- **Cookie永続化**: `config/session.json`に保存し、次回起動時に自動ログイン
- **CAPTCHA検知**: reCAPTCHA検出時にUIダイアログで通知
- **自動再認証**: セッション無効時に再ログインフローへ自動遷移

## 📂 プロジェクト構成

```
LINE自動化/
├── app.py                    # メインGUIアプリケーション
├── requirements.txt          # 依存パッケージ
├── config/
│   ├── settings.py           # 定数・設定値
│   ├── google_credentials.json  # Google API認証（手動配置）
│   ├── app_settings.json     # ユーザー設定（自動生成）
│   └── session.json          # Cookieセッション（自動生成）
└── core/
    ├── automation_runner.py  # 自動化オーケストレーション
    ├── line_automation.py    # LINE自動化ロジック
    ├── stealth_browser.py    # ステルスブラウザ
    ├── session_manager.py    # セッション管理
    ├── sheets_client.py      # Google Sheets連携
    ├── settings_manager.py   # 設定管理
    └── image_downloader.py   # 画像ダウンロード
```

## 🛠️ 技術スタック

| カテゴリ | ライブラリ | 用途 |
|---------|-----------|------|
| GUI | PySide6 | Qt6ベースのデスクトップUI |
| ブラウザ自動化 | Playwright | Chromiumベースの自動化 |
| ステルス | playwright-stealth | ボット検知回避 |
| Sheets連携 | gspread | Google Sheets API |
| 認証 | google-auth | OAuth 2.0認証 |
| HTTP | requests | 画像ダウンロード |

## 📄 ライセンス

Copyright (c) 2025 ガルリべ. All rights reserved.

**Private - 社内利用限定**