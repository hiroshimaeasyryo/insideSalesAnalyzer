# 🚀 本番環境でのGoogle Drive連携設定

機微データを安全に管理しながら、本番環境でGoogle Driveからデータを読み込む設定方法を説明します。

## 🔐 セキュリティ重要事項

### ✅ 保護されるもの
- **機微データ**: `dataset/`フォルダ内のJSONファイルはリポジトリに含まれません
- **認証情報**: サービスアカウントJSONファイルはGitに含まれません
- **アクセス制御**: 読み取り専用権限でのGoogle Drive接続

### ❌ リポジトリに含まれないもの
- `service_account.json`
- `dataset/*.json`（データファイル）
- `.env`（ローカル開発用設定）

## 🌐 プラットフォーム別設定方法

### 1. Streamlit Cloud

#### Step 1: Secrets設定
プロジェクト設定 > Secrets に以下を追加：

```toml
# Streamlit Secrets
[google_drive]
enabled = true
folder_id = "your-google-drive-folder-id"
production_mode = true
use_local_fallback = false

# サービスアカウント認証情報（JSONを文字列として）
service_account = '''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40project.iam.gserviceaccount.com"
}
'''
```

#### Step 2: 設定読み込みコード追加
`config.py`を以下のように更新：

```python
import streamlit as st

# Streamlit Cloud用の設定読み込み
if 'google_drive' in st.secrets:
    GOOGLE_DRIVE_ENABLED = st.secrets.google_drive.get("enabled", False)
    GOOGLE_DRIVE_FOLDER_ID = st.secrets.google_drive.get("folder_id", "")
    PRODUCTION_MODE = st.secrets.google_drive.get("production_mode", False)
    USE_LOCAL_FALLBACK = st.secrets.google_drive.get("use_local_fallback", True)
    
    # サービスアカウント情報を環境変数に設定
    import os
    if "service_account" in st.secrets.google_drive:
        os.environ["GOOGLE_SERVICE_ACCOUNT"] = st.secrets.google_drive.service_account
```

### 2. Heroku

#### Step 1: 環境変数設定
```bash
# Heroku CLI使用
heroku config:set GOOGLE_DRIVE_ENABLED=true
heroku config:set GOOGLE_DRIVE_FOLDER_ID=your-folder-id
heroku config:set PRODUCTION_MODE=true
heroku config:set USE_LOCAL_FALLBACK=false
heroku config:set GOOGLE_SERVICE_ACCOUNT='{"type": "service_account", ...}'
```

#### Step 2: または管理画面で設定
1. Heroku Dashboard > Settings > Config Vars
2. 上記の環境変数を追加

### 3. Vercel

#### Step 1: 環境変数設定
```bash
# Vercel CLI使用
vercel env add GOOGLE_DRIVE_ENABLED
# → true を入力

vercel env add GOOGLE_DRIVE_FOLDER_ID
# → フォルダIDを入力

vercel env add PRODUCTION_MODE
# → true を入力

vercel env add USE_LOCAL_FALLBACK
# → false を入力

vercel env add GOOGLE_SERVICE_ACCOUNT
# → サービスアカウントJSONを入力
```

### 4. AWS/GCP/Azure

#### 環境変数として設定
```bash
export GOOGLE_DRIVE_ENABLED=true
export GOOGLE_DRIVE_FOLDER_ID=your-folder-id
export PRODUCTION_MODE=true
export USE_LOCAL_FALLBACK=false
export GOOGLE_SERVICE_ACCOUNT='{"type": "service_account", ...}'
```

## ⚙️ 設定モードの説明

### 🔧 開発モード（デフォルト）
```bash
PRODUCTION_MODE=false
USE_LOCAL_FALLBACK=true
```
- Google Drive失敗時にローカルファイルを使用
- 開発・テスト環境向け

### 🚀 本番モード（推奨）
```bash
PRODUCTION_MODE=true
USE_LOCAL_FALLBACK=false
```
- Google Driveからのみデータを読み込み
- 機微データの漏洩を防止
- エラー時は明確なエラーメッセージを表示

### 🔒 厳格モード
```bash
PRODUCTION_MODE=true
USE_LOCAL_FALLBACK=false
GOOGLE_DRIVE_ENABLED=true
```
- 最も安全な設定
- Google Drive接続失敗時はアプリケーション停止

## 🧪 本番環境での動作確認

### 1. デバッグスクリプト実行
```bash
# 本番環境で実行
python debug_env.py
```

### 2. 期待される出力
```
🔍 環境設定デバッグ
==================================================
📋 Google Drive関連の環境変数:
  GOOGLE_DRIVE_ENABLED: true
  GOOGLE_DRIVE_FOLDER_ID: 1l0MK5vW...
  GOOGLE_SERVICE_ACCOUNT: 設定済み (1234 文字)
  PRODUCTION_MODE: true
  USE_LOCAL_FALLBACK: false

🌐 Google Drive接続テスト:
  設定読み込み: ✅ 成功
  Drive有効: True
  フォルダID: 設定済み
  接続テスト: ✅ 成功
```

### 3. アプリケーション起動
```bash
streamlit run streamlit_app.py
```

サイドバーで以下を確認：
- 🌐 **Google Driveから読み込み中**
- ✅ **Google Drive: 利用可能**

## 🚨 トラブルシューティング

### エラー: "本番環境モードでGoogle Drive接続に失敗"

**原因:**
- サービスアカウント認証情報の不備
- ネットワーク接続の問題
- 権限設定の問題

**解決策:**
1. サービスアカウントJSONの形式確認
2. Google Driveフォルダがサービスアカウントと共有されているか確認
3. Google Drive APIが有効化されているか確認

### エラー: "Google Drive読み込みに失敗し、ローカルフォールバックが無効化"

**原因:**
- `USE_LOCAL_FALLBACK=false`でGoogle Drive接続失敗

**解決策:**
1. Google Drive設定を修正
2. または一時的に`USE_LOCAL_FALLBACK=true`に設定

### エラー: "モジュールインポート失敗"

**原因:**
- 必要なライブラリがインストールされていない

**解決策:**
```bash
pip install -r requirements.txt
```

## 📊 セキュリティベストプラクティス

### 1. 最小権限の原則
- サービスアカウントには読み取り権限のみ付与
- 特定のフォルダのみアクセス可能に制限

### 2. 認証情報の管理
- 本番環境では環境変数を使用
- JSONファイルはローカル開発のみ
- 定期的なキーローテーション

### 3. アクセスログの監視
- Google Cloud Consoleでアクセスログを確認
- 異常なアクセスパターンをモニタリング

### 4. 暗号化
- Google Drive上でのファイル暗号化（必要に応じて）
- 転送時の暗号化（HTTPS）

## 🔄 継続的なメンテナンス

### 1. 定期確認事項
- [ ] サービスアカウントキーの有効期限
- [ ] Google Drive APIの利用状況
- [ ] アクセス権限の見直し

### 2. 更新時の注意点
- データ構造変更時は互換性を確認
- 新しいファイル追加時はGoogle Drive上にアップロード
- 権限設定の再確認

### 3. バックアップ戦略
- Google Drive上での複数フォルダでのバックアップ
- 定期的なデータエクスポート 