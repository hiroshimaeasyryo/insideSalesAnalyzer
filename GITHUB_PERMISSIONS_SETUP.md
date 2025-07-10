# GitHub Actions 権限設定ガイド

## 📋 現在の状況

✅ **ワークフロー修正完了**:
- `permissions: contents: write` を追加
- `checkout` アクションで `GITHUB_TOKEN` を明示的に指定

## 🔧 リポジトリ設定の確認

以下の設定を確認してください：

### 1. Actions権限設定

**GitHub リポジトリ** → **Settings** → **Actions** → **General**

**「Workflow permissions」** セクションで以下を確認：

#### 推奨設定 A: Read and write permissions
```
○ Read and write permissions
  Allow GitHub Actions to create and approve pull requests
  ☑ (チェック推奨)
```

#### または設定 B: Read repository contents and packages permissions
```
○ Read repository contents and packages permissions
```
この場合、個別にpermissionsを指定（既に実装済み）

### 2. 権限スコープ確認

**Actions** → **General** → **Fork pull request workflows from outside collaborators**:
```
○ Require approval for first-time contributors
```

## 🔄 テスト実行

設定完了後：

1. **Actions** タブに移動
2. **Sync Google Drive Data** ワークフローを選択
3. **Run workflow** で手動実行
4. ログで以下を確認：
   ```
   ✅ データが更新されました
   ```

## 🎯 期待される結果

正常実行時のログ：
```
✅ Google Drive API認証成功
📁 フォルダ内のファイル数: XX
📁 XX個のファイルを同期開始...
✅ filename.json - 同期完了
📊 同期結果:
  ✅ 成功: XX件
  ❌ 失敗: 0件
[main abc1234] 🔄 Auto-sync: Google Drive data updated at Thu Jul 10 12:12:39 UTC 2025
✅ データが更新されました
```

## ⚠️ トラブルシューティング

### まだ403エラーが出る場合：

1. **Personal Access Token** を使用
   - **Settings** → **Developer settings** → **Personal access tokens**
   - **repo** スコープで作成
   - **GitHub Secrets** に `PERSONAL_ACCESS_TOKEN` として保存

2. **ワークフロー修正**:
   ```yaml
   - name: 📥 Checkout repository
     uses: actions/checkout@v4
     with:
       token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
   ``` 