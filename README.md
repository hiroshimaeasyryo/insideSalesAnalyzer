# 📊 インサイドセールス分析ダッシュボード

## 🌟 概要
架電データを可視化するインタラクティブなダッシュボードです。Google Drive連携により、クラウド上のJSONファイルを直接読み込み可能。認証機能付きで、月次トレンド、支店別・スタッフ別分析を提供します。

## 🔧 最近の修正 (2025年1月)

### 本番環境でのGoogle Drive接続問題の解決

**問題**: 開発環境ではGoogle Driveから正常にデータを読み込むが、本番環境（Streamlit Cloud）ではローカルファイルを読みに行ってしまう

**原因**: 
- `is_drive_available()`メソッドのLRUキャッシュが一度失敗した結果をキャッシュし続ける
- 本番環境でのGoogle Drive接続テストの詳細エラー情報が不足

**解決策**:
1. LRUキャッシュを削除し、毎回接続テストを実行
2. より詳細なエラーログを追加
3. 本番環境モードでのエラーハンドリングを改善

### GitHub Actions定期キャッシュの停止

**変更**: 毎時実行されていたGoogle Drive同期の定期実行を停止

**理由**: 本番環境でGoogle Driveから直接読み込むため、ローカルキャッシュが不要になった

## 🗂️ 新機能: Google Drive連携

### データソースの選択
- **🌐 Google Drive**: クラウド上のJSONファイルを読み込み
- **📁 ローカルファイル**: 従来通りのローカルファイルシステム  
- **🔄 自動フォールバック**: Google Drive接続失敗時にローカルファイルを使用

### メリット
- **共有簡単**: チームメンバーとのデータ共有が容易
- **自動同期**: Google Apps Scriptで生成したファイルを自動読み込み
- **バックアップ**: クラウド上での安全なデータ保管

## 🚀 ローカル実行

### 1. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 2. アプリの起動
```bash
streamlit run streamlit_app.py
```

### 3. ブラウザでアクセス
```
http://localhost:8501
```

## 🌐 Google Drive連携設定

### クイックスタート
```bash
# 1. 環境変数を設定
export GOOGLE_DRIVE_ENABLED=true
export GOOGLE_DRIVE_FOLDER_ID=your-folder-id
export GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# 2. 接続テスト
python test_google_drive.py

# 3. アプリ起動
streamlit run streamlit_app.py
```

### 詳細セットアップ
詳細な設定手順は [`GOOGLE_DRIVE_SETUP.md`](GOOGLE_DRIVE_SETUP.md) を参照してください。

- Google Cloud Console設定
- サービスアカウント作成
- Google Driveフォルダ準備
- 認証設定

## 📈 機能

### メイン機能
- **認証システム**: ユーザー名・パスワード認証
- **月選択**: 直近6ヶ月のデータを選択可能
- **リアルタイム更新**: 月変更で自動データ更新
- **🗂️ データソース表示**: サイドバーでGoogle Drive/ローカルの状態を確認

### 分析機能
1. **📈 月次トレンド**
   - 日別架電数・成功率・アポイント数の推移
   - インタラクティブなグラフ表示

2. **🏢 支店別分析**
   - 支店別総架電数・成功率
   - ランキング表示

3. **👥 スタッフ別分析**
   - 架電数ランキング
   - 成約率ランキング
   - 個人別パフォーマンス

4. **📋 詳細データ**
   - フィルター機能（支店・スタッフ）
   - CSVダウンロード機能

## 🌐 Streamlit Cloud デプロイ

### 1. GitHubにプッシュ
```bash
git add .
git commit -m "Add Streamlit dashboard"
git push origin main
```

