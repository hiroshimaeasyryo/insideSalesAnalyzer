#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Drive同期スクリプト

GitHub ActionsでGoogle DriveからJSONファイルを定期同期するためのスクリプト
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from data_loader import get_data_loader
from google_drive_utils import get_drive_client

def ensure_dataset_directory():
    """datasetディレクトリを作成"""
    dataset_dir = Path('dataset')
    dataset_dir.mkdir(exist_ok=True)
    return dataset_dir

def sync_all_files():
    """Google Driveからすべてのファイルを同期"""
    try:
        # データローダーを初期化
        loader = get_data_loader()
        
        if not loader.is_drive_available():
            print("❌ Google Drive接続に失敗しました")
            return False
        
        # datasetディレクトリを準備
        dataset_dir = ensure_dataset_directory()
        
        # Google Driveクライアントを取得
        client = get_drive_client(
            service_account_file=loader.config.GOOGLE_SERVICE_ACCOUNT_FILE,
            folder_id=loader.config.GOOGLE_DRIVE_FOLDER_ID
        )
        
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
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 必要な環境変数が設定されていません: {', '.join(missing_vars)}")
        return False
    
    print("✅ 環境変数の検証完了")
    return True

def main():
    """メイン処理"""
    print("🚀 Google Drive同期スクリプト開始")
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