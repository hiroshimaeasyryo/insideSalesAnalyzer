# Streamlit Cloud 正しいSecrets設定

## 🔧 **必須設定**

Streamlit Cloudの **Settings** → **Secrets** で以下を設定：

```toml
# 本番環境モード（重要！）
PRODUCTION_MODE = true
GOOGLE_DRIVE_ENABLED = true
USE_LOCAL_FALLBACK = false

# Google Drive設定
GOOGLE_DRIVE_FOLDER_ID = "1l0MK5vWqOZnQ13GTyN5LoQk-SjZ7UG2U"

# サービスアカウント情報（JSON形式）
[google_drive]
service_account = '''
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
'''
```

## ⚠️ **重要な設定ポイント**

### 1. PRODUCTION_MODE = true
- **必須**: Streamlit Cloudでは必ず `true`
- Google Drive専用モードになります

### 2. USE_LOCAL_FALLBACK = false  
- **推奨**: ローカルフォールバックを無効化
- 本番環境では確実にGoogle Driveからデータを取得

### 3. service_account は [google_drive] セクション内
- **必須**: サービスアカウントJSONは `[google_drive]` セクション内に配置

## 🔄 **設定後の動作**

### ✅ 正常時
```
✅ Google Drive API認証成功
✅ データソース: Google Drive
✅ 利用可能月数: 13ヶ月
```

### ❌ 設定ミス時のエラー
```
❌ 本番環境モードではGoogle Drive設定が必須です
❌ 本番環境モードでGoogle Drive接続に失敗しました
```

## 🧪 **設定確認方法**

アプリ起動後、**データソース状態** で以下を確認：

```
📊 データソース状態
- Google Drive: ✅ 利用可能
- アクティブソース: google_drive  
- キャッシュ: 有効
```

## 🔧 **トラブルシューティング**

### データが読み込めない場合：

1. **Secrets設定確認**:
   - `PRODUCTION_MODE = true`
   - `GOOGLE_DRIVE_FOLDER_ID` 正確な値
   
2. **サービスアカウント確認**:
   - JSON形式が正しい
   - `[google_drive]` セクション内に配置
   
3. **アプリ再起動**:
   - Streamlit Cloudでアプリを再起動 