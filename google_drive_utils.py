#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Drive ユーティリティモジュール

Google DriveからJSONファイルを読み込むための関数群
"""

import json
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
import io
import streamlit as st

class GoogleDriveClient:
    """Google Drive API クライアント"""
    
    def __init__(self, service_account_file=None, folder_id=None):
        """
        初期化
        
        Args:
            service_account_file (str): サービスアカウントJSONファイルのパス
            folder_id (str): 読み込み対象のGoogle DriveフォルダID
        """
        self.service_account_file = service_account_file or 'service_account.json'
        self.folder_id = folder_id
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Google Drive APIの認証"""
        try:
            # 環境変数からサービスアカウント情報を取得（Streamlit Cloud対応）
            if 'GOOGLE_SERVICE_ACCOUNT' in os.environ:
                import json
                service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT'])
                credentials = Credentials.from_service_account_info(
                    service_account_info,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            # ローカルファイルから読み込み
            elif os.path.exists(self.service_account_file):
                credentials = Credentials.from_service_account_file(
                    self.service_account_file,
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            else:
                raise FileNotFoundError(f"サービスアカウントファイルが見つかりません: {self.service_account_file}")
            
            self.service = build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            raise
    
    def list_files_in_folder(self, folder_id=None, file_extension='.json'):
        """
        指定フォルダ内のファイル一覧を取得
        
        Args:
            folder_id (str): フォルダID（Noneの場合はself.folder_idを使用）
            file_extension (str): ファイル拡張子フィルタ
            
        Returns:
            list: ファイル情報のリスト
        """
        if not self.service:
            raise RuntimeError("Google Drive APIが認証されていません")
        
        target_folder = folder_id or self.folder_id
        if not target_folder:
            raise ValueError("フォルダIDが指定されていません")
        
        try:
            # フォルダ内のファイルを検索
            query = f"parents in '{target_folder}' and trashed=false"
            if file_extension:
                query += f" and name contains '{file_extension}'"
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, modifiedTime, size)"
            ).execute()
            
            files = results.get('files', [])
            
            return files
            
        except Exception as e:
            return []
    
    def download_file_content(self, file_id):
        """
        ファイルの内容を文字列として取得
        
        Args:
            file_id (str): ファイルID
            
        Returns:
            str: ファイルの内容
        """
        if not self.service:
            raise RuntimeError("Google Drive APIが認証されていません")
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content.seek(0)
            content = file_content.read().decode('utf-8')
            
            return content
            
        except Exception as e:
            raise
    
    def load_json_file(self, filename):
        """
        指定されたJSONファイルを読み込み
        
        Args:
            filename (str): ファイル名
            
        Returns:
            dict: JSONデータ
        """
        try:
            files = self.list_files_in_folder()
            
            # ファイル名でマッチング
            target_file = None
            for file in files:
                if file['name'] == filename:
                    target_file = file
                    break
            
            if not target_file:
                raise FileNotFoundError(f"ファイルが見つかりません: {filename}")
            
            content = self.download_file_content(target_file['id'])
            data = json.loads(content)
            
            return data
            
        except Exception as e:
            raise

# グローバルクライアントインスタンス
_drive_client = None

def get_drive_client(service_account_file=None, folder_id=None):
    """
    Google Driveクライアントのシングルトンインスタンスを取得
    
    Args:
        service_account_file (str): サービスアカウントJSONファイルのパス
        folder_id (str): Google DriveフォルダID
        
    Returns:
        GoogleDriveClient: クライアントインスタンス
    """
    global _drive_client
    
    if _drive_client is None:
        _drive_client = GoogleDriveClient(service_account_file, folder_id)
    
    return _drive_client

def load_json_from_drive(filename, folder_id=None, service_account_file=None):
    """
    Google DriveからJSONファイルを読み込み
    
    Args:
        filename (str): ファイル名
        folder_id (str): Google DriveフォルダID
        service_account_file (str): サービスアカウントJSONファイルのパス
        
    Returns:
        dict: JSONデータ
    """
    client = get_drive_client(service_account_file, folder_id)
    return client.load_json_file(filename)

def test_connection(folder_id=None, service_account_file=None):
    """
    Google Drive接続テスト
    
    Args:
        folder_id (str): Google DriveフォルダID
        service_account_file (str): サービスアカウントJSONファイルのパス
        
    Returns:
        bool: 接続成功の場合True
    """
    try:
        client = get_drive_client(service_account_file, folder_id)
        files = client.list_files_in_folder()
        return True
    except Exception as e:
        return False 