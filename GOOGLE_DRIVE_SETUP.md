# 📁 Google Drive連携セットアップガイド

このガイドでは、JSONファイルをGoogle Driveから読み込むための設定方法を説明します。

## 🚀 セットアップ手順

### 1. Google Cloud Consoleでプロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. プロジェクト名をメモしておく

### 2. Google Drive APIを有効化

1. Google Cloud Consoleで「APIとサービス」→「ライブラリ」を選択
2. "Google Drive API"を検索
3. 「有効にする」をクリック

### 3. サービスアカウントの作成

1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「サービスアカウント」をクリック
3. サービスアカウント名を入力（例：`sales-dashboard-reader`）
4. 「作成して続行」をクリック
5. ロール設定はスキップして「完了」をクリック

### 4. サービスアカウントキーの生成

1. 作成したサービスアカウントをクリック
2. 「キー」タブに移動
3. 「鍵を追加」→「新しい鍵を作成」をクリック
4. 「JSON」を選択して「作成」をクリック
5. ダウンロードされたJSONファイルを`service_account.json`として保存

### 5. Google Driveフォルダの準備

1. Google Driveで新しいフォルダを作成（例：`営業分析データ`）
2. フォルダを右クリックして「共有」を選択
3. サービスアカウントのメールアドレス（`xxxxx@project-id.iam.gserviceaccount.com`）を追加
4. 権限を「閲覧者」に設定
5. フォルダIDをメモ（URLの`/folders/`以降の部分）

### 6. JSONファイルのアップロード

現在`dataset/`フォルダにあるJSONファイルをGoogle Driveフォルダにアップロード：
- `基本分析_*.json`
- `詳細分析_*.json`
- `月次サマリー_*.json`
- `定着率分析_*.json`

## ⚙️ 環境設定

### 方法1: 環境変数で設定（推奨）

```bash
# 基本設定
export GOOGLE_DRIVE_ENABLED=true
export GOOGLE_DRIVE_FOLDER_ID="your-folder-id-here"

# サービスアカウント（ファイルまたは環境変数）
export GOOGLE_SERVICE_ACCOUNT_FILE="service_account.json"
# または
export GOOGLE_SERVICE_ACCOUNT='{"type": "service_account", ...}'

# フォールバック設定
export USE_LOCAL_FALLBACK=true
```

### 方法2: `.env`ファイルで設定

`.env`ファイルを作成：

```env
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
USE_LOCAL_FALLBACK=true
```

## 🧪 動作確認

### 接続テスト

```python
from google_drive_utils import test_connection

# 接続テスト実行
success = test_connection(
    folder_id="your-folder-id",
    service_account_file="service_account.json"
)

if success:
    print("✅ Google Drive接続成功")
else:
    print("❌ Google Drive接続失敗")
```

### アプリケーション実行

```bash
# Streamlitアプリ起動
streamlit run streamlit_app.py

# Flaskアプリ起動
python app.py
```

## 📊 使用方法

### 自動フォールバック

- Google Drive接続が失敗した場合、自動的にローカルファイルを読み込み
- `USE_LOCAL_FALLBACK=false`にすると、Google Driveのみ使用

### データソース確認

Streamlitアプリのサイドバーで現在のデータソースを確認可能：
- 🌐 Google Driveから読み込み中
- 📁 ローカルファイルから読み込み中

## 🔧 トラブルシューティング

### よくあるエラー

#### 1. 認証エラー
```
❌ Google Drive API認証失敗
```
**解決策：**
- サービスアカウントJSONファイルのパスを確認
- ファイル権限（読み取り可能）を確認

#### 2. フォルダアクセスエラー
```
❌ ファイル一覧取得エラー
```
**解決策：**
- フォルダIDが正しいか確認
- サービスアカウントがフォルダに共有されているか確認

#### 3. ファイルが見つからない
```
❌ ファイルが見つかりません: 基本分析_2025-01.json
```
**解決策：**
- ファイル名が正確か確認
- ファイルがGoogle Driveフォルダにアップロードされているか確認

### デバッグ情報

コンソールログで詳細な情報を確認：
```python
from data_loader import get_data_loader

loader = get_data_loader()
status = loader.get_data_source_status()
print(status)
```

## 🔒 セキュリティ注意事項

1. **サービスアカウントJSONファイル**
   - Gitにコミットしない（`.gitignore`に追加）
   - 適切な権限（読み取り専用）で設定
   
2. **環境変数**
   - 本番環境では環境変数を使用
   - JSONファイルではなく`GOOGLE_SERVICE_ACCOUNT`環境変数を推奨

3. **フォルダ共有**
   - 最小限の権限（閲覧者）で共有
   - 不要になったら共有を削除

## 🚀 本番環境でのデプロイ

### Streamlit Cloud

`secrets.toml`に設定：
```toml
[google_drive]
enabled = true
folder_id = "your-folder-id"
service_account = """
{
  "type": "service_account",
  ...
}
"""
```

### その他のクラウドサービス

環境変数として設定：
- `GOOGLE_DRIVE_ENABLED=true`
- `GOOGLE_DRIVE_FOLDER_ID=your-folder-id`
- `GOOGLE_SERVICE_ACCOUNT={"type": "service_account", ...}` 