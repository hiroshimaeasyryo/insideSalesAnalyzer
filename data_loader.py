#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データローダーモジュール

Google DriveまたはローカルファイルシステムからJSONデータを読み込みます
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import streamlit as st
import concurrent.futures
import threading
from functools import lru_cache

from config import get_config
from google_drive_utils import load_json_from_drive, test_connection

class DataLoader:
    """統合データローダークラス"""
    
    def __init__(self):
        self.config = get_config()
        self._drive_available = None
        self._file_cache = {}  # メモリキャッシュ
        self._cache_lock = threading.Lock()
    
    @lru_cache(maxsize=1)
    def is_drive_available(self) -> bool:
        """Google Drive接続が利用可能かチェック（LRUキャッシュ付き）"""
        if not self.config.GOOGLE_DRIVE_ENABLED:
            return False
        else:
            try:
                return test_connection(
                    folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                    service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE
                )
            except Exception as e:
                return False
    
    def test_drive_connection_fresh(self) -> tuple:
        """Google Drive接続を強制的に再テスト（キャッシュなし）"""
        if not self.config.GOOGLE_DRIVE_ENABLED or not self.config.GOOGLE_DRIVE_FOLDER_ID:
            return False, "Google Drive設定が無効"
        
        try:
            from google_drive_utils import get_drive_client
            # 強制リフレッシュで新しいクライアントを作成
            client = get_drive_client(
                service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE,
                folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                force_refresh=True
            )
            files = client.list_files_in_folder()
            return True, f"成功 ({len(files)}ファイル)"
        except Exception as e:
            return False, str(e)
    
    def _get_cache_key(self, filename: str) -> str:
        """キャッシュキーを生成"""
        return f"{filename}_{self.config.GOOGLE_DRIVE_FOLDER_ID}"
    
    def _load_file_with_cache(self, filename: str) -> Optional[Dict[Any, Any]]:
        """キャッシュ付きファイル読み込み"""
        cache_key = self._get_cache_key(filename)
        
        # キャッシュから確認
        with self._cache_lock:
            if cache_key in self._file_cache:
                return self._file_cache[cache_key]
        
        # ファイルを読み込み
        data = self._load_single_file(filename)
        
        # キャッシュに保存
        if data is not None:
            with self._cache_lock:
                self._file_cache[cache_key] = data
        
        return data
    
    def _load_single_file(self, filename: str) -> Optional[Dict[Any, Any]]:
        """単一ファイルの読み込み（並列処理用）"""
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
            data = load_json_from_drive(
                filename,
                folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE
            )
            return data
        
        # 1. Google Driveから読み込みを試行
        if self.is_drive_available():
            try:
                data = load_json_from_drive(
                    filename,
                    folder_id=self.config.GOOGLE_DRIVE_FOLDER_ID,
                    service_account_file=self.config.GOOGLE_SERVICE_ACCOUNT_FILE
                )
                return data
            except Exception as e:
                if not self.config.USE_LOCAL_FALLBACK:
                    raise
        
        # 2. ローカルファイルシステムから読み込み（開発環境のみ）
        if not self.config.USE_LOCAL_FALLBACK:
            raise RuntimeError(f"Google Drive読み込みに失敗し、ローカルフォールバックが無効化されています: {filename}")
        
        return self._load_local_file(filename)

    def load_json_file(self, filename: str) -> Optional[Dict[Any, Any]]:
        """
        JSONファイルを読み込み（キャッシュ付き）
        
        Args:
            filename (str): ファイル名
            
        Returns:
            Optional[Dict]: JSONデータ（読み込み失敗時はNone）
        """
        return self._load_file_with_cache(filename)
    
    def load_multiple_files_parallel(self, filenames: List[str], max_workers: int = 3) -> Dict[str, Optional[Dict]]:
        """
        複数ファイルを並列で読み込み
        
        Args:
            filenames (List[str]): ファイル名のリスト
            max_workers (int): 最大並列数
            
        Returns:
            Dict[str, Optional[Dict]]: ファイル名をキーとする結果辞書
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 並列実行を開始
            future_to_filename = {
                executor.submit(self._load_file_with_cache, filename): filename 
                for filename in filenames
            }
            
            # 結果を収集
            for future in concurrent.futures.as_completed(future_to_filename):
                filename = future_to_filename[future]
                try:
                    data = future.result()
                    results[filename] = data
                except Exception as e:
                    results[filename] = None
        
        return results
    
    def _load_local_file(self, filename: str) -> Optional[Dict[Any, Any]]:
        """ローカルファイルシステムからJSONファイルを読み込み"""
        local_path = self.config.LOCAL_DATA_DIR / filename
        
        try:
            if not local_path.exists():
                return None
            
            with open(local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            return None
    
    def load_analysis_data(self, month: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
        """
        指定月の分析データをすべて読み込み（並列処理版）
        
        Args:
            month (str): 月（YYYY-MM形式）
            
        Returns:
            Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]: 
                (基本分析データ, 詳細分析データ, 月次サマリーデータ)
        """
        filenames = [
            f'基本分析_{month}.json',
            f'詳細分析_{month}.json',
            f'月次サマリー_{month}.json'
        ]
        
        # 並列読み込み
        results = self.load_multiple_files_parallel(filenames)
        
        return (
            results.get(filenames[0]),
            results.get(filenames[1]), 
            results.get(filenames[2])
        )
    
    def load_retention_data(self, month: str) -> Optional[Dict]:
        """
        指定月の定着率分析データを読み込み
        
        Args:
            month (str): 月（YYYY-MM形式）
            
        Returns:
            Optional[Dict]: 定着率分析データ
        """
        return self.load_json_file(f'定着率分析_{month}.json')
    
    def clear_cache(self):
        """キャッシュをクリア"""
        with self._cache_lock:
            self._file_cache.clear()
        
        # LRUキャッシュもクリア
        self.is_drive_available.cache_clear()
        
        # Google Driveクライアントもリセット
        try:
            from google_drive_utils import reset_drive_client
            reset_drive_client()
        except ImportError:
            pass
    
    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュ情報を取得"""
        with self._cache_lock:
            cache_size = len(self._file_cache)
            cache_keys = list(self._file_cache.keys())
        
        return {
            'cache_size': cache_size,
            'cached_files': cache_keys,
            'drive_check_cache': self.is_drive_available.cache_info()._asdict()
        }
    
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
                pass
        
        # ローカルファイルから取得（フォールバック）
        if self.config.LOCAL_DATA_DIR.exists():
            for file_path in self.config.LOCAL_DATA_DIR.glob('基本分析_*.json'):
                filename = file_path.name
                month = filename.replace('基本分析_', '').replace('.json', '')
                months.add(month)
        
        return sorted(list(months), reverse=True)
    
    def get_data_source_status(self) -> Dict[str, Any]:
        """データソースの状態を取得"""
        cache_info = self.get_cache_info()
        
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
            'cache': cache_info,
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