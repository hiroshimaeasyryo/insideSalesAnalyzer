#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データローダーモジュール

Google DriveまたはローカルファイルシステムからJSONデータを読み込みます
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import streamlit as st

from config import get_config
from google_drive_utils import load_json_from_drive, test_connection

class DataLoader:
    """統合データローダークラス"""
    
    def __init__(self):
        self.config = get_config()
        self._drive_available = None
    
    def is_drive_available(self) -> bool:
        """Google Drive接続が利用可能かチェック"""
        if self._drive_available is None:
            if not self.config.GOOGLE_DRIVE_ENABLED:
                self._drive_available = False
            else:
                try:
                    self._drive_available = test_connection(
                        folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                        service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE
                    )
                except Exception as e:
                    print(f"Google Drive接続テスト失敗: {e}")
                    self._drive_available = False
        
        return self._drive_available
    
    def load_json_file(self, filename: str) -> Optional[Dict[Any, Any]]:
        """
        JSONファイルを読み込み（Google Drive優先、ローカルフォールバック）
        
        Args:
            filename (str): ファイル名
            
        Returns:
            Optional[Dict]: JSONデータ（読み込み失敗時はNone）
        """
        # 本番環境モードの場合はGoogle Driveのみ使用
        if self.config.PRODUCTION_MODE:
            if not self.config.GOOGLE_DRIVE_ENABLED or not self.config.GOOGLE_DRIVE_FOLDER_ID:
                raise RuntimeError(
                    "本番環境モードではGoogle Drive設定が必須です。"
                    "GOOGLE_DRIVE_ENABLED=true および GOOGLE_DRIVE_FOLDER_ID を設定してください。"
                )
            
            if not self.is_drive_available():
                raise RuntimeError(
                    "本番環境モードでGoogle Drive接続に失敗しました。"
                    "サービスアカウント認証情報とネットワーク接続を確認してください。"
                )
            
            # Google Driveからのみ読み込み（フォールバックなし）
            print(f"🌐 [本番モード] Google Driveから読み込み中: {filename}")
            data = load_json_from_drive(
                filename,
                folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE
            )
            print(f"✅ [本番モード] Google Drive読み込み成功: {filename}")
            return data
        
        # 1. Google Driveから読み込みを試行
        if self.is_drive_available():
            try:
                print(f"🌐 Google Driveから読み込み中: {filename}")
                data = load_json_from_drive(
                    filename,
                    folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                    service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE
                )
                print(f"✅ Google Drive読み込み成功: {filename}")
                return data
            except Exception as e:
                print(f"⚠️ Google Drive読み込み失敗: {filename} - {e}")
                if not self.config.USE_LOCAL_FALLBACK:
                    raise
        
        # 2. ローカルファイルシステムから読み込み（開発環境のみ）
        if not self.config.USE_LOCAL_FALLBACK:
            raise RuntimeError(f"Google Drive読み込みに失敗し、ローカルフォールバックが無効化されています: {filename}")
        
        return self._load_local_file(filename)
    
    def _load_local_file(self, filename: str) -> Optional[Dict[Any, Any]]:
        """ローカルファイルシステムからJSONファイルを読み込み"""
        local_path = self.config.LOCAL_DATA_DIR / filename
        
        try:
            if not local_path.exists():
                print(f"❌ ローカルファイルが見つかりません: {local_path}")
                return None
            
            print(f"📁 ローカルファイルから読み込み中: {filename}")
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ ローカル読み込み成功: {filename}")
            return data
            
        except Exception as e:
            print(f"❌ ローカルファイル読み込みエラー ({filename}): {e}")
            return None
    
    def load_analysis_data(self, month: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
        """
        指定月の分析データをすべて読み込み
        
        Args:
            month (str): 月（YYYY-MM形式）
            
        Returns:
            Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]: 
                (基本分析データ, 詳細分析データ, 月次サマリーデータ)
        """
        basic_data = self.load_json_file(f'基本分析_{month}.json')
        detail_data = self.load_json_file(f'詳細分析_{month}.json')
        summary_data = self.load_json_file(f'月次サマリー_{month}.json')
        
        return basic_data, detail_data, summary_data
    
    def load_retention_data(self, month: str) -> Optional[Dict]:
        """
        指定月の定着率分析データを読み込み
        
        Args:
            month (str): 月（YYYY-MM形式）
            
        Returns:
            Optional[Dict]: 定着率分析データ
        """
        return self.load_json_file(f'定着率分析_{month}.json')
    
    def get_available_months(self) -> list:
        """
        利用可能な月のリストを取得
        
        Returns:
            list: 利用可能な月のリスト（YYYY-MM形式）
        """
        months = set()
        
        # Google Driveから取得
        if self.is_drive_available():
            try:
                from google_drive_utils import get_drive_client
                client = get_drive_client(
                    service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE,
                    folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID
                )
                files = client.list_files_in_folder()
                
                for file in files:
                    filename = file['name']
                    # 基本分析ファイルから月を抽出
                    if filename.startswith('基本分析_') and filename.endswith('.json'):
                        month = filename.replace('基本分析_', '').replace('.json', '')
                        months.add(month)
                        
            except Exception as e:
                print(f"Google Driveからの月リスト取得失敗: {e}")
        
        # ローカルファイルから取得（フォールバック）
        if self.config.LOCAL_DATA_DIR.exists():
            for file_path in self.config.LOCAL_DATA_DIR.glob('基本分析_*.json'):
                filename = file_path.name
                month = filename.replace('基本分析_', '').replace('.json', '')
                months.add(month)
        
        return sorted(list(months), reverse=True)
    
    def get_data_source_status(self) -> Dict[str, Any]:
        """データソースの状態を取得"""
        status = {
            'google_drive': {
                'enabled': self.config.GOOGLE_DRIVE_ENABLED,
                'available': self.is_drive_available(),
                'folder_id': self.config.GOOGLE_DRIVE_FOLDER_ID
            },
            'local': {
                'path': str(self.config.LOCAL_DATA_DIR),
                'exists': self.config.LOCAL_DATA_DIR.exists(),
                'fallback_enabled': self.config.USE_LOCAL_FALLBACK
            },
            'active_source': 'google_drive' if self.is_drive_available() else 'local'
        }
        
        return status

# グローバルローダーインスタンス
_data_loader = None

def get_data_loader() -> DataLoader:
    """データローダーのシングルトンインスタンスを取得"""
    global _data_loader
    
    if _data_loader is None:
        _data_loader = DataLoader()
    
    return _data_loader

# 互換性のための関数
def load_data(month: str):
    """
    指定月のデータを読み込み（互換性のための関数）
    
    Args:
        month (str): 月（YYYY-MM形式）
        
    Returns:
        Tuple: (基本分析データ, 詳細分析データ, 月次サマリーデータ)
    """
    loader = get_data_loader()
    return loader.load_analysis_data(month)

def load_retention_data(month: str):
    """
    指定月の定着率分析データを読み込み（互換性のための関数）
    
    Args:
        month (str): 月（YYYY-MM形式）
        
    Returns:
        Optional[Dict]: 定着率分析データ
    """
    loader = get_data_loader()
    return loader.load_retention_data(month) 