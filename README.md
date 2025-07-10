# 📊 インサイドセールス分析ダッシュボード

## 🌟 概要
架電データを可視化するインタラクティブなダッシュボードです。Google Drive連携により、クラウド上のJSONファイルを直接読み込み可能。認証機能付きで、月次トレンド、支店別・スタッフ別分析を提供します。

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
export GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
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

### Google Drive関連

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