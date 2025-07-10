# GitHub Secrets設定確認手順

## 🔐 現在のSecrets設定状況

エラーログから以下の問題が判明：
```
GOOGLE_DRIVE_FOLDER_ID: （空）
```

## ✅ 必要なSecrets設定

GitHub リポジトリの設定で以下のSecretsが設定されている必要があります：

### 1. GOOGLE_SERVICE_ACCOUNT
```json
{
  "type": "service_account",
  "project_id": "line-talk-extract",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "insidesales-dashboard-reader@line-talk-extract.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### 2. GOOGLE_DRIVE_FOLDER_ID
```
1l0MK5vWqOZnQ13GTyN5LoQk-SjZ7UG2U
```

## 🔧 Secrets設定手順

1. **GitHubリポジトリにアクセス**
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. 以下の2つのSecretsを追加：

### GOOGLE_SERVICE_ACCOUNT
- **Name**: `GOOGLE_SERVICE_ACCOUNT`
- **Secret**: サービスアカウントJSONの内容全体

### GOOGLE_DRIVE_FOLDER_ID  
- **Name**: `GOOGLE_DRIVE_FOLDER_ID`
- **Secret**: `1l0MK5vWqOZnQ13GTyN5LoQk-SjZ7UG2U`

## ✅ 設定確認方法

設定後、GitHub Actionsが次回実行時に以下のログが表示されるはず：
```
✅ GOOGLE_SERVICE_ACCOUNT: 設定済み
✅ GOOGLE_DRIVE_FOLDER_ID: 設定済み
```

## 🔄 手動実行テスト

設定後、GitHub Actionsを手動実行してテスト：
1. **Actions** タブ
2. **Sync Google Drive Data** ワークフロー
3. **Run workflow** ボタン
4. **Run workflow** をクリック 