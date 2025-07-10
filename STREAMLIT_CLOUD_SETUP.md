# 🚀 Streamlit Cloud 本番環境設定ガイド

## 🎯 **目標**
機微データをリポジトリから除外し、Streamlit CloudでGoogle Driveからデータを読み込む

## ⚠️ **現在の状況**
- ✅ ローカル環境: Google Drive読み込み成功
- ❌ 本番環境: 設定不足によりフォールバック発生

## 🔧 **Step 1: サービスアカウント情報の準備**

### 1-1. ローカルの `service_account.json` を開く
```bash
cat service_account.json
```

### 1-2. 内容をコピー
全体をコピーしてください（改行も含めて）

## 🔐 **Step 2: Streamlit Cloud Secrets設定**

### 2-1. Streamlit Cloud ダッシュボードにアクセス
1. [Streamlit Cloud](https://share.streamlit.io/) にログイン
2. あなたのアプリを選択
3. **Settings** → **Secrets** をクリック

### 2-2. Secrets設定を追加
以下の内容を **Secrets** に貼り付け：

```toml
[google_drive]
enabled = true
folder_id = "1l0MK5vWRTrM9k8..." # あなたのフォルダIDに変更
production_mode = true
use_local_fallback = false

service_account = '''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id", 
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40project.iam.gserviceaccount.com"
}
'''
```

### 2-3. **重要**: 設定値の修正
- **`folder_id`**: あなたのGoogle DriveフォルダID（`1l0MK5vW...`）に変更
- **`service_account`**: Step 1でコピーしたJSONの内容に置き換え

### 2-4. 設定保存
**Save** ボタンをクリックして保存

## 🔄 **Step 3: アプリの再起動**

### 3-1. 自動再起動を待つ
設定保存後、アプリが自動的に再起動されます

### 3-2. または手動再起動
- Streamlit Cloudの **Reboot** ボタンをクリック

## ✅ **Step 4: 動作確認**

### 4-1. デバッグページで確認
1. アプリにアクセス
2. 「🔍 システムデバッグ」を選択
3. 「📋 設定確認」タブで確認：

期待される表示：
```json
{
  "GOOGLE_DRIVE_ENABLED": "true",
  "GOOGLE_DRIVE_FOLDER_ID": "1l0MK5vW...",
  "GOOGLE_SERVICE_ACCOUNT": "設定済み (xxxx 文字)",
  "PRODUCTION_MODE": "true",
  "USE_LOCAL_FALLBACK": "false"
}
```

### 4-2. 接続テスト
1. 「🔌 接続テスト」タブ
2. 「🔄 接続テストを実行」ボタンをクリック

期待される結果：
```
✅ Google Drive API認証成功
✅ フォルダアクセス成功: 100 ファイル検出
```

### 4-3. データテスト  
1. 「📊 データテスト」タブ
2. 「2025-07」を選択
3. 「📥 データ読み込みテスト」ボタンをクリック

期待される結果：
```
✅ 基本分析データ読み込み成功
✅ 詳細分析データ読み込み成功
✅ 月次サマリーデータ読み込み成功
```

## 🎯 **Step 5: メインページで確認**

### 5-1. 「📊 単月詳細」を選択
### 5-2. サイドバーで確認：
```
🗂️ データソース
🌐 Google Driveから読み込み中
フォルダID: 1l0MK5vW...
✅ Google Drive: 利用可能
```

### 5-3. データが正常に表示されることを確認

## 🚨 **トラブルシューティング**

### エラー: "本番環境モードでGoogle Drive接続に失敗"

**原因**:
- サービスアカウントJSONの形式エラー
- プライベートキーの改行文字が正しくない

**解決策**:
1. `service_account.json`を再度コピー
2. プライベートキーの `\n` が正しく含まれているか確認
3. JSON全体が `'''` で囲まれているか確認

### エラー: "フォルダアクセス失敗"

**原因**:
- フォルダIDが間違っている
- サービスアカウントがフォルダにアクセスできない

**解決策**:
1. Google Driveでフォルダを右クリック → 共有
2. サービスアカウントのメールアドレスを編集者として追加
3. フォルダIDを再確認

### 確認用コマンド（ローカル環境）
```bash
# サービスアカウントファイルの確認
python -c "import json; print(json.load(open('service_account.json'))['client_email'])"

# フォルダIDの確認  
python -c "from config import get_config; print(get_config().GOOGLE_DRIVE_FOLDER_ID)"
```

## 📋 **チェックリスト**

設定完了後、以下をすべて確認：

### 📝 Streamlit Cloud設定
- [ ] Secrets に `[google_drive]` セクションを追加
- [ ] `folder_id` を正しい値に設定
- [ ] `service_account` にJSONを正しく設定
- [ ] `production_mode = true` に設定  
- [ ] `use_local_fallback = false` に設定

### 🔌 動作確認
- [ ] デバッグページで環境変数が正しく表示される
- [ ] 接続テストが成功する
- [ ] データテストが成功する
- [ ] メインページでGoogle Driveから読み込まれる
- [ ] ローカルファイルにフォールバックしない

### 🔐 セキュリティ確認
- [ ] `dataset/` ディレクトリがリポジトリに含まれない
- [ ] `service_account.json` がリポジトリに含まれない
- [ ] 本番環境でローカルファイルが使用されない

## 🎉 **完了！**

すべてのチェックが完了したら、機微データを安全に管理しながら本番環境でGoogle Driveからデータを読み込むシステムの完成です！ 