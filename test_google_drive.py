#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Drive接続テストスクリプト

使用方法:
    python test_google_drive.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def test_google_drive_connection():
    """Google Drive接続をテストする"""
    print("🧪 Google Drive接続テストを開始...")
    
    try:
        from config import get_config
        from google_drive_utils import test_connection
        from data_loader import get_data_loader
        
        # 設定確認
        config = get_config()
        print(f"\n📋 設定確認:")
        print(f"  Google Drive有効: {config.GOOGLE_DRIVE_ENABLED}")
        print(f"  フォルダID: {config.GOOGLE_DRIVE_FOLDER_ID}")
        print(f"  サービスアカウントファイル: {config.GOOGLE_SERVICE_ACCOUNT_FILE}")
        print(f"  ローカルフォールバック: {config.USE_LOCAL_FALLBACK}")
        
        # サービスアカウントファイル確認
        if config.GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_FILE):
            print(f"  ✅ サービスアカウントファイル存在")
        elif 'GOOGLE_SERVICE_ACCOUNT' in os.environ:
            print(f"  ✅ サービスアカウント環境変数設定済み")
        else:
            print(f"  ❌ サービスアカウント認証情報が見つかりません")
            print(f"     {config.GOOGLE_SERVICE_ACCOUNT_FILE} が存在しないか、")
            print(f"     GOOGLE_SERVICE_ACCOUNT 環境変数が設定されていません")
        
        # Google Drive設定の検証
        print(f"\n🔍 Google Drive設定検証:")
        is_valid, message = config.validate_google_drive_config()
        if is_valid:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")
            return False
        
        # 接続テスト
        print(f"\n🌐 Google Drive接続テスト:")
        success = test_connection(
            folder_id=config.GOOGLE_DRIVE_FOLDER_ID,
            service_account_file=config.GOOGLE_SERVICE_ACCOUNT_FILE
        )
        
        if success:
            print(f"  ✅ Google Drive接続成功")
        else:
            print(f"  ❌ Google Drive接続失敗")
            return False
        
        # データローダーテスト
        print(f"\n📁 データローダーテスト:")
        loader = get_data_loader()
        
        # データソース状態
        status = loader.get_data_source_status()
        active_source = status['active_source']
        print(f"  アクティブソース: {active_source}")
        
        if active_source == 'google_drive':
            print(f"  ✅ Google Driveから読み込み予定")
        else:
            print(f"  ℹ️ ローカルファイルから読み込み予定")
        
        # 利用可能月の取得
        months = loader.get_available_months()
        print(f"  利用可能な月: {len(months)}個")
        if months:
            print(f"    最新: {months[0]}")
            print(f"    その他: {', '.join(months[1:3])}...")
        
        # サンプルファイル読み込みテスト
        if months:
            print(f"\n📄 サンプルファイル読み込みテスト:")
            latest_month = months[0]
            
            try:
                basic_data, detail_data, summary_data = loader.load_analysis_data(latest_month)
                
                if basic_data:
                    print(f"  ✅ 基本分析データ ({latest_month}): {len(basic_data)} 項目")
                else:
                    print(f"  ❌ 基本分析データ読み込み失敗")
                
                if detail_data:
                    print(f"  ✅ 詳細分析データ ({latest_month}): {len(detail_data)} 項目")
                else:
                    print(f"  ❌ 詳細分析データ読み込み失敗")
                
                if summary_data:
                    print(f"  ✅ 月次サマリーデータ ({latest_month}): {len(summary_data)} 項目")
                else:
                    print(f"  ❌ 月次サマリーデータ読み込み失敗")
                
            except Exception as e:
                print(f"  ❌ ファイル読み込みエラー: {e}")
                return False
        
        print(f"\n🎉 すべてのテストが正常に完了しました！")
        return True
        
    except ImportError as e:
        print(f"❌ モジュールのインポートに失敗: {e}")
        print(f"   必要なライブラリがインストールされていない可能性があります")
        print(f"   pip install -r requirements.txt を実行してください")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def show_setup_help():
    """セットアップヘルプを表示"""
    print("""
📚 Google Drive連携セットアップヘルプ

Google Drive連携を使用するには以下の設定が必要です:

1. 環境変数の設定:
   export GOOGLE_DRIVE_ENABLED=true
   export GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
   export GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

2. サービスアカウントJSONファイルの配置:
   service_account.json ファイルをプロジェクトルートに配置

3. Google Driveフォルダの準備:
   - フォルダを作成してJSONファイルをアップロード
   - サービスアカウントと共有（閲覧者権限）

詳細は GOOGLE_DRIVE_SETUP.md を参照してください。
    """)

if __name__ == "__main__":
    print("🚀 Google Drive接続テストツール")
    print("=" * 50)
    
    # 引数確認
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_setup_help()
        sys.exit(0)
    
    # テスト実行
    success = test_google_drive_connection()
    
    if not success:
        print(f"\n❌ テストが失敗しました")
        print(f"   セットアップガイドを確認してください: GOOGLE_DRIVE_SETUP.md")
        print(f"   または --help オプションでヘルプを表示")
        sys.exit(1)
    else:
        print(f"\n🎯 Google Drive連携の準備が完了しました！")
        sys.exit(0) 