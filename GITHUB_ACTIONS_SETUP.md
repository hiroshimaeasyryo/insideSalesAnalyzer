# 🔄 GitHub Actions定期同期システム セットアップガイド

Google DriveからJSONファイルを自動で同期し、Streamlit Cloudでローカルファイル並みの高速読み込みを実現します。

## 🎯 システムの特徴

- **毎時自動同期**: Google Driveの最新データを自動取得
- **高速読み込み**: ローカルファイル並みの読み込み速度
- **手動実行可能**: 緊急時の手動同期も対応
- **同期レポート**: 実行結果の詳細レポート

## 📋 セットアップ手順

### 1. GitHub Secretsの設定

リポジトリの`Settings` > `Secrets and variables` > `Actions`で以下を設定：

#### **GOOGLE_SERVICE_ACCOUNT**
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
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

#### **GOOGLE_DRIVE_FOLDER_ID**
```
1l0MK5vWqOZnQ13GTyN5LoQk-SjZ7UG2U
```

### 2. Streamlit Cloud設定の更新

**Streamlit Cloud Secrets**を以下に更新：

```toml
[google_drive]
enabled = true
folder_id = "1l0MK5vWqOZnQ13GTyN5LoQk-SjZ7UG2U"
production_mode = false  # GitHubからローカルファイルを使用
use_local_fallback = true
```

### 3. ワークフローの有効化

1. **手動実行でテスト**:
   - `Actions`タブ → `🔄 Google Drive Data Sync`
   - `Run workflow`ボタンをクリック

2. **自動同期確認**:
   - 毎時0分に自動実行される
   - 実行結果は`Actions`タブで確認可能

## 🔧 設定カスタマイズ

### 同期頻度の変更

`.github/workflows/sync-google-drive.yml`の`cron`設定を変更：

```yaml
schedule:
  # 毎30分に実行
  - cron: '0,30 * * * *'
  
  # 毎6時間に実行  
  - cron: '0 */6 * * *'
  
  # 平日の営業時間のみ（9-18時、毎時）
  - cron: '0 9-18 * * 1-5'
```

### 同期対象ファイルの制限

`sync_google_drive.py`で特定ファイルのみ同期：

```python
# 基本分析ファイルのみ同期
if not filename.startswith('基本分析_'):
    continue
    
# 過去3ヶ月のみ同期
import re
match = re.search(r'(\d{4}-\d{2})', filename)
if match:
    file_month = match.group(1)
    # 日付比較ロジック
```

## 📊 運用と監視

### 同期状況の確認

1. **GitHub Actions**:
   - 実行ログで詳細確認
   - 失敗時の自動通知

2. **Streamlit Cloud**:
   - サイドバーでキャッシュ状況確認
   - データソース表示

### トラブルシューティング

#### ❌ 同期失敗の場合

1. **Secret設定確認**:
   ```bash
   # ローカルでテスト
   python sync_google_drive.py
   ```

2. **権限確認**:
   - サービスアカウントのフォルダアクセス権
   - Google Drive API有効化

3. **手動実行**:
   - GitHub ActionsのRun workflowで強制実行

#### ⚠️ 部分的な失敗

- 失敗したファイルのみ再実行
- Google Drive API制限確認
- ファイル破損チェック

## 🚀 期待される効果

### パフォーマンス改善

- **初回読み込み**: Google Drive API → ローカルファイル（**10-50倍高速化**）
- **キャッシュ効果**: 並列読み込み + メモリキャッシュ
- **API制限回避**: 頻繁なAPI呼び出しを削減

### 運用改善

- **自動更新**: 人的作業なしでデータ最新化
- **可用性向上**: Google Drive障害時も動作継続
- **監視可能**: 同期状況の可視化

## 📋 運用チェックリスト

- [ ] GitHub Secrets設定完了
- [ ] Streamlit Cloud Secrets更新完了
- [ ] 手動実行テスト成功
- [ ] 自動同期動作確認
- [ ] Streamlitアプリの高速化確認
- [ ] 監視・アラート設定（任意）

---

## 🔗 関連ファイル

- **ワークフロー**: `.github/workflows/sync-google-drive.yml`
- **同期スクリプト**: `sync_google_drive.py`
- **データローダー**: `data_loader.py` (並列読み込み対応)
- **設定**: `config.py` (本番環境設定)

この設定により、Google Driveの利便性を保ちながら、ローカルファイル並みの高速読み込みが実現できます！ 