### 2. Streamlit Cloudでデプロイ
1. [Streamlit Cloud](https://share.streamlit.io/)にアクセス
2. GitHubアカウントでログイン
3. リポジトリを選択
4. メインファイル: `streamlit_app.py`
5. デプロイ実行

## 📊 データサイズ制限
- **現在のデータサイズ**: 約4.2MB
- **Streamlit無料プラン制限**: 200MB/ファイル
- **✅ 制限内で十分余裕**

## 🔐 セキュリティ・本番環境

### 🛡️ データ保護
- **機微データの除外**: `dataset/`フォルダはリポジトリに含まれません
- **読み取り専用権限**: Google Drive接続は読み取り専用
- **環境別制御**: 本番環境と開発環境での異なるセキュリティレベル

### 🔑 認証・アクセス制御
- サービスアカウントベースの認証
- 認証情報の環境変数管理
- Google Cloud Console での権限管理

### 🚀 本番環境向け機能
- **PRODUCTION_MODE**: 本番環境での強化されたセキュリティ
- **フォールバック制御**: ローカルファイル代替機能の有効/無効
- **環境別設定**: プラットフォーム固有の設定サポート

### 🔧 本番環境設定
詳細な本番環境設定は [`PRODUCTION_SETUP.md`](PRODUCTION_SETUP.md) を参照：

#### 基本設定
```bash
# 本番環境の推奨設定
export PRODUCTION_MODE=true
export USE_LOCAL_FALLBACK=false
export GOOGLE_DRIVE_ENABLED=true
export GOOGLE_DRIVE_FOLDER_ID=your-folder-id
export GOOGLE_SERVICE_ACCOUNT='{"type": "service_account", ...}'
```

#### プラットフォーム対応
- ✅ Streamlit Cloud (Secrets管理)
- ✅ Heroku (環境変数)
- ✅ Vercel (環境変数)
- ✅ AWS/GCP/Azure (環境変数)

#### 設定確認
```bash
# 本番環境での設定確認
python debug_env.py
```

## 🔧 カスタマイズ

### データパスの変更
データファイルのパスを変更する場合：
```python
with open(f'data/基本分析_{month}.json', 'r', encoding='utf-8') as f:
```

## 📱 PDF出力
ブラウザの印刷機能を使用：
1. `Ctrl+P` (Windows) / `Cmd+P` (Mac)
2. 印刷設定でPDF保存を選択
3. レイアウトを調整して保存

## 🛠️ トラブルシューティング

### 🚀 本番環境関連

#### 本番環境でGoogle Drive読み込みが失敗する
**症状**: ローカルでは動作するが、本番環境でフォールバックが発生

**原因**:
- 環境変数の設定不備
- サービスアカウント認証情報の問題  
- ネットワーク/ファイアウォールの制限

**解決策**:
```bash
# 設定確認
python debug_env.py

# 本番環境モードでテスト
PRODUCTION_MODE=true USE_LOCAL_FALLBACK=false python debug_env.py
```

詳細は [`PRODUCTION_SETUP.md`](PRODUCTION_SETUP.md) を参照

#### 機微データがリポジトリに含まれる
**解決策**:
```bash
# データファイルを除外
git rm -r --cached dataset/*.json
git add .gitignore
git commit -m "Remove sensitive data from repository"
```

### 🌐 Google Drive関連

#### 🌐 接続エラー
```bash
# 接続テストでエラー確認
python test_google_drive.py
```
- サービスアカウントJSONファイルのパス確認
- フォルダIDが正しいか確認
- フォルダがサービスアカウントと共有されているか確認

#### 📁 ファイルが見つからない
- Google DriveフォルダにJSONファイルがアップロードされているか確認
- ファイル名の形式: `基本分析_YYYY-MM.json`
- フォールバック設定を確認: `USE_LOCAL_FALLBACK=true`

### その他

#### データが見つからないエラー
- データファイルが`dataset/`フォルダに存在するか確認（ローカル使用時）
- ファイル名の形式: `基本分析_YYYY-MM.json`

#### 認証エラー
- ユーザー名・パスワードが正しいか確認
- ブラウザのキャッシュをクリア

#### ポート競合
```bash
streamlit run streamlit_app.py --server.port 8502
```

## 🧪 Google Drive接続テスト

Google Drive連携が正しく設定されているかテストできます：

```bash
# 詳細なテスト実行
python test_google_drive.py

# ヘルプ表示
python test_google_drive.py --help
```

このテストでは以下を確認します：
- Google Drive API認証
- フォルダアクセス権限
- JSONファイルの読み込み
- データローダーの動作

## 📞 サポート
問題が発生した場合は、以下を確認してください：
1. 依存関係が正しくインストールされているか
2. Google Drive設定が正しいか（`python test_google_drive.py`で確認）
3. データファイルの形式が正しいか
4. ブラウザのコンソールにエラーがないか 

## 🐛 デバッグ

Streamlitアプリ内でのシステムデバッグ:

1. アプリにログイン
2. サイドバーで「🔧 システムデバッグ」を選択
3. 「🔍 詳細デバッグ実行」ボタンをクリック

## 📁 ファイル構成

```
├── app.py                    # Flaskアプリケーション
├── streamlit_app.py          # Streamlitアプリケーション（デバッグ機能内蔵）
├── data_loader.py            # データ読み込みモジュール
├── config.py                 # 設定管理
├── google_drive_utils.py     # Google Drive連携
├── analysis_dashboard.py     # 分析ロジック
├── dataset/                  # ローカルデータ（開発用）
└── .github/workflows/        # GitHub Actions（定期実行停止済み）
``` 