#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
データローダーモジュール

ZipファイルアップロードからJSONデータを読み込みます
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import zipfile
import tempfile
from functools import lru_cache

from config import get_config

class ZipDataLoader:
    """Zipファイルデータローダークラス"""
    
    def __init__(self):
        self.config = get_config()
        self._json_data = {}
        self._available_months = []
        self._uploaded_file_name = None
    
    def load_from_zip(self, zip_file) -> bool:
        """
        ZipファイルからJSONデータを読み込み
        
        Args:
            zip_file: アップロードされたZipファイル
            
        Returns:
            bool: 読み込み成功時True
        """
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                # 一時ディレクトリを作成
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Zipファイルを展開
                    zip_ref.extractall(temp_dir)
                    
                    # JSONファイルを検索
                    json_files = {}
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith('.json'):
                                file_path = os.path.join(root, file)
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        json_files[file] = data
                                except Exception as e:
                                    print(f"JSONファイル読み込みエラー {file}: {e}")
                    
                    if not json_files:
                        print("警告: JSONファイルが見つかりませんでした")
                        return False
                    
                    self._json_data = json_files
                    self._available_months = self._extract_available_months(json_files)
                    self._uploaded_file_name = getattr(zip_file, 'filename', 'unknown.zip')
                    
                    print(f"✅ {len(json_files)}個のJSONファイルを読み込みました")
                    print(f"利用可能な月: {', '.join(self._available_months)}")
                    
                    return True
                    
        except Exception as e:
            print(f"Zipファイル処理エラー: {e}")
            return False
    
    def _extract_available_months(self, json_data: Dict[str, Any]) -> List[str]:
        """JSONデータから利用可能な月を抽出"""
        months = set()
        for filename in json_data.keys():
            # ファイル名から月を抽出（例: 基本分析_2024-09.json）
            if '_' in filename and '.json' in filename:
                parts = filename.split('_')
                if len(parts) >= 2:
                    month_part = parts[-1].replace('.json', '')
                    if len(month_part) == 7 and month_part[4] == '-':  # YYYY-MM形式
                        months.add(month_part)
        return sorted(list(months), reverse=True)
    
    def get_available_months(self) -> List[str]:
        """利用可能な月のリストを取得"""
        return self._available_months
    
    def get_uploaded_file_name(self) -> Optional[str]:
        """アップロードされたファイル名を取得"""
        return self._uploaded_file_name
    
    def get_json_data(self) -> Dict[str, Any]:
        """読み込まれたJSONデータを取得"""
        return self._json_data
    
    def load_analysis_data(self, month: str) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
        """
        指定月の分析データを読み込み
        
        Args:
            month (str): 月（YYYY-MM形式）
            
        Returns:
            Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]: 
                (基本分析データ, 詳細分析データ, 月次サマリーデータ)
        """
        basic_data = None
        detail_data = None
        summary_data = None
        
        for filename, data in self._json_data.items():
            if f'基本分析_{month}.json' in filename:
                basic_data = data
            elif f'詳細分析_{month}.json' in filename:
                detail_data = data
            elif f'月次サマリー_{month}.json' in filename:
                summary_data = data
        
        return basic_data, detail_data, summary_data
    
    def load_retention_data(self, month: str) -> Optional[Dict]:
        """
        指定月の定着率分析データを読み込み
        
        Args:
            month (str): 月（YYYY-MM形式）
            
        Returns:
            Optional[Dict]: 定着率分析データ
        """
        for filename, data in self._json_data.items():
            if f'定着率分析_{month}.json' in filename:
                return data
        return None
    
    def get_data_summary(self) -> Dict[str, Any]:
        """データサマリー情報を取得"""
        return {
            'total_files': len(self._json_data),
            'available_months': self._available_months,
            'uploaded_file_name': self._uploaded_file_name,
            'file_types': list(set([filename.split('_')[0] for filename in self._json_data.keys() if '_' in filename]))
        }
    
    def clear_data(self):
        """データをクリア"""
        self._json_data = {}
        self._available_months = []
        self._uploaded_file_name = None

# グローバルデータローダーインスタンス
_data_loader = None

def get_data_loader() -> ZipDataLoader:
    """データローダーインスタンスを取得"""
    global _data_loader
    
    if _data_loader is None:
        _data_loader = ZipDataLoader()
    
    return _data_loader

def load_data(month: str):
    """指定月のデータを読み込み（後方互換性のため）"""
    loader = get_data_loader()
    return loader.load_analysis_data(month)

def load_retention_data(month: str):
    """指定月の定着率データを読み込み（後方互換性のため）"""
    loader = get_data_loader()
    return loader.load_retention_data(month) 