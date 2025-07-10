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

# Streamlit Cloud用の設定読み込み
def _load_streamlit_secrets():
    """Streamlit Secretsからの設定読み込み"""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'google_drive' in st.secrets:
            secrets = st.secrets.google_drive
            
            # 環境変数として設定（既存の環境変数を上書きしない）
            if not os.getenv('GOOGLE_DRIVE_ENABLED'):
                os.environ['GOOGLE_DRIVE_ENABLED'] = str(secrets.get("enabled", "false"))
            if not os.getenv('GOOGLE_DRIVE_FOLDER_ID'):
                os.environ['GOOGLE_DRIVE_FOLDER_ID'] = secrets.get("folder_id", "")
            if not os.getenv('PRODUCTION_MODE'):
                os.environ['PRODUCTION_MODE'] = str(secrets.get("production_mode", "false"))
            if not os.getenv('USE_LOCAL_FALLBACK'):
                os.environ['USE_LOCAL_FALLBACK'] = str(secrets.get("use_local_fallback", "true"))
            
            # サービスアカウント情報
            if "service_account" in secrets and not os.getenv('GOOGLE_SERVICE_ACCOUNT'):
                os.environ['GOOGLE_SERVICE_ACCOUNT'] = secrets.service_account
                
            print("✅ Streamlit Secrets から設定を読み込みました")
            
    except ImportError:
        # Streamlitが利用できない環境（開発環境など）
        pass
    except Exception as e:
        print(f"⚠️ Streamlit Secrets読み込みエラー: {e}")

# Streamlit Secrets読み込み実行
_load_streamlit_secrets()

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
    
    # 本番環境での強制モード（Google Driveのみ使用）
    PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'
    
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