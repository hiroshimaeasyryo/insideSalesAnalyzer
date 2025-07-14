import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# 新しいデータローダーをインポート
from data_loader import get_data_loader
from config import get_config

# ページ設定
st.set_page_config(
    page_title="インサイドセールス_ダッシュボード",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 認証設定
credentials = {
    "usernames": {
        "admin": {
            "name": "管理者",
            "password": "admin123"
        },
        "user": {
            "name": "一般ユーザー",
            "password": "user123"
        }
    }
}

# 認証オブジェクトを作成（新しいAPI）
authenticator = stauth.Authenticate(
    credentials,
    "dashboard",
    "auth_key",
    cookie_expiry_days=30
)

# ログインフォームをmainエリアに表示
authenticator.login(location='main', key='ログイン')

# 認証状態をセッションから取得
authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

if authentication_status == False:
    st.error('❌ ユーザー名/パスワードが間違っています')
elif authentication_status == None:
    st.warning('⚠️ ユーザー名とパスワードを入力してください')
elif authentication_status:
    # 認証後のメインアプリ
    st.success(f"ようこそ {name} さん")
    
    # サイドバーにログアウトボタン
    with st.sidebar:
        st.title("🔐 認証")
        authenticator.logout('ログアウト', 'sidebar')
        st.write(f'ようこそ **{name}** さん')
        
        st.divider()
        
        # 分析タイプ選択
        st.subheader("📊 分析タイプ")
        analysis_options = {
            "📊 月次サマリー分析": "basic_analysis",
            "📈 定着率分析": "retention_analysis",
            "📋 単月詳細データ": "monthly_detail",
            "📁 ファイルアップロード": "file_upload"
        }
        
        analysis_type = st.selectbox(
            "分析タイプを選択",
            list(analysis_options.keys())
        )
        
        selected_analysis = analysis_options[analysis_type]
        
        # ファイルアップロードページ
        if selected_analysis == "file_upload":
            st.title("📁 ファイルアップロード")
            st.markdown("分析用のJSONファイルをアップロードしてください")
            
            # データローダーを初期化
            loader = get_data_loader()
            config = get_config()
            
            # 現在のファイル状況を表示
            st.subheader("📊 現在のデータ状況")
            data_status = loader.get_data_source_status()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**アップロード済みファイル**")
                if data_status['uploaded_files']:
                    for file in data_status['uploaded_files']:
                        st.write(f"- {file}")
                else:
                    st.write("なし")
            
            with col2:
                st.write("**ローカルファイル**")
                if data_status['local_files']:
                    for file in data_status['local_files'][:5]:  # 最初の5個のみ表示
                        st.write(f"- {file}")
                    if len(data_status['local_files']) > 5:
                        st.write(f"...他{len(data_status['local_files']) - 5}個")
                else:
                    st.write("なし")
            
            st.write(f"**利用可能な月**: {data_status['available_months']}")
            
            st.divider()
            
            # ファイルアップロード機能
            st.subheader("📤 ファイルアップロード")
            
            # アップロード方法の選択
            upload_method = st.radio(
                "アップロード方法を選択",
                ["個別JSONファイル", "ZIPファイル一括アップロード"]
            )
            
            if upload_method == "個別JSONファイル":
                uploaded_files = st.file_uploader(
                    "JSONファイルを選択",
                    type=['json'],
                    accept_multiple_files=True,
                    help="複数ファイルを同時に選択可能です"
                )
                
                if uploaded_files:
                    st.write(f"選択されたファイル: {len(uploaded_files)}個")
                    
                    # ファイル一覧を表示
                    for file in uploaded_files:
                        st.write(f"- {file.name} ({file.size:,} bytes)")
                    
                    if st.button("📥 アップロード実行", type="primary"):
                        with st.spinner("ファイルをアップロード中..."):
                            try:
                                # ファイルデータを読み込み
                                file_data = []
                                filenames = []
                                
                                for file in uploaded_files:
                                    file.seek(0)  # ファイルポインタをリセット
                                    file_data.append(file.read())
                                    filenames.append(file.name)
                                
                                # ファイルを保存
                                saved_files = loader.save_uploaded_files(file_data, filenames)
                                
                                if saved_files:
                                    st.success(f"✅ {len(saved_files)}個のファイルをアップロードしました")
                                    for filename in saved_files:
                                        st.write(f"- {filename}")
                                    
                                    # ページを更新
                                    st.rerun()
                                else:
                                    st.error("❌ ファイルのアップロードに失敗しました")
                                    
                            except Exception as e:
                                st.error(f"❌ アップロードエラー: {str(e)}")
            
            else:  # ZIPファイル一括アップロード
                uploaded_zip = st.file_uploader(
                    "ZIPファイルを選択",
                    type=['zip'],
                    help="JSON形式のファイルを含むZIPファイルを選択してください"
                )
                
                if uploaded_zip:
                    st.write(f"選択されたファイル: {uploaded_zip.name} ({uploaded_zip.size:,} bytes)")
                    
                    if st.button("📥 ZIP展開・アップロード実行", type="primary"):
                        with st.spinner("ZIPファイルを展開中..."):
                            try:
                                # ZIPファイルを展開
                                uploaded_zip.seek(0)  # ファイルポインタをリセット
                                zip_data = uploaded_zip.read()
                                extracted_files = loader.extract_zip_file(zip_data, uploaded_zip.name)
                                
                                if extracted_files:
                                    st.success(f"✅ {len(extracted_files)}個のJSONファイルを展開・アップロードしました")
                                    for filename in extracted_files:
                                        st.write(f"- {filename}")
                                    
                                    # ページを更新
                                    st.rerun()
                                else:
                                    st.warning("⚠️ ZIPファイル内にJSONファイルが見つかりませんでした")
                                    
                            except Exception as e:
                                st.error(f"❌ ZIP展開エラー: {str(e)}")
            
            st.divider()
            
            # ファイル管理機能
            st.subheader("🗂️ ファイル管理")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ アップロードファイルをすべて削除", type="secondary"):
                    try:
                        loader.clear_uploaded_files()
                        st.success("✅ アップロードファイルをすべて削除しました")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ ファイル削除エラー: {str(e)}")
            
            with col2:
                if st.button("🔄 キャッシュクリア", type="secondary"):
                    loader.clear_cache()
                    st.success("✅ キャッシュをクリアしました")
                    st.rerun()
            
            st.stop()  # ファイルアップロードページはここで終了
        
        # 共通のデータ読み込み部分
        if selected_analysis in ['basic_analysis', 'retention_analysis', 'monthly_detail']:
            # データローダーを初期化
            loader = get_data_loader()
            
            # データソース状態を表示
            data_source_status = loader.get_data_source_status()
            with st.sidebar:
                st.subheader("📊 データソース情報")
                
                st.success("📁 ローカルファイル使用中")
                st.caption(f"パス: dataset/")
                
                # データソース詳細情報
                with st.expander("🔍 データソース詳細"):
                    st.write("**データソース情報:**")
                    st.write(f"- アップロード済みファイル数: {data_source_status['uploaded_count']}")
                    st.write(f"- ローカルファイル数: {data_source_status['local_count']}")
                    st.write(f"- 利用可能な月: {len(data_source_status['available_months'])}個")
                    
                    if data_source_status['available_months']:
                        st.write(f"- 最新月: {data_source_status['available_months'][0]}")
                        st.write(f"- 最古月: {data_source_status['available_months'][-1]}")
                
                # キャッシュ情報表示
                cache_info = loader.get_cache_info()
                st.subheader("⚡ キャッシュ状況")
                st.metric("キャッシュファイル数", cache_info.get('cache_size', 0))
                
                # キャッシュクリアボタン
                if st.button("🗑️ キャッシュクリア", help="メモリキャッシュをクリアして最新データを強制取得"):
                    loader.clear_cache()
                    st.cache_data.clear()
                    st.success("キャッシュをクリアしました")
                    st.rerun()
            
            # 月選択
            months = loader.get_available_months()
            if not months:
                st.error("❌ 利用可能なデータが見つかりません")
                st.info("データをアップロードするには、サイドバーで「📁 ファイルアップロード」を選択してください")
                st.stop()
            
            selected_month = st.selectbox(
                "対象月を選択",
                months,
                format_func=lambda x: f"{x} ({months.index(x) + 1}/{len(months)})"
            )
            
            # データ読み込み
            if selected_analysis in ['basic_analysis', 'monthly_detail']:
                basic_data, detail_data, summary_data = loader.load_analysis_data(selected_month)
            else:  # retention_analysis
                retention_data = loader.load_retention_data(selected_month)
                basic_data, detail_data, summary_data = None, None, None
        
        st.divider()
        
        # ヘルプ
        st.subheader("ℹ️ ヘルプ")
        if selected_analysis == "basic_analysis":
            st.markdown("""
            - **月次サマリー分析**: 全期間の月次推移データ
            - **PDF出力**: ブラウザの印刷機能を使用
            """)
        elif selected_analysis == "retention_analysis":
            st.markdown("""
            - **定着率分析**: 全期間の定着率推移データ
            - **PDF出力**: ブラウザの印刷機能を使用
            """)
        else:
            st.markdown("""
            - **単月詳細データ**: 選択月の詳細分析
            - **PDF出力**: ブラウザの印刷機能を使用
            """)

    # メインコンテンツ
    st.title("📊 架電ダッシュボード")
    
    # データディレクトリの取得関数（互換性のため保持）
    def get_data_dir():
        """データディレクトリのパスを取得（互換性のため保持）"""
        config = get_config()
        if config.LOCAL_DATA_DIR.exists():
            return str(config.LOCAL_DATA_DIR)
        return None
    
    # データ読み込み関数（新しいデータローダーを使用）
    @st.cache_data(ttl=1800)  # 30分間キャッシュ
    def load_data(month):
        """指定月のデータを読み込み（TTL付きキャッシュ）"""
        try:
            loader = get_data_loader()
            basic_data, detail_data, summary_data = loader.load_analysis_data(month)
            
            if basic_data is None or detail_data is None or summary_data is None:
                st.error(f"❌ {month}のデータの一部が読み込めませんでした")
                return None, None, None
                
            return basic_data, detail_data, summary_data
            
        except Exception as e:
            st.error(f"❌ データ読み込みエラー: {e}")
            st.write(f"エラーの詳細: {type(e).__name__}")
            return None, None, None

    @st.cache_data(ttl=1800)  # 30分間キャッシュ
    def load_retention_data(month):
        """指定された月の定着率分析データを読み込み（TTL付きキャッシュ）"""
        try:
            loader = get_data_loader()
            data = loader.load_retention_data(month)
            return data if data is not None else {}
        except Exception as e:
            st.error(f"定着率分析データ読み込みエラー: {str(e)}")
            return {}
    
    # --- グラフ共通のlegend設定関数 ---
    def update_legend(fig):
        fig.update_layout(
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.3,
                xanchor='center',
                x=0.5,
                font=dict(family='"Meiryo", "Yu Gothic", "Noto Sans JP", "sans-serif"', size=12)
            )
        )
        return fig

    # --- 数値フォーマット設定関数 ---
    def update_number_format(fig):
        """数値の表示形式を統一"""
        fig.update_traces(
            texttemplate='%{value:,.0f}',
            textposition='outside',
            textfont=dict(family='"Meiryo", "Yu Gothic", "Noto Sans JP", "sans-serif"', size=12)
        )
        return fig

    # 分析タイプに応じたコンテンツ表示
    if selected_analysis == "basic_analysis":
        st.header("📊 月次サマリー分析")
        st.caption("全期間の月次推移データを表示します")
        
        # 最新月のデータを読み込み（月次推移データとして使用）
        current_date = datetime.now()
        latest_month = current_date.strftime('%Y-%m')
        basic_data, detail_data, summary_data = load_data(latest_month)
        
        if basic_data and detail_data and summary_data:
            st.success("✅ データが正常に読み込まれました")
            # ここに具体的な分析コードを追加
            st.write("月次サマリー分析を実装予定")
        else:
            st.error("❌ データの読み込みに失敗しました")
    
    elif selected_analysis == "retention_analysis":
        st.header("📈 定着率分析")
        st.caption(f"選択月: {selected_month}")
        
        # 定着率データを読み込み
        retention_data = load_retention_data(selected_month)
        
        if retention_data:
            st.success("✅ 定着率データが正常に読み込まれました")
            # ここに具体的な分析コードを追加
            st.write("定着率分析を実装予定")
        else:
            st.error("❌ 定着率データの読み込みに失敗しました")
    
    elif selected_analysis == "monthly_detail":
        st.header("📋 単月詳細データ")
        st.caption(f"選択月: {selected_month}")
        
        # 選択月のデータを読み込み
        basic_data, detail_data, summary_data = load_data(selected_month)
        
        if basic_data and detail_data and summary_data:
            st.success("✅ データが正常に読み込まれました")
            # ここに具体的な分析コードを追加
            st.write("単月詳細データ分析を実装予定")
        else:
            st.error("❌ データの読み込みに失敗しました")
    
    else:
        st.info("分析タイプを選択してください") 