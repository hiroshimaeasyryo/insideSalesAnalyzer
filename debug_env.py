#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
環境設定デバッグスクリプト

本番環境でのGoogle Drive設定状況を確認
"""

import os
import sys
from pathlib import Path

def debug_environment():
    """環境設定をデバッグ"""
    print("🔍 環境設定デバッグ")
    print("=" * 50)
    
    # 基本的な環境情報
    print(f"📍 Python実行パス: {sys.executable}")
    print(f"📁 現在のディレクトリ: {os.getcwd()}")
    print(f"🐍 Pythonバージョン: {sys.version}")
    
    print("\n📋 Google Drive関連の環境変数:")
    google_drive_vars = [
        'GOOGLE_DRIVE_ENABLED',
        'GOOGLE_DRIVE_FOLDER_ID', 
        'GOOGLE_SERVICE_ACCOUNT_FILE',
        'GOOGLE_SERVICE_ACCOUNT',
        'USE_LOCAL_FALLBACK'
    ]
    
    for var in google_drive_vars:
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_SERVICE_ACCOUNT':
                # サービスアカウント情報は部分的に表示
                print(f"  {var}: 設定済み ({len(value)} 文字)")
            elif var == 'GOOGLE_DRIVE_FOLDER_ID':
                # フォルダIDは部分的に表示
                print(f"  {var}: {value[:8]}...")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: ❌ 未設定")
    
    print("\n📂 ファイル存在確認:")
    files_to_check = [
        'service_account.json',
        '.env',
        'dataset/',
        'config.py',
        'google_drive_utils.py',
        'data_loader.py'
    ]
    
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            if path.is_dir():
                file_count = len(list(path.glob('*.json')))
                print(f"  {file_path}: ✅ 存在 ({file_count} JSONファイル)")
            else:
                print(f"  {file_path}: ✅ 存在")
        else:
            print(f"  {file_path}: ❌ 存在しない")
    
    print("\n🔧 モジュールインポートテスト:")
    modules_to_test = [
        'google.auth',
        'googleapiclient.discovery',
        'config',
        'google_drive_utils',
        'data_loader'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"  {module}: ✅ インポート成功")
        except ImportError as e:
            print(f"  {module}: ❌ インポート失敗 - {e}")
        except Exception as e:
            print(f"  {module}: ⚠️ エラー - {e}")
    
    print("\n🌐 Google Drive接続テスト:")
    try:
        from config import get_config
        config = get_config()
        
        print(f"  設定読み込み: ✅ 成功")
        print(f"  Drive有効: {config.GOOGLE_DRIVE_ENABLED}")
        print(f"  フォルダID: {'設定済み' if config.GOOGLE_DRIVE_FOLDER_ID else '未設定'}")
        
        if config.GOOGLE_DRIVE_ENABLED and config.GOOGLE_DRIVE_FOLDER_ID:
            try:
                from google_drive_utils import test_connection
                success = test_connection(
                    folder_id=config.GOOGLE_DRIVE_FOLDER_ID,
                    service_account_file=config.GOOGLE_SERVICE_ACCOUNT_FILE
                )
                if success:
                    print(f"  接続テスト: ✅ 成功")
                else:
                    print(f"  接続テスト: ❌ 失敗")
            except Exception as e:
                print(f"  接続テスト: ❌ エラー - {e}")
        else:
            print(f"  接続テスト: ⏭️ スキップ（設定不足）")
            
    except Exception as e:
        print(f"  設定読み込み: ❌ エラー - {e}")
    
    print("\n📊 推奨アクション:")
    
    # 環境変数チェック
    if not os.getenv('GOOGLE_DRIVE_ENABLED'):
        print("  ⚠️ GOOGLE_DRIVE_ENABLED を true に設定してください")
    
    if not os.getenv('GOOGLE_DRIVE_FOLDER_ID'):
        print("  ⚠️ GOOGLE_DRIVE_FOLDER_ID を設定してください")
    
    if not os.getenv('GOOGLE_SERVICE_ACCOUNT') and not Path('service_account.json').exists():
        print("  ⚠️ GOOGLE_SERVICE_ACCOUNT 環境変数またはservice_account.jsonファイルが必要です")
    
    # 本番環境向けの推奨事項
    print("  💡 本番環境では以下を推奨:")
    print("     - 環境変数でのサービスアカウント設定")
    print("     - USE_LOCAL_FALLBACK=false でフォールバック無効化")
    print("     - datasetディレクトリをリポジトリから除外")

if __name__ == "__main__":
    debug_environment() 