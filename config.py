#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
設定管理モジュール

環境変数とStreamlit Secretsからの設定読み込みを管理します
"""

import os
import json
from pathlib import Path
from typing import Optional
import streamlit as st
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Config:
    """設定クラス"""
    
    def __init__(self):
        # Streamlit Secrets からの設定読み込みを試行
        self._load_from_streamlit_secrets()
        
        # Google Drive設定
        self.GOOGLE_DRIVE_ENABLED = self._get_bool('GOOGLE_DRIVE_ENABLED', True)
        self.GOOGLE_DRIVE_FOLDER_ID = self._get_env('GOOGLE_DRIVE_FOLDER_ID')
        self.GOOGLE_SERVICE_ACCOUNT_FILE = self._get_env('GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
        
        # 本番環境設定
        self.PRODUCTION_MODE = self._get_bool('PRODUCTION_MODE', False)
        self.USE_LOCAL_FALLBACK = self._get_bool('USE_LOCAL_FALLBACK', True)
        
        # ローカルデータディレクトリ
        self.LOCAL_DATA_DIR = Path(self._get_env('LOCAL_DATA_DIR', 'dataset'))
        
        # 環境変数からサービスアカウント情報を取得
        if 'GOOGLE_SERVICE_ACCOUNT' in os.environ:
            self.GOOGLE_SERVICE_ACCOUNT_FILE = None  # 環境変数を優先
    
    def _load_from_streamlit_secrets(self):
        """Streamlit Secrets から設定を読み込み"""
        try:
            if hasattr(st, 'secrets'):
                # 直接設定されたトップレベルのsecretsを処理
                for key in ['PRODUCTION_MODE', 'GOOGLE_DRIVE_ENABLED', 'USE_LOCAL_FALLBACK', 'GOOGLE_DRIVE_FOLDER_ID']:
                    if key in st.secrets:
                        os.environ[key] = str(st.secrets[key])
                
                # google_driveセクションを処理
                if 'google_drive' in st.secrets:
                    secrets = st.secrets['google_drive']
                    
                    # 環境変数として設定
                    for key, value in secrets.items():
                        if key == 'service_account' and isinstance(value, str):
                            # JSON文字列を環境変数に設定
                            os.environ['GOOGLE_SERVICE_ACCOUNT'] = value
                        else:
                            os.environ[key.upper()] = str(value)
                
        except Exception as e:
            # エラーログを出力（デバッグ用）
            print(f"Streamlit Secrets読み込みエラー: {e}")
            pass
    
    def _get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """環境変数を取得"""
        return os.getenv(key, default)
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """boolean型の環境変数を取得"""
        value = os.getenv(key, '').lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        else:
            return default

# グローバル設定インスタンス
_config = None

def get_config() -> Config:
    """設定インスタンスを取得"""
    global _config
    
    if _config is None:
        _config = Config()
    
    return _config

def get_data_source_info(config):
    """データソース情報を取得"""
    if config.GOOGLE_DRIVE_ENABLED and config.GOOGLE_DRIVE_FOLDER_ID:
        return {
            'type': 'google_drive',
            'folder_id': config.GOOGLE_DRIVE_FOLDER_ID,
            'fallback_enabled': config.USE_LOCAL_FALLBACK
        }
    else:
        return {
            'type': 'local',
            'data_dir': str(config.LOCAL_DATA_DIR),
            'exists': config.LOCAL_DATA_DIR.exists()
        }

def validate_google_drive_config(config):
    """Google Drive設定の検証"""
    if not config.GOOGLE_DRIVE_ENABLED:
        return False, "Google Drive機能が無効化されています"
    
    if not config.GOOGLE_DRIVE_FOLDER_ID:
        return False, "Google DriveフォルダIDが設定されていません"
    
    # サービスアカウントファイルまたは環境変数の確認
    if not os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_FILE) and 'GOOGLE_SERVICE_ACCOUNT' not in os.environ:
        return False, "サービスアカウント認証情報が見つかりません"
    
    return True, "設定は正常です" 