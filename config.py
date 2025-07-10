#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
設定管理モジュール

アプリケーションの設定を管理します
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

class Config:
    """アプリケーション設定クラス"""
    
    # Google Drive設定
    GOOGLE_DRIVE_ENABLED = os.getenv('GOOGLE_DRIVE_ENABLED', 'false').lower() == 'true'
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
    
    # ローカルデータ設定
    LOCAL_DATA_DIR = Path(__file__).parent / 'dataset'
    
    # フォールバック設定
    USE_LOCAL_FALLBACK = os.getenv('USE_LOCAL_FALLBACK', 'true').lower() == 'true'
    
    @classmethod
    def get_data_source_info(cls):
        """データソース情報を取得"""
        if cls.GOOGLE_DRIVE_ENABLED and cls.GOOGLE_DRIVE_FOLDER_ID:
            return {
                'type': 'google_drive',
                'folder_id': cls.GOOGLE_DRIVE_FOLDER_ID,
                'fallback_enabled': cls.USE_LOCAL_FALLBACK
            }
        else:
            return {
                'type': 'local',
                'data_dir': str(cls.LOCAL_DATA_DIR),
                'exists': cls.LOCAL_DATA_DIR.exists()
            }
    
    @classmethod
    def validate_google_drive_config(cls):
        """Google Drive設定の検証"""
        if not cls.GOOGLE_DRIVE_ENABLED:
            return False, "Google Drive機能が無効化されています"
        
        if not cls.GOOGLE_DRIVE_FOLDER_ID:
            return False, "Google DriveフォルダIDが設定されていません"
        
        # サービスアカウントファイルまたは環境変数の確認
        if not os.path.exists(cls.GOOGLE_SERVICE_ACCOUNT_FILE) and 'GOOGLE_SERVICE_ACCOUNT' not in os.environ:
            return False, "サービスアカウント認証情報が見つかりません"
        
        return True, "設定は正常です"

def get_config():
    """設定インスタンスを取得"""
    return Config() 