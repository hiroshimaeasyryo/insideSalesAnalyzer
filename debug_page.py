#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Streamlit Cloud用デバッグページ

本番環境での設定状況とGoogle Drive接続をデバッグ
"""

import streamlit as st
import os
import sys
from pathlib import Path
import traceback
import json
from datetime import datetime

def debug_page():
    """デバッグページのメイン関数"""
    st.title("🔍 システムデバッグ情報")
    st.markdown("---")
    
    # デバッグ情報をタブで整理
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 環境情報", 
        "📋 設定確認", 
        "🔌 接続テスト", 
        "📊 データテスト"
    ])
    
    with tab1:
        show_environment_info()
    
    with tab2:
        show_configuration()
    
    with tab3:
        show_connection_test()
    
    with tab4:
        show_data_test()

def show_environment_info():
    """環境情報を表示"""
    st.subheader("🌐 実行環境情報")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📍 Python実行環境**")
        st.code(f"""
Python実行パス: {sys.executable}
Pythonバージョン: {sys.version}
現在のディレクトリ: {os.getcwd()}
        """)
    
    with col2:
        st.write("**📂 ファイル存在確認**")
        files_to_check = [
            'service_account.json',
            '.env',
            'dataset/',
            'config.py',
            'google_drive_utils.py',
            'data_loader.py'
        ]
        
        status_text = ""
        for file_path in files_to_check:
            path = Path(file_path)
            if path.exists():
                if path.is_dir():
                    file_count = len(list(path.glob('*.json')))
                    status_text += f"✅ {file_path} ({file_count} JSONファイル)\n"
                else:
                    status_text += f"✅ {file_path}\n"
            else:
                status_text += f"❌ {file_path}\n"
        
        st.code(status_text)

def show_configuration():
    """設定情報を表示"""
    st.subheader("📋 Google Drive設定確認")
    
    # 環境変数の確認
    st.write("**🔧 環境変数**")
    google_drive_vars = [
        'GOOGLE_DRIVE_ENABLED',
        'GOOGLE_DRIVE_FOLDER_ID', 
        'GOOGLE_SERVICE_ACCOUNT_FILE',
        'GOOGLE_SERVICE_ACCOUNT',
        'USE_LOCAL_FALLBACK',
        'PRODUCTION_MODE'
    ]
    
    config_data = {}
    for var in google_drive_vars:
        value = os.getenv(var)
        if value:
            if var == 'GOOGLE_SERVICE_ACCOUNT':
                config_data[var] = f"設定済み ({len(value)} 文字)"
            elif var == 'GOOGLE_DRIVE_FOLDER_ID':
                config_data[var] = f"{value[:8]}..." if len(value) > 8 else value
            else:
                config_data[var] = value
        else:
            config_data[var] = "❌ 未設定"
    
    st.json(config_data)
    
    # Streamlit Secretsの確認
    st.write("**🔐 Streamlit Secrets**")
    try:
        if hasattr(st, 'secrets') and 'google_drive' in st.secrets:
            secrets_info = {}
            for key in st.secrets.google_drive:
                if key == 'service_account':
                    secrets_info[key] = f"設定済み ({len(st.secrets.google_drive[key])} 文字)"
                elif key == 'folder_id':
                    value = st.secrets.google_drive[key]
                    secrets_info[key] = f"{value[:8]}..." if len(value) > 8 else value
                else:
                    secrets_info[key] = st.secrets.google_drive[key]
            st.json(secrets_info)
            st.success("✅ Streamlit Secrets設定済み")
        else:
            st.info("ℹ️ Streamlit Secrets未設定（ローカル環境では正常）")
    except Exception as e:
        st.info(f"ℹ️ Streamlit Secrets未設定（ローカル環境では正常）: {str(e)[:100]}")
    
    # 設定読み込みテスト
    st.write("**⚙️ 設定読み込みテスト**")
    try:
        from config import get_config
        config = get_config()
        
        config_summary = {
            "GOOGLE_DRIVE_ENABLED": config.GOOGLE_DRIVE_ENABLED,
            "フォルダID設定": "設定済み" if config.GOOGLE_DRIVE_FOLDER_ID else "未設定",
            "PRODUCTION_MODE": config.PRODUCTION_MODE,
            "USE_LOCAL_FALLBACK": config.USE_LOCAL_FALLBACK,
        }
        
        st.success("✅ 設定読み込み成功")
        st.json(config_summary)
        
    except Exception as e:
        st.error(f"❌ 設定読み込みエラー: {e}")
        st.code(traceback.format_exc())

def show_connection_test():
    """Google Drive接続テスト"""
    st.subheader("🔌 Google Drive接続テスト")
    
    if st.button("🔄 接続テストを実行", type="primary"):
        with st.spinner("接続テスト実行中..."):
            try:
                from config import get_config
                config = get_config()
                
                if not config.GOOGLE_DRIVE_ENABLED:
                    st.warning("Google Drive が無効化されています")
                    return
                
                if not config.GOOGLE_DRIVE_FOLDER_ID:
                    st.error("Google Drive フォルダID が設定されていません")
                    return
                
                # Google Drive接続テスト
                from google_drive_utils import GoogleDriveClient
                
                client = GoogleDriveClient(
                    service_account_file=config.GOOGLE_SERVICE_ACCOUNT_FILE
                )
                
                st.success("✅ Google Drive API認証成功")
                
                # フォルダアクセステスト
                files = client.list_files(folder_id=config.GOOGLE_DRIVE_FOLDER_ID)
                st.success(f"✅ フォルダアクセス成功: {len(files)} ファイル検出")
                
                # ファイル一覧表示
                if files:
                    st.write("**📁 検出されたファイル**")
                    file_list = []
                    for file_info in files[:10]:  # 最初の10ファイルのみ表示
                        file_list.append({
                            "ファイル名": file_info['name'],
                            "更新日": file_info.get('modifiedTime', 'N/A')
                        })
                    st.dataframe(file_list)
                    
                    if len(files) > 10:
                        st.info(f"他 {len(files) - 10} ファイル...")
                
            except Exception as e:
                st.error(f"❌ 接続テスト失敗: {e}")
                st.code(traceback.format_exc())

def show_data_test():
    """データ読み込みテスト"""
    st.subheader("📊 データ読み込みテスト")
    
    # 月選択
    months = [
        "2025-07", "2025-06", "2025-05", "2025-04", "2025-03",
        "2025-02", "2025-01", "2024-12", "2024-11", "2024-10"
    ]
    
    selected_month = st.selectbox("テストする月を選択", months)
    
    if st.button("📥 データ読み込みテスト", type="primary"):
        with st.spinner(f"{selected_month} のデータ読み込み中..."):
            try:
                from data_loader import DataLoader
                loader = DataLoader()
                
                # 基本分析データ
                st.write("**📈 基本分析データ**")
                basic_data = loader.load_basic_analysis(selected_month)
                if basic_data:
                    st.success(f"✅ 基本分析データ読み込み成功 ({len(basic_data)} レコード)")
                    
                    # データサンプル表示
                    if isinstance(basic_data, list) and len(basic_data) > 0:
                        sample = basic_data[0]
                        st.json(sample)
                else:
                    st.error("❌ 基本分析データ読み込み失敗")
                
                # 詳細分析データ
                st.write("**📊 詳細分析データ**")
                detailed_data = loader.load_detailed_analysis(selected_month)
                if detailed_data:
                    st.success(f"✅ 詳細分析データ読み込み成功")
                    
                    # データ構造表示
                    if isinstance(detailed_data, dict):
                        st.write("データ構造:")
                        structure = {key: type(value).__name__ for key, value in detailed_data.items()}
                        st.json(structure)
                else:
                    st.error("❌ 詳細分析データ読み込み失敗")
                
                # 月次サマリーデータ
                st.write("**📋 月次サマリーデータ**")
                summary_data = loader.load_monthly_summary(selected_month)
                if summary_data:
                    st.success(f"✅ 月次サマリーデータ読み込み成功")
                    if isinstance(summary_data, dict):
                        st.json(summary_data)
                else:
                    st.error("❌ 月次サマリーデータ読み込み失敗")
                
            except Exception as e:
                st.error(f"❌ データ読み込みエラー: {e}")
                st.code(traceback.format_exc())
                
                # より詳細なエラー情報
                st.write("**🔍 詳細エラー情報**")
                st.write(f"エラータイプ: {type(e).__name__}")
                st.write(f"エラーメッセージ: {str(e)}")

def show_logs():
    """ログ情報の表示"""
    st.subheader("📝 システムログ")
    
    # Streamlit Cloud のログは直接アクセスできないため、
    # アプリケーション内でキャプチャしたログを表示
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []
    
    if st.session_state.debug_logs:
        for log in st.session_state.debug_logs:
            st.text(log)
    else:
        st.info("まだログが記録されていません")

if __name__ == "__main__":
    debug_page() 