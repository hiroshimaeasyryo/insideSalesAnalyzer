#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Drive同期スクリプト（独立版）

GitHub ActionsでGoogle DriveからJSONファイルを定期同期するためのスクリプト
streamlit依存なし
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

class SimpleGoogleDriveClient:
    """シンプルなGoogle Drive APIクライアント（streamlit依存なし）"""
    
    def __init__(self, service_account_info, folder_id):
        self.folder_id = folder_id
        self.service = None
        self._authenticate(service_account_info)
    
    def _authenticate(self, service_account_info):
        """Google Drive APIの認証"""
        try:
            # 環境変数からサービスアカウント情報を取得
            if isinstance(service_account_info, str):
                service_account_info = json.loads(service_account_info)
            
            credentials = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            
            self.service = build('drive', 'v3', credentials=credentials)
            print("✅ Google Drive API認証成功")
            
        except Exception as e:
            print(f"❌ Google Drive API認証失敗: {e}")
            raise
    
    def list_files_in_folder(self, file_extension='.json'):
        """フォルダ内のファイル一覧を取得"""
        if not self.service:
            raise RuntimeError("Google Drive APIが認証されていません")
        
        try:
            # フォルダ内のファイルを検索
            query = f"parents in '{self.folder_id}' and trashed=false"
            if file_extension:
                query += f" and name contains '{file_extension}'"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            print(f"📁 フォルダ内のファイル数: {len(files)}")
            
            return files
            
        except Exception as e:
            print(f"❌ ファイル一覧取得エラー: {e}")
            return []
    
    def download_file_content(self, file_id):
        """ファイルの内容を文字列として取得"""
        if not self.service:
            raise RuntimeError("Google Drive APIが認証されていません")
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            content = file_content.read().decode('utf-8')
            
            return content
            
        except Exception as e:
            print(f"❌ ファイルダウンロードエラー (ID: {file_id}): {e}")
            raise

def ensure_dataset_directory():
    """datasetディレクトリを作成"""
    dataset_dir = Path('dataset')
    dataset_dir.mkdir(exist_ok=True)
    return dataset_dir

def sync_all_files():
    """Google Driveからすべてのファイルを同期"""
    try:
        # 環境変数取得
        service_account_env = os.getenv('GOOGLE_SERVICE_ACCOUNT')
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        if not service_account_env:
            print("❌ GOOGLE_SERVICE_ACCOUNT環境変数が設定されていません")
            return False
        
        if not folder_id:
            print("❌ GOOGLE_DRIVE_FOLDER_ID環境変数が設定されていません")
            return False
        
        # datasetディレクトリを準備
        dataset_dir = ensure_dataset_directory()
        
        # Google Driveクライアントを初期化
        client = SimpleGoogleDriveClient(service_account_env, folder_id)
        
        # フォルダ内のすべてのJSONファイルを取得
        files = client.list_files_in_folder(file_extension='.json')
        
        if not files:
            print("⚠️ Google Driveフォルダにファイルが見つかりません")
            return False
        
        print(f"📁 {len(files)}個のファイルを同期開始...")
        
        synced_count = 0
        failed_count = 0
        
        for file_info in files:
            filename = file_info['name']
            file_id = file_info['id']
            
            try:
                # ファイルをダウンロード
                content = client.download_file_content(file_id)
                
                # JSONとして検証
                json_data = json.loads(content)
                
                # ローカルファイルに保存
                local_path = dataset_dir / filename
                with open(local_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ {filename} - 同期完了")
                synced_count += 1
                
            except Exception as e:
                print(f"❌ {filename} - 同期失敗: {e}")
                failed_count += 1
        
        print(f"\n📊 同期結果:")
        print(f"  ✅ 成功: {synced_count}件")
        print(f"  ❌ 失敗: {failed_count}件")
        print(f"  📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return synced_count > 0
        
    except Exception as e:
        print(f"❌ 同期処理でエラーが発生: {e}")
        return False

def validate_environment():
    """環境変数の検証"""
    required_vars = [
        'GOOGLE_SERVICE_ACCOUNT',
        'GOOGLE_DRIVE_FOLDER_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: 設定済み")
    
    if missing_vars:
        print(f"❌ 必要な環境変数が設定されていません: {', '.join(missing_vars)}")
        return False
    
    print("✅ 環境変数の検証完了")
    return True

def main():
    """メイン処理"""
    print("🚀 Google Drive同期スクリプト開始（独立版）")
    print("=" * 50)
    
    # 環境変数の検証
    if not validate_environment():
        sys.exit(1)
    
    # 同期実行
    success = sync_all_files()
    
    if success:
        print("\n🎉 同期が正常に完了しました！")
        sys.exit(0)
    else:
        print("\n💥 同期に失敗しました")
        sys.exit(1)

if __name__ == '__main__':
    main() 