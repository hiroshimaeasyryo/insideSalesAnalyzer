#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
設定管理モジュール

Zipファイルアップロード機能に特化した設定管理
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

class Config:
    """設定クラス"""
    
    def __init__(self):
        # アプリケーション設定
        self.APP_NAME = "インサイドセールス分析ダッシュボード"
        self.APP_VERSION = "2.0.0"
        
        # ファイルアップロード設定
        self.MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
        self.ALLOWED_EXTENSIONS = {'.zip'}
        
        # セッション設定
        self.SESSION_TIMEOUT = 3600  # 1時間
        
        # データ処理設定
        self.TEMP_DIR = Path(self._get_env('TEMP_DIR', '/tmp'))
        self.CACHE_ENABLED = self._get_bool('CACHE_ENABLED', True)
        self.CACHE_TTL = int(self._get_env('CACHE_TTL', '1800'))  # 30分
        
        # セキュリティ設定
        self.SECRET_KEY = self._get_env('SECRET_KEY', 'your-secret-key-here')
        
        # 対応ファイル形式
        self.SUPPORTED_FILE_PATTERNS = [
            '基本分析_YYYY-MM.json',
            '詳細分析_YYYY-MM.json',
            '月次サマリー_YYYY-MM.json',
            '定着率分析_YYYY-MM.json'
        ]
    
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
    
    def validate_file_upload(self, filename: str, file_size: int) -> tuple[bool, str]:
        """ファイルアップロードの検証"""
        # ファイルサイズチェック
        if file_size > self.MAX_FILE_SIZE:
            return False, f"ファイルサイズが大きすぎます（最大{self.MAX_FILE_SIZE // (1024*1024)}MB）"
        
        # ファイル拡張子チェック
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"対応していないファイル形式です（対応形式: {', '.join(self.ALLOWED_EXTENSIONS)}）"
        
        return True, "ファイルは正常です"

# グローバル設定インスタンス
_config = None

def get_config() -> Config:
    """設定インスタンスを取得"""
    global _config
    
    if _config is None:
        _config = Config()
    
    return _config

def get_app_info():
    """アプリケーション情報を取得"""
    config = get_config()
    return {
        'name': config.APP_NAME,
        'version': config.APP_VERSION,
        'max_file_size': config.MAX_FILE_SIZE,
        'supported_extensions': list(config.ALLOWED_EXTENSIONS),
        'supported_patterns': config.SUPPORTED_FILE_PATTERNS
    } 