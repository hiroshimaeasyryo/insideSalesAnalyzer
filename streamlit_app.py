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
            "📋 単月詳細データ": "monthly_detail"
        }
        
        analysis_type = st.selectbox(
            "分析タイプを選択",
            list(analysis_options.keys())
        )
        
        selected_analysis = analysis_options[analysis_type]
        
        # 共通のデータ読み込み部分
        if selected_analysis in ['basic_analysis', 'monthly_summary', 'retention_analysis', 'monthly_detail']:
            # データローダーを初期化
            loader = get_data_loader()
            
            # データソース状態を表示
            data_source_status = loader.get_data_source_status()
            with st.sidebar:
                st.subheader("📊 データソース情報")
                
                if data_source_status['google_drive']['available']:
                    st.success("🌐 Google Drive接続中")
                    st.caption(f"フォルダID: {data_source_status['google_drive']['folder_id'][:8]}...")
                else:
                    st.error("📁 ローカルファイル使用中")
                    st.caption(f"パス: dataset/")
                    
                    # 詳細デバッグ情報
                    with st.expander("🔍 デバッグ情報"):
                        config = get_config()
                        
                        st.write("**設定状態:**")
                        st.write(f"- PRODUCTION_MODE: {config.PRODUCTION_MODE}")
                        st.write(f"- GOOGLE_DRIVE_ENABLED: {config.GOOGLE_DRIVE_ENABLED}")
                        st.write(f"- USE_LOCAL_FALLBACK: {config.USE_LOCAL_FALLBACK}")
                        st.write(f"- FOLDER_ID: {config.GOOGLE_DRIVE_FOLDER_ID}")
                        
                        # Streamlit Secrets チェック
                        st.write("**Streamlit Secrets状態:**")
                        try:
                            secrets_available = hasattr(st, 'secrets')
                            st.write(f"- Secrets利用可能: {'✅' if secrets_available else '❌'}")
                            
                            if secrets_available:
                                secrets_keys = list(st.secrets.keys())
                                st.write(f"- 設定済みキー: {secrets_keys}")
                                
                                # google_driveセクション確認
                                if 'google_drive' in st.secrets:
                                    gd_keys = list(st.secrets['google_drive'].keys())
                                    st.write(f"- google_driveキー: {gd_keys}")
                                    if 'service_account' in st.secrets['google_drive']:
                                        sa_value = st.secrets['google_drive']['service_account']
                                        st.write(f"- service_account長さ: {len(sa_value)}")
                                else:
                                    st.write("- google_driveセクション: ❌ なし")
                        except Exception as e:
                            st.write(f"- Secretsエラー: {str(e)}")
                        
                        # 環境変数チェック
                        st.write("**環境変数状態:**")
                        service_account_env = os.getenv('GOOGLE_SERVICE_ACCOUNT')
                        st.write(f"- GOOGLE_SERVICE_ACCOUNT: {'✅ 設定済み' if service_account_env else '❌ 未設定'}")
                        
                        if service_account_env:
                            try:
                                import json
                                service_data = json.loads(service_account_env)
                                st.write(f"- プロジェクトID: {service_data.get('project_id', 'N/A')}")
                                st.write(f"- クライアントメール: {service_data.get('client_email', 'N/A')[:30]}...")
                            except Exception as e:
                                st.write(f"- JSON解析エラー: {str(e)[:50]}...")
                        
                        # Google Drive接続テスト
                        st.write("**接続テスト:**")
                        
                        # キャッシュ無し強制テスト
                        success, message = loader.test_drive_connection_fresh()
                        if success:
                            st.write(f"- 強制リフレッシュテスト: ✅ {message}")
                        else:
                            st.write(f"- 強制リフレッシュテスト: ❌ 失敗")
                            st.write(f"- エラー詳細: {message[:100]}...")
                        
                        # 通常テスト
                        try:
                            from google_drive_utils import get_drive_client
                            client = get_drive_client(
                                service_account_file=config.GOOGLE_SERVICE_ACCOUNT_FILE,
                                folder_id=config.GOOGLE_DRIVE_FOLDER_ID
                            )
                            files = client.list_files_in_folder()
                            st.write(f"- 通常テスト: ✅ 成功 ({len(files)}ファイル)")
                        except Exception as e:
                            st.write(f"- 通常テスト: ❌ 失敗")
                            st.write(f"- エラー: {str(e)[:100]}...")
                
                # キャッシュ情報表示
                cache_info = data_source_status.get('cache', {})
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
                st.stop()
            
            selected_month = st.selectbox(
                "対象月を選択",
                months,
                format_func=lambda x: f"{x} ({months.index(x) + 1}/{len(months)})"
            )
            
            # データ読み込み
            if selected_analysis in ['basic_analysis', 'monthly_summary', 'monthly_detail']:
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
    
    # --- グラフの数値フォーマット設定関数 ---
    def update_number_format(fig):
        fig.update_layout(
            yaxis=dict(
                tickformat=',',
                separatethousands=True
            )
        )
        return fig

    # --- 指標名の日本語マッピング ---
    indicator_labels = {
        'call_count': '架電数',
        'call_hours': '架電時間数',
        'charge_connected': '担当コネクト数',
        'get_appointment': 'アポ獲得数',
        'total_deals': 'TAAAN商談数',
        'total_approved': '承認数',
        'total_revenue': '報酬合計額',
        'unique_staff_count': 'ユニーク稼働者数',
        'total_calls_per_staff': '1人あたり架電数',
        'call_hours_per_staff': '1人あたり架電時間数',
        'charge_connected_per_staff': '1人あたり担当コネクト数',
        'appointments_per_staff': '1人あたりアポ獲得数',
        'taaan_deals_per_staff': '1人あたりTAAAN商談数',
        'approved_deals_per_staff': '1人あたり承認数',
        'revenue_per_staff': '1人あたり報酬合計額',
        'total_calls_per_hour': '時間あたり架電数',
        'charge_connected_per_hour': '時間あたり担当コネクト数',
        'appointments_per_hour': '時間あたりアポ獲得数',
        'taaan_deals_per_hour': '時間あたりTAAAN商談数',
        'approved_deals_per_hour': '時間あたり承認数',
        'revenue_per_hour': '時間あたり報酬合計額'
    }

    # 分析タイプに応じたコンテンツ表示
    if selected_analysis == "basic_analysis":
        st.header("📊 月次サマリー分析")
        st.caption("全期間の月次推移データを表示します")
        
        # 最新月のデータを読み込み（月次推移データとして使用）
        current_date = datetime.now()
        latest_month = current_date.strftime('%Y-%m')
        basic_data, detail_data, summary_data = load_data(latest_month)
        
        if basic_data and detail_data and summary_data:
            # データディレクトリを取得
            data_dir = get_data_dir()
            
            # 月次推移データの抽出
            conversion_df = pd.DataFrame()
            retention_trend_df = pd.DataFrame()
            
            # monthly_conversionデータの抽出
            try:
                monthly_conv = basic_data.get('monthly_conversion', {})
                conv_list = []
                for month, month_data in monthly_conv.items():
                    # 全体
                    total = month_data.get('total', {})
                    conv_list.append({"month": month, "type": "total", **total})
                    for staff, sdata in month_data.get('by_staff', {}).items():
                        conv_list.append({"month": month, "type": "staff", "name": staff, **sdata})
                    for branch, bdata in month_data.get('by_branch', {}).items():
                        conv_list.append({"month": month, "type": "branch", "name": branch, **bdata})
                    for prod, pdata in month_data.get('by_product', {}).items():
                        conv_list.append({"month": month, "type": "product", "name": prod, **pdata})
                conversion_df = pd.DataFrame(conv_list)
            except Exception as e:
                st.warning(f"月次推移データの読み込みに失敗: {e}")
            
            # 定着率推移データの抽出
            try:
                if data_dir:
                    retention_path = os.path.join(data_dir, f'定着率分析_{latest_month}.json')
                    if os.path.exists(retention_path):
                        with open(retention_path, encoding='utf-8') as f:
                            retention_json = json.load(f)
                    
                    if "monthly_retention_rates" in retention_json:
                        trend = []
                        for month, r in retention_json["monthly_retention_rates"].items():
                            trend.append({
                                "month": month,
                                "active_staff": r.get("active_staff", 0),
                                "total_staff": r.get("total_staff", 0),
                                "retention_rate": float(r.get("retention_rate", 0))
                            })
                        retention_trend_df = pd.DataFrame(trend)
            except Exception as e:
                st.warning(f"定着率データの読み込みに失敗: {e}")
            
            # 1. アポ獲得→TAAAN→承認の月次推移グラフ・メトリクス
            if not conversion_df.empty:
                st.subheader("📈 アポ獲得→TAAAN→承認の月次推移")
                conv_total = conversion_df[conversion_df['type']=='total'].sort_values('month')
                
                if not conv_total.empty:
                    fig = go.Figure()
                    
                    # カラムの存在確認をしてからグラフに追加
                    if 'self_reported_appointments' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['self_reported_appointments'], mode='lines+markers', name='日報上のアポ獲得'))
                    if 'taaan_entries' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['taaan_entries'], mode='lines+markers', name='TAAAN入力'))
                    if 'approved_deals' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['approved_deals'], mode='lines+markers', name='メーカーからの承認'))
                    if 'taaan_rate' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['taaan_rate']*100, mode='lines+markers', name='アポ→TAAAN率(%)', yaxis='y2'))
                    if 'approval_rate' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['approval_rate']*100, mode='lines+markers', name='TAAAN→承認率(%)', yaxis='y2'))
                    if 'true_approval_rate' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['true_approval_rate']*100, mode='lines+markers', name='アポ→承認率(%)', yaxis='y2'))
                    
                    fig.update_layout(
                        yaxis=dict(title='件数'),
                        yaxis2=dict(title='割合(%)', overlaying='y', side='right'),
                        legend=dict(orientation='h'),
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 最新月のメトリクス
                    latest = conv_total.iloc[-1]
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    
                    col1.metric("日報上のアポ獲得", 
                               int(latest.get('self_reported_appointments', 0)) if pd.notnull(latest.get('self_reported_appointments')) else 0)
                    col2.metric("TAAAN入力", 
                               int(latest.get('taaan_entries', 0)) if pd.notnull(latest.get('taaan_entries')) else 0)
                    col3.metric("メーカーからの承認", 
                               int(latest.get('approved_deals', 0)) if pd.notnull(latest.get('approved_deals')) else 0)
                    col4.metric("アポ→TAAAN率", 
                               f"{latest.get('taaan_rate', 0)*100:.1f}%" if pd.notnull(latest.get('taaan_rate')) else 'N/A')
                    col5.metric("TAAAN→承認率", 
                               f"{latest.get('approval_rate', 0)*100:.1f}%" if pd.notnull(latest.get('approval_rate')) else 'N/A')
                    col6.metric("アポ→承認率", 
                               f"{latest.get('true_approval_rate', 0)*100:.1f}%" if pd.notnull(latest.get('true_approval_rate')) else 'N/A')
                
                # 最新月の商談ステータス詳細
                st.subheader("📊 最新月の商談ステータス詳細")
                
                # 最新月のサマリーデータを読み込み
                if data_dir:
                    latest_month_summary_path = os.path.join(data_dir, f'月次サマリー_{latest_month}.json')
                    if os.path.exists(latest_month_summary_path):
                        try:
                            with open(latest_month_summary_path, encoding='utf-8') as f:
                                latest_summary = json.load(f)
                        
                            if 'deal_status_breakdown' in latest_summary:
                                deal_status = latest_summary['deal_status_breakdown']
                                total_deals = deal_status.get('total', 0)
                                
                                if total_deals > 0:
                                    col1, col2, col3, col4 = st.columns(4)
                                    
                                    with col1:
                                        approved = deal_status.get('approved', 0)
                                        approved_rate = (approved / total_deals * 100) if total_deals > 0 else 0
                                        st.metric(
                                            "承認", 
                                            f"{approved:,}件",
                                            f"{approved_rate:.1f}%",
                                            help="商談ステータス: 承認"
                                        )
                                    
                                    with col2:
                                        rejected = deal_status.get('rejected', 0)
                                        rejected_rate = (rejected / total_deals * 100) if total_deals > 0 else 0
                                        st.metric(
                                            "却下", 
                                            f"{rejected:,}件",
                                            f"{rejected_rate:.1f}%",
                                            help="商談ステータス: 却下"
                                        )
                                    
                                    with col3:
                                        pending = deal_status.get('pending', 0)
                                        pending_rate = (pending / total_deals * 100) if total_deals > 0 else 0
                                        st.metric(
                                            "承認待ち・要対応", 
                                            f"{pending:,}件",
                                            f"{pending_rate:.1f}%",
                                            help="商談ステータス: 承認待ち・要対応"
                                        )
                                    
                                    with col4:
                                        st.metric(
                                            "総商談数", 
                                            f"{total_deals:,}件",
                                            help="TAAANシステムに登録された総商談数"
                                        )
                                    
                                    # 商談ステータスの円グラフ
                                    fig = go.Figure(data=[go.Pie(
                                        labels=['承認', '却下', '承認待ち・要対応'],
                                        values=[approved, rejected, pending],
                                        hole=0.3,
                                        marker_colors=['#00ff00', '#ff0000', '#ffaa00']
                                    )])
                                    fig.update_layout(
                                        title=f"{latest_month}の商談ステータス分布",
                                        height=400
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("ℹ️ 商談データがありません")
                        except Exception as e:
                            st.warning(f"商談ステータスデータの読み込みに失敗: {e}")
                    else:
                        st.info("ℹ️ 最新月のサマリーデータが見つかりません")
                else:
                    st.warning("⚠️ コンバージョンデータが見つかりませんでした")
            
            # 2. 定着率推移グラフ
            if not retention_trend_df.empty and 'retention_rate' in retention_trend_df.columns:
                st.subheader("📊 定着率推移")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=retention_trend_df['month'], y=retention_trend_df['retention_rate'], mode='lines+markers', name='定着率(%)'))
                fig2.update_layout(yaxis=dict(title='定着率(%)', range=[0,100]), height=300)
                st.plotly_chart(fig2, use_container_width=True)
            elif not retention_trend_df.empty:
                st.warning("⚠️ 定着率データの形式が正しくありません")
            else:
                st.info("ℹ️ 定着率データが見つかりませんでした")
        else:
            st.error("❌ 月次分析データの読み込みに失敗しました")
    
    elif selected_analysis == "retention_analysis":
        st.header("📈 定着率分析")
        st.caption("全期間の定着率推移データを表示します")
        
        # 最新月のデータを読み込み（定着率データとして使用）
        current_date = datetime.now()
        latest_month = current_date.strftime('%Y-%m')
        retention_data = load_retention_data(latest_month)
        
        if retention_data:
            # 定着率推移グラフ
            st.subheader("📊 定着率推移")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=retention_data['month'], y=retention_data['retention_rate'], mode='lines+markers', name='定着率(%)'))
            fig.update_layout(yaxis=dict(title='定着率(%)', range=[0,100]), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ 定着率データが見つかりませんでした")
    
    elif selected_analysis == "monthly_detail":
        st.header("📋 単月詳細データ")
        st.caption(f"選択月: {selected_month}")
        
        # 選択月のデータを読み込み
        basic_data, detail_data, summary_data = load_data(selected_month)
        
        if basic_data and detail_data and summary_data:
            # データフレーム作成
            def extract_daily_activity_from_staff(staff_dict):
                """スタッフごとのdaily_activityをフラットなDataFrameに変換（メイン商材とサブ商材を含む）"""
                records = []
                for staff_name, staff_data in staff_dict.items():
                    branch = staff_data.get("branch")
                    join_date = staff_data.get("join_date")
                    for activity in staff_data.get("daily_activity", []):
                        # 日付をUTC→JST変換
                        activity_date = activity.get("date")
                        if activity_date:
                            try:
                                # UTC→JST変換
                                date_jst = pd.to_datetime(activity_date, utc=True).tz_convert('Asia/Tokyo').date()
                                activity_date = str(date_jst)
                            except:
                                # 変換に失敗した場合はそのまま使用
                                pass
                        
                        # メイン商材の処理
                        main = activity.get("main_product", {})
                        if main.get("call_count", 0) > 0:  # 架電数が0より大きい場合のみ追加
                            record = {
                                "date": activity_date,
                                "product": main.get("product"),
                                "call_hours": main.get("call_hours"),
                                "call_count": main.get("call_count"),
                                "reception_bk": main.get("reception_bk"),
                                "no_one_in_charge": main.get("no_one_in_charge"),
                                "disconnect": main.get("disconnect"),
                                "charge_connected": main.get("charge_connected"),
                                "charge_bk": main.get("charge_bk"),
                                "get_appointment": main.get("get_appointment"),
                                "staff_name": staff_name,
                                "branch": branch,
                                "join_date": join_date,
                                "product_type": "メイン商材"
                            }
                            records.append(record)
                        
                        # サブ商材の処理
                        sub_products = activity.get("sub_products", [])
                        for sub in sub_products:
                            if sub.get("call_count", 0) > 0:  # 架電数が0より大きい場合のみ追加
                                record = {
                                    "date": activity_date,
                                    "product": sub.get("product"),
                                    "call_hours": sub.get("call_hours"),
                                    "call_count": sub.get("call_count"),
                                    "reception_bk": sub.get("reception_bk"),
                                    "no_one_in_charge": sub.get("no_one_in_charge"),
                                    "disconnect": sub.get("disconnect"),
                                    "charge_connected": sub.get("charge_connected"),
                                    "charge_bk": sub.get("charge_bk"),
                                    "get_appointment": sub.get("get_appointment"),
                                    "staff_name": staff_name,
                                    "branch": branch,
                                    "join_date": join_date,
                                    "product_type": "サブ商材"
                                }
                                records.append(record)
                return pd.DataFrame(records)
            
            # 基本分析データフレーム
            try:
                staff_dict = basic_data["monthly_analysis"][selected_month]["staff"]
                df_basic = extract_daily_activity_from_staff(staff_dict)
            except Exception as e:
                st.error(f"データ抽出エラー: {e}")
                df_basic = pd.DataFrame()
            
            # サブヘッダー
            st.subheader("営業フロー指標")
            st.info("フロー: 架電数 → 担当コネクト → アポ獲得 → TAAAN入力")

            if not df_basic.empty:
                total_calls = df_basic['call_count'].sum() if 'call_count' in df_basic.columns else 0
                charge_connected = df_basic['charge_connected'].sum() if 'charge_connected' in df_basic.columns else 0
                appointments = df_basic['get_appointment'].sum() if 'get_appointment' in df_basic.columns else 0
                total_deals = summary_data['key_metrics'].get('total_deals', 0) if 'key_metrics' in summary_data else 0
                total_approved = summary_data['key_metrics'].get('total_approved', 0) if 'key_metrics' in summary_data else 0
                
                # 売上データは branch_performance から合計を計算
                total_revenue = 0
                total_potential_revenue = 0
                if 'branch_performance' in summary_data:
                    for branch, data in summary_data['branch_performance'].items():
                        total_revenue += data.get('total_revenue', 0)
                        total_potential_revenue += data.get('total_potential_revenue', 0)

                # --- カードスタイルで指標を表示 ---
                card_style = """
                    <div style="
                        background-color: #fff;
                        border-radius: 10px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                        padding: 20px 10px 10px 10px;
                        margin: 5px;
                        text-align: center;
                        border-left: 6px solid {color};
                        min-width: 170px;
                        min-height: 170px;
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                    ">
                        <div>
                            <div style=\"font-size: 1.1em; color: #555;\">{label}</div>
                            <div style=\"font-size: 2em; font-weight: bold; color: {color};\">{value}</div>
                        </div>
                        <div style=\"font-size: 0.9em; color: #888; margin-top: 10px;\">{desc}</div>
                    </div>
                """

                # (a) 架電数セット（青系グラデーション）
                card_data = [
                    {"label": "架電数", "value": f"{total_calls:,}件", "desc": "日報上で報告された架電数", "color": "#01478c"},
                    {"label": "担当コネクト数", "value": f"{charge_connected:,}件", "desc": "日報上で報告された担当コネクト数", "color": "#1976d2"},
                    {"label": "アポ獲得数", "value": f"{appointments:,}件", "desc": "日報上で報告されたアポ獲得数", "color": "#42a5f5"},
                    {"label": "TAAAN商談数", "value": f"{total_deals:,}件", "desc": "TAAANに入力された件数", "color": "#90caf9"},
                ]
                cols = st.columns(len(card_data))
                for i, card in enumerate(card_data):
                    cols[i].markdown(card_style.format(**card), unsafe_allow_html=True)

                # (b) 売上セット（緑系グラデーション）
                revenue_card_data = [
                    {"label": "確定売上", "value": f"¥{total_revenue:,}", "desc": "TAAAN入力で商談ステータスが「承認」の報酬合計", "color": "#055709"},
                    {"label": "潜在売上", "value": f"¥{total_potential_revenue:,}", "desc": "TAAAN入力で商談ステータスが「承認待ち」または「要対応」の報酬合計", "color": "#388e3c"},
                    {"label": "総売上", "value": f"¥{total_revenue + total_potential_revenue:,}", "desc": "確定売上と潜在売上の合計", "color": "#81c784"},
                ]
                revenue_cols = st.columns(len(revenue_card_data))
                for i, card in enumerate(revenue_card_data):
                    revenue_cols[i].markdown(card_style.format(**card), unsafe_allow_html=True)

                # --- 変換率の計算 ---
                call_to_connect = (charge_connected / total_calls * 100) if total_calls > 0 else 0
                connect_to_appointment = (appointments / charge_connected * 100) if charge_connected > 0 else 0
                appointment_to_taaan = (total_deals / appointments * 100) if appointments > 0 else 0
                taaan_to_approved = (total_approved / total_deals * 100) if total_deals > 0 else 0

                # (c) 変換率セット（オレンジ系グラデーション）
                rate_card_data = [
                    {"label": "架電→担当率", "value": f"{call_to_connect:.1f}%", "desc": "日報上で報告された担当コネクト数÷架電数", "color": "#9e5102"},
                    {"label": "担当→アポ率", "value": f"{connect_to_appointment:.1f}%", "desc": "日報上で報告されたアポ獲得数÷担当コネクト数", "color": "#f57c00"},
                    {"label": "アポ→TAAAN率", "value": f"{appointment_to_taaan:.1f}%", "desc": "アポ獲得数÷TAAAN商談数", "color": "#ffb300"},
                    {"label": "TAAAN→承認率", "value": f"{taaan_to_approved:.1f}%", "desc": "TAAANに入力された件数のうち、商談ステータスが「承認」の割合", "color": "#ffe082"},
                ]
                rate_cols = st.columns(len(rate_card_data))
                for i, card in enumerate(rate_card_data):
                    rate_cols[i].markdown(card_style.format(**card), unsafe_allow_html=True)

                # --- ファネルチャートはそのまま下に表示 ---
                funnel_labels = ["架電数", "担当コネクト数", "アポ獲得数", "TAAAN商談数"]
                funnel_values = [total_calls, charge_connected, appointments, total_deals]
                fig = go.Figure(go.Funnel(
                    y=funnel_labels,
                    x=funnel_values,
                    textinfo="value+percent previous"
                ))
                fig.update_layout(title="営業フロー ファネルチャート", height=350)
                st.plotly_chart(fig, use_container_width=True)

                # 商談ステータス詳細（円グラフのみ、数値の重複表示なし）
                if 'deal_status_breakdown' in summary_data:
                    st.subheader("商談ステータス詳細")
                    deal_status = summary_data['deal_status_breakdown']
                    approved = deal_status.get('approved', 0)
                    rejected = deal_status.get('rejected', 0)
                    pending = deal_status.get('pending', 0)
                    total_deals = deal_status.get('total', 0)
                    fig = go.Figure(data=[go.Pie(
                        labels=['承認', '却下', '承認待ち・要対応'],
                        values=[approved, rejected, pending],
                        hole=0.3,
                        marker_colors=['#00ff00', '#ff0000', '#ffaa00']
                    )])
                    fig.update_layout(title="商談ステータス分布", height=350)
                    st.plotly_chart(fig, use_container_width=True)
                
                st.divider()
            
            # タブ表示（データが存在する場合のみ）
            # カラムの存在確認を改善
            has_call_data = (not df_basic.empty and 
                            ('call_count' in df_basic.columns or 'total_calls' in df_basic.columns))
            
            if has_call_data:
                # タブを作成
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 日次トレンド", "🏢 支部別分析", "👥 スタッフ別分析", "📦 商材別分析", "📋 詳細データ"])
                
                with tab1:
                    st.subheader("日次トレンド")
                    
                    # 日次トレンドのサブタブ
                    trend_tab1, trend_tab2 = st.tabs(["📊 日別トレンド", "📈 累計値トレンド"])
                    
                    # 日別トレンド - カラム名を動的に決定
                    call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_basic.columns else 'successful_calls'
                    
                    daily_trend = df_basic.groupby('date').agg({
                        call_col: 'sum',
                        success_col: 'sum',
                        appointment_col: 'sum'
                    }).reset_index()
                    
                    # カラム名を統一
                    daily_trend.columns = ['date', 'total_calls', 'successful_calls', 'appointments']
                    
                    # 日付をdatetimeに変換（UTC→JST変換）
                    daily_trend['date'] = pd.to_datetime(daily_trend['date'], utc=True).dt.tz_convert('Asia/Tokyo').dt.date
                    daily_trend['date'] = pd.to_datetime(daily_trend['date'])
                    # ポイントを日付の中央（12:00）に配置
                    daily_trend['date'] = daily_trend['date'] + pd.Timedelta(hours=12)
                    daily_trend = daily_trend.sort_values('date')
                    
                    # 土日判定を追加
                    daily_trend['is_weekend'] = daily_trend['date'].dt.dayofweek.isin([5, 6])  # 5=土曜日, 6=日曜日
                    
                    # 土日ハイライト用の全日付範囲を作成（JST時間で）
                    if not daily_trend.empty:
                        # JST時間での日付範囲を作成
                        date_range = pd.date_range(
                            start=daily_trend['date'].min(),
                            end=daily_trend['date'].max(),
                            freq='D',
                            tz='Asia/Tokyo'  # 日本時間で作成
                        )
                        weekend_dates = [d for d in date_range if d.weekday() >= 5]  # 土日のみ
                    else:
                        weekend_dates = []
                    
                    with trend_tab1:
                        # 日別トレンドグラフ
                        fig_trend = go.Figure()
                        
                        # 土日の背景色を追加（視覚効果のため半日前倒し）
                        for weekend_date in weekend_dates:
                            # タイムゾーンを除去して日付のみで範囲指定
                            date_start = weekend_date.replace(tzinfo=None)
                            # 視覚効果のため半日前倒し（前日の12:00から当日の12:00まで）
                            visual_start = date_start - pd.Timedelta(hours=12)
                            visual_end = date_start + pd.Timedelta(hours=12)
                            fig_trend.add_vrect(
                                x0=visual_start,
                                x1=visual_end,
                                fillcolor="lightgray",
                                opacity=0.3,
                                layer="below",
                                line_width=0
                            )
                        
                        # 総架電数
                        fig_trend.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['total_calls'],
                            mode='lines+markers',
                            name='総架電数',
                            line=dict(color='blue', width=2),
                            yaxis='y1',
                            hovertemplate='%{x|%Y/%m/%d}<br>総架電数: %{y:,}件<extra></extra>'
                        ))
                        # 担当コネクト数
                        fig_trend.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['successful_calls'],
                            mode='lines+markers',
                            name='担当コネクト数',
                            line=dict(color='green', width=2),
                            yaxis='y1',
                            hovertemplate='%{x|%Y/%m/%d}<br>担当コネクト数: %{y:,}件<extra></extra>'
                        ))
                        # アポ獲得数（右軸）
                        fig_trend.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['appointments'],
                            mode='lines+markers',
                            name='アポ獲得数(右軸)',
                            line=dict(color='red', width=2, dash='dot'),
                            yaxis='y2',
                            hovertemplate='%{x|%Y/%m/%d}<br>アポ獲得数: %{y:,}件<extra></extra>'
                        ))
                        
                        fig_trend.update_layout(
                            title="日別架電トレンド",
                            xaxis_title="日付",
                            yaxis=dict(
                                title='件数', 
                                side='left', 
                                showgrid=True, 
                                zeroline=True,
                                tickformat=',',  # カンマ区切り
                                separatethousands=True
                            ),
                            yaxis2=dict(
                                title='アポ獲得数', 
                                side='right', 
                                overlaying='y', 
                                showgrid=False, 
                                zeroline=False,
                                tickformat=',',  # カンマ区切り
                                separatethousands=True
                            ),
                            height=400,
                            legend=dict(orientation='h'),
                            # 日本人にわかりやすい日付形式
                            xaxis=dict(
                                tickformat='%Y/%m/%d',
                                hoverformat='%Y/%m/%d'
                            )
                        )
                        
                        st.plotly_chart(fig_trend, use_container_width=True)
                    
                    with trend_tab2:
                        # 累計値トレンドグラフ
                        daily_trend['cumulative_calls'] = daily_trend['total_calls'].cumsum()
                        daily_trend['cumulative_connects'] = daily_trend['successful_calls'].cumsum()
                        daily_trend['cumulative_appointments'] = daily_trend['appointments'].cumsum()
                        
                        fig_cumulative = go.Figure()
                        
                        # 土日の背景色を追加（視覚効果のため半日前倒し）
                        for weekend_date in weekend_dates:
                            # タイムゾーンを除去して日付のみで範囲指定
                            date_start = weekend_date.replace(tzinfo=None)
                            # 視覚効果のため半日前倒し（前日の12:00から当日の12:00まで）
                            visual_start = date_start - pd.Timedelta(hours=12)
                            visual_end = date_start + pd.Timedelta(hours=12)
                            fig_cumulative.add_vrect(
                                x0=visual_start,
                                x1=visual_end,
                                fillcolor="lightgray",
                                opacity=0.3,
                                layer="below",
                                line_width=0
                            )
                        
                        # 累計総架電数
                        fig_cumulative.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['cumulative_calls'],
                            mode='lines+markers',
                            name='累計総架電数',
                            line=dict(color='blue', width=2),
                            yaxis='y1',
                            hovertemplate='%{x|%Y/%m/%d}<br>累計総架電数: %{y:,}件<extra></extra>'
                        ))
                        # 累計担当コネクト数
                        fig_cumulative.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['cumulative_connects'],
                            mode='lines+markers',
                            name='累計担当コネクト数',
                            line=dict(color='green', width=2),
                            yaxis='y1',
                            hovertemplate='%{x|%Y/%m/%d}<br>累計担当コネクト数: %{y:,}件<extra></extra>'
                        ))
                        # 累計アポ獲得数（右軸）
                        fig_cumulative.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['cumulative_appointments'],
                            mode='lines+markers',
                            name='累計アポ獲得数(右軸)',
                            line=dict(color='red', width=2, dash='dot'),
                            yaxis='y2',
                            hovertemplate='%{x|%Y/%m/%d}<br>累計アポ獲得数: %{y:,}件<extra></extra>'
                        ))
                        
                        fig_cumulative.update_layout(
                            title="累計値トレンド",
                            xaxis_title="日付",
                            yaxis=dict(
                                title='累計件数', 
                                side='left', 
                                showgrid=True, 
                                zeroline=True,
                                tickformat=',',  # カンマ区切り
                                separatethousands=True
                            ),
                            yaxis2=dict(
                                title='累計アポ獲得数', 
                                side='right', 
                                overlaying='y', 
                                showgrid=False, 
                                zeroline=False,
                                tickformat=',',  # カンマ区切り
                                separatethousands=True
                            ),
                            height=400,
                            legend=dict(orientation='h'),
                            # 日本人にわかりやすい日付形式
                            xaxis=dict(
                                tickformat='%Y/%m/%d',
                                hoverformat='%Y/%m/%d'
                            )
                        )
                        
                        st.plotly_chart(fig_cumulative, use_container_width=True)
                
                with tab2:
                    st.subheader("支部別分析")

                    # --- 統一した支部の色パレットを定義 ---
                    branch_colors = {
                        '東京': '#ff6b6b',      # 赤
                        '横浜': '#4ecdc4',      # ティール
                        '名古屋': '#45b7d1',    # 青
                        '福岡': '#96ceb4',      # 緑
                        '新潟': '#feca57',      # オレンジ
                        '大分': '#ff9ff3',      # ピンク
                        '未設定': '#95a5a6',    # グレー
                        '社員': '#6c5ce7'       # 紫（未設定と区別）
                    }

                    # --- サブタブ共通で使う支部別集計処理をここで必ず実行 ---
                    call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_basic.columns else 'successful_calls'
                    hours_col = 'call_hours' if 'call_hours' in df_basic.columns else None
                    df_basic_for_branch = df_basic.copy()
                    df_basic_for_branch['branch'] = df_basic_for_branch['branch'].fillna('未設定')
                    unique_staff_by_branch = df_basic_for_branch.groupby('branch')['staff_name'].nunique().reset_index()
                    unique_staff_by_branch.columns = ['branch', 'unique_staff_count']
                    agg_dict = {call_col: 'sum', success_col: 'sum', appointment_col: 'sum'}
                    if hours_col:
                        agg_dict[hours_col] = 'sum'
                    branch_summary = df_basic_for_branch.groupby('branch').agg(agg_dict).reset_index()
                    columns = ['branch', 'total_calls', 'charge_connected', 'appointments']
                    if hours_col:
                        columns.append('call_hours')
                    branch_summary.columns = columns
                    branch_summary = branch_summary.merge(unique_staff_by_branch, on='branch', how='left')
                    if 'branch_performance' in summary_data:
                        taaan_branch_data = {}
                        for branch, data in summary_data['branch_performance'].items():
                            taaan_branch_data[branch] = {
                                'total_deals': data.get('total_deals', 0),
                                'total_approved': data.get('total_approved', 0),
                                'total_revenue': data.get('total_revenue', 0),
                                'total_potential_revenue': data.get('total_potential_revenue', 0)
                            }
                        branch_summary['taaan_deals'] = branch_summary['branch'].map(
                            lambda x: taaan_branch_data.get(x, {}).get('total_deals', 0)
                        )
                        branch_summary['approved_deals'] = branch_summary['branch'].map(
                            lambda x: taaan_branch_data.get(x, {}).get('total_approved', 0)
                        )
                        branch_summary['total_revenue'] = branch_summary['branch'].map(
                            lambda x: taaan_branch_data.get(x, {}).get('total_revenue', 0)
                        )
                        branch_summary['total_potential_revenue'] = branch_summary['branch'].map(
                            lambda x: taaan_branch_data.get(x, {}).get('total_potential_revenue', 0)
                        )
                    else:
                        branch_summary['taaan_deals'] = 0
                        branch_summary['approved_deals'] = 0
                        branch_summary['total_revenue'] = 0
                        branch_summary['total_potential_revenue'] = 0
                    branch_summary['connect_rate'] = (
                        (branch_summary['charge_connected'] / branch_summary['total_calls'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    branch_summary['appointment_rate'] = (
                        (branch_summary['appointments'] / branch_summary['charge_connected'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    branch_summary['approval_rate'] = (
                        (branch_summary['approved_deals'] / branch_summary['taaan_deals'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    # --- ここまで共通集計 ---

                    # サブタブを追加
                    subtab1, subtab2, subtab3, subtab4 = st.tabs([
                        "実数", "単位あたり分析", "実数3ヶ月比較", "単位あたり3ヶ月比較"
                    ])

                    with subtab1:
                        st.markdown("#### 実数")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_calls = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_calls.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['total_calls'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>架電数: %{y:,}件<extra></extra>'
                                ))
                            fig_branch_calls.update_layout(
                                title=indicator_labels.get('call_count', '架電数'),
                                yaxis_title=indicator_labels.get('call_count', '架電数'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_calls, use_container_width=True)
                        with col2:
                            if 'call_hours' in branch_summary.columns:
                                # go.Figureを使用して手動で凡例を追加
                                fig_branch_hours = go.Figure()
                                # 支部ごとに異なる色でバーを作成
                                for branch in branch_summary['branch']:
                                    branch_data = branch_summary[branch_summary['branch'] == branch]
                                    fig_branch_hours.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data['call_hours'],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate='<b>%{x}</b><br>架電時間数: %{y:,.1f}時間<extra></extra>'
                                    ))
                                fig_branch_hours.update_layout(
                                    title=indicator_labels.get('call_hours', '架電時間数'),
                                    yaxis_title=indicator_labels.get('call_hours', '架電時間数'),
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig_branch_hours, use_container_width=True)
                            else:
                                st.info("架電時間データがありません")
                        with col3:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_connect = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_connect.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['charge_connected'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>担当コネクト数: %{y:,}件<extra></extra>'
                                ))
                            fig_branch_connect.update_layout(
                                title=indicator_labels.get('charge_connected', '担当コネクト数'),
                                yaxis_title=indicator_labels.get('charge_connected', '担当コネクト数'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_connect, use_container_width=True)
                        col4, col5, col6 = st.columns(3)
                        with col4:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_appointments = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_appointments.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['appointments'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>アポ獲得数: %{y:,}件<extra></extra>'
                                ))
                            fig_branch_appointments.update_layout(
                                title=indicator_labels.get('get_appointment', 'アポ獲得数'),
                                yaxis_title=indicator_labels.get('get_appointment', 'アポ獲得数'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_appointments, use_container_width=True)
                        with col5:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_taaan = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_taaan.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['taaan_deals'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>TAAAN商談数: %{y:,}件<extra></extra>'
                                ))
                            fig_branch_taaan.update_layout(
                                title=indicator_labels.get('total_deals', 'TAAAN商談数'),
                                yaxis_title=indicator_labels.get('total_deals', 'TAAAN商談数'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_taaan, use_container_width=True)
                        with col6:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_approved = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_approved.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['approved_deals'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>承認数: %{y:,}件<extra></extra>'
                                ))
                            fig_branch_approved.update_layout(
                                title=indicator_labels.get('total_approved', '承認数'),
                                yaxis_title=indicator_labels.get('total_approved', '承認数'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_approved, use_container_width=True)
                        col7, col8 = st.columns(2)
                        with col7:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_reward = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_reward.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['total_revenue'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>報酬合計額: ¥%{y:,}<extra></extra>'
                                ))
                            fig_branch_reward.update_layout(
                                title=indicator_labels.get('total_revenue', '報酬合計額'),
                                yaxis_title=indicator_labels.get('total_revenue', '報酬合計額'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_reward, use_container_width=True)
                        with col8:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_staff = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_staff.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['unique_staff_count'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False,
                                    hovertemplate='<b>%{x}</b><br>ユニーク稼働者数: %{y:,}人<extra></extra>'
                                ))
                            fig_branch_staff.update_layout(
                                title=indicator_labels.get('unique_staff_count', 'ユニーク稼働者数'),
                                yaxis_title=indicator_labels.get('unique_staff_count', 'ユニーク稼働者数'),
                                showlegend=False,
                                yaxis=dict(tickformat=',', separatethousands=True)
                            )
                            st.plotly_chart(fig_branch_staff, use_container_width=True)

                    with subtab2:
                        st.markdown("##### 1人あたり指標")
                        unit_df = branch_summary.copy()
                        unit_df['total_calls_per_staff'] = unit_df['total_calls'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['call_hours_per_staff'] = unit_df['call_hours'] / unit_df['unique_staff_count'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['charge_connected_per_staff'] = unit_df['charge_connected'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['appointments_per_staff'] = unit_df['appointments'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['taaan_deals_per_staff'] = unit_df['taaan_deals'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['approved_deals_per_staff'] = unit_df['approved_deals'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['revenue_per_staff'] = unit_df['total_revenue'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            for y_col, label in [
                                ('total_calls_per_staff', indicator_labels['total_calls_per_staff']),
                                ('taaan_deals_per_staff', indicator_labels['taaan_deals_per_staff'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:,.1f}}<extra></extra>'
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        with col2:
                            for y_col, label in [
                                ('call_hours_per_staff', indicator_labels['call_hours_per_staff']),
                                ('approved_deals_per_staff', indicator_labels['approved_deals_per_staff'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:,.1f}}<extra></extra>'
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        with col3:
                            for y_col, label in [
                                ('charge_connected_per_staff', indicator_labels['charge_connected_per_staff']),
                                ('appointments_per_staff', indicator_labels['appointments_per_staff']),
                                ('revenue_per_staff', indicator_labels['revenue_per_staff'])
                            ]:
                                fig = go.Figure()
                                # 報酬関連はホバーテンプレートに¥マークを追加
                                is_revenue = 'revenue' in y_col
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    hover_template = f'<b>%{{x}}</b><br>{label}: ¥%{{y:,.1f}}<extra></extra>' if is_revenue else f'<b>%{{x}}</b><br>{label}: %{{y:,.1f}}<extra></extra>'
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate=hover_template
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig, use_container_width=True)

                        st.markdown("##### 時間あたり指標")
                        unit_df['total_calls_per_hour'] = unit_df['total_calls'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['charge_connected_per_hour'] = unit_df['charge_connected'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['appointments_per_hour'] = unit_df['appointments'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['taaan_deals_per_hour'] = unit_df['taaan_deals'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['approved_deals_per_hour'] = unit_df['approved_deals'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['revenue_per_hour'] = unit_df['total_revenue'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        col4, col5, col6 = st.columns(3)
                        with col4:
                            for y_col, label in [
                                ('total_calls_per_hour', indicator_labels['total_calls_per_hour']),
                                ('taaan_deals_per_hour', indicator_labels['taaan_deals_per_hour'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:,.1f}}<extra></extra>'
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        with col5:
                            for y_col, label in [
                                ('charge_connected_per_hour', indicator_labels['charge_connected_per_hour']),
                                ('approved_deals_per_hour', indicator_labels['approved_deals_per_hour'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:,.1f}}<extra></extra>'
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        with col6:
                            for y_col, label in [
                                ('appointments_per_hour', indicator_labels['appointments_per_hour']),
                                ('revenue_per_hour', indicator_labels['revenue_per_hour'])
                            ]:
                                fig = go.Figure()
                                # 報酬関連はホバーテンプレートに¥マークを追加
                                is_revenue = 'revenue' in y_col
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    hover_template = f'<b>%{{x}}</b><br>{label}: ¥%{{y:,.0f}}<extra></extra>' if is_revenue else f'<b>%{{x}}</b><br>{label}: %{{y:,.1f}}<extra></extra>'
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False,
                                        hovertemplate=hover_template
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig, use_container_width=True)

                    with subtab3:
                        st.markdown("#### 実数3ヶ月比較")
                        # 比較月リスト作成
                        def get_prev_months(month_str, n=3):
                            base = datetime.strptime(month_str, '%Y-%m')
                            return [(base - timedelta(days=30*i)).strftime('%Y-%m') for i in reversed(range(n))]
                        compare_months = get_prev_months(selected_month, 3)
                        # 各月の支部別集計を取得
                        branch_summaries = {}
                        for m in compare_months:
                            b, d, s = load_data(m)
                            if b and s:
                                try:
                                    staff_dict = b["monthly_analysis"][m]["staff"]
                                    df_b = extract_daily_activity_from_staff(staff_dict)
                                    df_b["branch"] = df_b["branch"].fillna("未設定")
                                    unique_staff = df_b.groupby('branch')['staff_name'].nunique().reset_index()
                                    unique_staff.columns = ['branch', 'unique_staff_count']
                                    agg_dict = {'call_count': 'sum', 'charge_connected': 'sum', 'get_appointment': 'sum', 'call_hours': 'sum'}
                                    branch_df = df_b.groupby('branch').agg(agg_dict).reset_index()
                                    branch_df = branch_df.merge(unique_staff, on='branch', how='left')
                                    # TAAANデータ
                                    if 'branch_performance' in s:
                                        for col in ['total_deals','total_approved','total_revenue']:
                                            branch_df[col] = branch_df['branch'].map(lambda x: s['branch_performance'].get(x,{}).get(col,0))
                                    else:
                                        branch_df['total_deals'] = 0
                                        branch_df['total_approved'] = 0
                                        branch_df['total_revenue'] = 0
                                    branch_summaries[m] = branch_df
                                except Exception as e:
                                    branch_summaries[m] = None
                            else:
                                branch_summaries[m] = None
                        # 指標リスト
                        indicators = [
                            ('call_count', '架電数', 'Blues'),
                            ('call_hours', '架電時間数', 'Teal'),
                            ('charge_connected', '担当コネクト数', 'Greens'),
                            ('get_appointment', 'アポ獲得数', 'Oranges'),
                            ('total_deals', 'TAAAN商談数', 'Purples'),
                            ('total_approved', '承認数', 'Reds'),
                            ('total_revenue', '報酬合計額', 'Greens'),
                            ('unique_staff_count', 'ユニーク稼働者数', 'Viridis')
                        ]
                        for i in range(0, len(indicators), 3):
                            cols = st.columns(3)
                            for j, (col, label, color) in enumerate(indicators[i:i+3]):
                                with cols[j]:
                                    st.markdown(f"##### {label}（支部別3ヶ月比較）")
                                    plot_df = []
                                    for m in compare_months:
                                        df = branch_summaries.get(m)
                                        if df is not None and col in df.columns:
                                            for _, row in df.iterrows():
                                                plot_df.append({"month": m, "branch": row['branch'], "value": row[col]})
                                    if plot_df:
                                        plot_df = pd.DataFrame(plot_df)
                                        # 統一した色パレットを使用
                                        color_sequence = [branch_colors.get(branch, '#95a5a6') for branch in plot_df['branch'].unique()]
                                        
                                        # 報酬関連はホバーテンプレートに¥マークを追加
                                        is_revenue = 'revenue' in col
                                        hover_template = f'支部: %{{fullData.name}}<br>月: %{{x}}<br>{label}: ¥%{{y:,}}<extra></extra>' if is_revenue else f'支部: %{{fullData.name}}<br>月: %{{x}}<br>{label}: %{{y:,}}<extra></extra>'
                                        
                                        fig = px.line(
                                            plot_df, x='month', y='value', color='branch', markers=True,
                                            color_discrete_sequence=color_sequence,
                                            labels={"value": label, "month": "月", "branch": "支部"}
                                        )
                                        
                                        # ホバーテンプレートを個別に設定
                                        for trace in fig.data:
                                            trace.hovertemplate = hover_template
                                        
                                        fig.update_xaxes(type='category', tickvals=compare_months, ticktext=compare_months)
                                        fig.update_layout(
                                            yaxis_title=label,
                                            yaxis=dict(tickformat=',', separatethousands=True),
                                            legend=dict(
                                                orientation='h',
                                                yanchor='bottom',
                                                y=-0.5,
                                                xanchor='center',
                                                x=0.5,
                                                font=dict(family='"Meiryo", "Yu Gothic", "Noto Sans JP", "sans-serif"', size=12)
                                            )
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.info("データがありません")

                    with subtab4:
                        st.markdown("#### 単位あたり3ヶ月比較")
                        # 指標リスト
                        unit_indicators = [
                            ('total_calls_per_staff', '1人あたり架電数', 'Blues'),
                            ('call_hours_per_staff', '1人あたり架電時間数', 'Teal'),
                            ('charge_connected_per_staff', '1人あたり担当コネクト数', 'Greens'),
                            ('appointments_per_staff', '1人あたりアポ獲得数', 'Oranges'),
                            ('taaan_deals_per_staff', '1人あたりTAAAN商談数', 'Purples'),
                            ('approved_deals_per_staff', '1人あたり承認数', 'Reds'),
                            ('revenue_per_staff', '1人あたり報酬合計額', 'Greens'),
                            ('total_calls_per_hour', '時間あたり架電数', 'Blues'),
                            ('charge_connected_per_hour', '時間あたり担当コネクト数', 'Greens'),
                            ('appointments_per_hour', '時間あたりアポ獲得数', 'Oranges'),
                            ('taaan_deals_per_hour', '時間あたりTAAAN商談数', 'Purples'),
                            ('approved_deals_per_hour', '時間あたり承認数', 'Reds'),
                            ('revenue_per_hour', '時間あたり報酬合計額', 'Greens')
                        ]
                        # 各月の単位あたり指標を計算
                        unit_monthly = {}
                        for m in compare_months:
                            df = branch_summaries.get(m)
                            if df is not None:
                                u = df.copy()
                                u['total_calls_per_staff'] = u['call_count'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['call_hours_per_staff'] = u['call_hours'] / u['unique_staff_count'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['charge_connected_per_staff'] = u['charge_connected'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['appointments_per_staff'] = u['get_appointment'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['taaan_deals_per_staff'] = u['total_deals'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['approved_deals_per_staff'] = u['total_approved'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['revenue_per_staff'] = u['total_revenue'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['total_calls_per_hour'] = u['call_count'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['charge_connected_per_hour'] = u['charge_connected'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['appointments_per_hour'] = u['get_appointment'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['taaan_deals_per_hour'] = u['total_deals'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['approved_deals_per_hour'] = u['total_approved'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['revenue_per_hour'] = u['total_revenue'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                unit_monthly[m] = u
                            else:
                                unit_monthly[m] = None
                        for i in range(0, len(unit_indicators), 3):
                            cols = st.columns(3)
                            for j, (col, label, color) in enumerate(unit_indicators[i:i+3]):
                                with cols[j]:
                                    st.markdown(f"##### {label}（支部別3ヶ月比較）")
                                    plot_df = []
                                    for m in compare_months:
                                        df = unit_monthly.get(m)
                                        if df is not None and col in df.columns:
                                            for _, row in df.iterrows():
                                                plot_df.append({"month": m, "branch": row['branch'], "value": row[col]})
                                    if plot_df:
                                        plot_df = pd.DataFrame(plot_df)
                                        # 統一した色パレットを使用
                                        color_sequence = [branch_colors.get(branch, '#95a5a6') for branch in plot_df['branch'].unique()]
                                        
                                        # 報酬関連はホバーテンプレートに¥マークを追加
                                        is_revenue = 'revenue' in col
                                        if is_revenue:
                                            # 単位あたり報酬は1桁表示
                                            precision = ':.1f' if 'per_staff' in col else ':.0f'
                                            hover_template = f'支部: %{{fullData.name}}<br>月: %{{x}}<br>{label}: ¥%{{y{precision}}}<extra></extra>'
                                        else:
                                            hover_template = f'支部: %{{fullData.name}}<br>月: %{{x}}<br>{label}: %{{y:,.1f}}<extra></extra>'
                                        
                                        fig = px.line(
                                            plot_df, x='month', y='value', color='branch', markers=True,
                                            color_discrete_sequence=color_sequence,
                                            labels={"value": label, "month": "月", "branch": "支部"}
                                        )
                                        
                                        # ホバーテンプレートを個別に設定
                                        for trace in fig.data:
                                            trace.hovertemplate = hover_template
                                        
                                        fig.update_xaxes(type='category', tickvals=compare_months, ticktext=compare_months)
                                        fig.update_layout(
                                            yaxis_title=label,
                                            yaxis=dict(tickformat=',', separatethousands=True),
                                            legend=dict(
                                                orientation='h',
                                                yanchor='bottom',
                                                y=-0.5,
                                                xanchor='center',
                                                x=0.5,
                                                font=dict(family='"Meiryo", "Yu Gothic", "Noto Sans JP", "sans-serif"', size=12)
                                            )
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.info("データがありません")
                
                with tab3:
                    st.subheader("スタッフ別分析")
                    
                    # スタッフ別集計 - カラム名を動的に決定
                    call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_basic.columns else 'successful_calls'
                    
                    staff_summary = df_basic.groupby('staff_name').agg({
                        call_col: 'sum',
                        success_col: 'sum',
                        appointment_col: 'sum',
                        'branch': 'first'  # 支部情報も追加
                    }).reset_index()
                    
                    # カラム名を統一
                    staff_summary.columns = ['staff_name', 'total_calls', 'successful_calls', 'appointments', 'branch']
                    
                    # 支部名を正規化
                    staff_summary['branch'] = staff_summary['branch'].fillna('未設定')
                    
                    # ゼロ除算を避ける
                    staff_summary['success_rate'] = (
                        (staff_summary['successful_calls'] / staff_summary['total_calls'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    staff_summary['appointment_rate'] = (
                        (staff_summary['appointments'] / staff_summary['successful_calls'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    
                    # 支部別の色を定義（支部別分析と統一）
                    branch_colors = {
                        '東京': '#ff6b6b',      # 赤
                        '横浜': '#4ecdc4',      # ティール
                        '名古屋': '#45b7d1',    # 青
                        '福岡': '#96ceb4',      # 緑
                        '新潟': '#feca57',      # オレンジ
                        '大分': '#ff9ff3',      # ピンク
                        '未設定': '#95a5a6',    # グレー
                        '社員': '#6c5ce7'       # 紫（未設定と区別）
                    }
                    
                    # ランキング表示
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🏆 架電数ランキング")
                        st.caption("※%は架電→担当コネクト率（担当コネクト数÷架電数）")
                        top_callers = staff_summary.nlargest(10, 'total_calls')[['staff_name', 'total_calls', 'success_rate', 'branch']]
                        for i, (_, row) in enumerate(top_callers.iterrows(), 1):
                            branch_color = branch_colors.get(row['branch'], '#95a5a6')
                            branch_tag = f'<span style="background-color: {branch_color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-left: 8px;">{row["branch"]}</span>'
                            st.markdown(f"{i}. {row['staff_name']}{branch_tag} - {row['total_calls']}件 ({row['success_rate']}%)", unsafe_allow_html=True)
                    
                    with col2:
                        st.subheader("🎯 アポ獲得率ランキング")
                        st.caption("※%は担当コネクト→アポ獲得率（アポ獲得数÷担当コネクト数）")
                        top_appointments = staff_summary.nlargest(10, 'appointment_rate')[['staff_name', 'appointment_rate', 'appointments', 'branch']]
                        for i, (_, row) in enumerate(top_appointments.iterrows(), 1):
                            branch_color = branch_colors.get(row['branch'], '#95a5a6')
                            branch_tag = f'<span style="background-color: {branch_color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-left: 8px;">{row["branch"]}</span>'
                            st.markdown(f"{i}. {row['staff_name']}{branch_tag} - {row['appointment_rate']}% ({row['appointments']}件)", unsafe_allow_html=True)
                
                with tab4:
                    st.subheader("商材別分析")
                    
                    # 商材別分析のサブタブ
                    subtab1, subtab2, subtab3, subtab4 = st.tabs(["📊 商材別パフォーマンス", "🔗 支部×商材クロス分析", "📈 商材別3ヶ月比較", "📋 商材別詳細"])
                    
                    with subtab1:
                        # 商材別パフォーマンス
                        st.subheader("商材別パフォーマンス")
                        
                        # 日報データから商材別集計（1-3の指標）
                        call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                        appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                        success_col = 'charge_connected' if 'charge_connected' in df_basic.columns else 'successful_calls'
                        
                        # 日報データのみから商材別集計（1-3の指標）
                        daily_product_summary = df_basic.groupby('product').agg({
                            call_col: 'sum',
                            success_col: 'sum',
                            appointment_col: 'sum'
                        }).reset_index()
                        
                        # カラム名を統一
                        daily_product_summary.columns = ['product', 'total_calls', 'charge_connected', 'appointments']
                        
                        # TAAANデータから商材別集計（4-6の指標）
                        taaan_product_summary = pd.DataFrame()
                        taaan_product_data = []
                        if 'product_performance' in summary_data:
                            for product, data in summary_data['product_performance'].items():
                                taaan_product_data.append({
                                    'product': product,
                                    'taaan_deals': data.get('total_deals', 0),
                                    'approved_deals': data.get('total_approved', 0),
                                    'total_revenue': data.get('total_revenue', 0),
                                    'total_potential_revenue': data.get('total_potential_revenue', 0)
                                })
                            taaan_product_summary = pd.DataFrame(taaan_product_data)
                        else:
                            st.warning("⚠️ **TAAANデータが見つかりません**: 商材別分析ではTAAAN関連の指標を表示できません")
                        
                        # 商材別グラフ（TAAANデータのみ）
                        
                        # TAAAN商談数、承認数、売上（TAAANデータ）
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if not taaan_product_summary.empty:
                                fig_product_taaan = px.bar(
                                    taaan_product_summary,
                                    x='product',
                                    y='taaan_deals',
                                    title="商材別TAAAN商談数（TAAANデータ）",
                                    color_discrete_sequence=['#7b1fa2']  # 紫
                                )
                                fig_product_taaan.update_layout(
                                    height=350,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig_product_taaan, use_container_width=True)
                            else:
                                st.info("TAAANデータがありません")
                        
                        with col2:
                            if not taaan_product_summary.empty:
                                fig_product_approved = px.bar(
                                    taaan_product_summary,
                                    x='product',
                                    y='approved_deals',
                                    title="商材別承認数（TAAANデータ）",
                                    color_discrete_sequence=['#c62828']  # 赤
                                )
                                fig_product_approved.update_layout(
                                    height=350,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig_product_approved, use_container_width=True)
                            else:
                                st.info("TAAANデータがありません")
                        
                        with col3:
                            if not taaan_product_summary.empty:
                                fig_product_revenue = px.bar(
                                    taaan_product_summary,
                                    x='product',
                                    y='total_revenue',
                                    title="商材別確定売上（TAAANデータ）",
                                    color_discrete_sequence=['#00695c']  # ダークグリーン
                                )
                                fig_product_revenue.update_layout(
                                    height=350,
                                    yaxis=dict(tickformat=',', separatethousands=True)
                                )
                                st.plotly_chart(fig_product_revenue, use_container_width=True)
                            else:
                                st.info("TAAANデータがありません")
                    
                    with subtab2:
                        # 支部×商材クロス分析
                        st.subheader("支部×商材クロス分析")
                        
                        # 分析指標の選択（ボタン形式）
                        st.write("**分析指標を選択**")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("💼 TAAAN商談数", use_container_width=True, key="btn_taaan"):
                                st.session_state.analysis_metric = "TAAAN商談数"
                        with col2:
                            if st.button("✅ 承認数", use_container_width=True, key="btn_approved"):
                                st.session_state.analysis_metric = "承認数"
                        with col3:
                            if st.button("💰 確定売上", use_container_width=True, key="btn_revenue"):
                                st.session_state.analysis_metric = "確定売上"
                        
                        # デフォルトの分析指標を設定
                        if 'analysis_metric' not in st.session_state:
                            st.session_state.analysis_metric = "TAAAN商談数"
                        
                        analysis_metric = st.session_state.analysis_metric
                        
                        # 現在選択されている指標を表示
                        st.info(f"📊 現在の分析指標: **{analysis_metric}**")
                        
                        # 支部×商材クロス分析データを使用して分析を実行
                        if analysis_metric in ["TAAAN商談数", "承認数", "確定売上"]:
                            try:
                                # 月次サマリーから支部×商材クロス分析データを取得
                                if summary_data and 'branch_product_cross_analysis' in summary_data:
                                    cross_data = summary_data['branch_product_cross_analysis']
                                    
                                    # 指標に応じたデータを選択
                                    metric_mapping = {
                                        "TAAAN商談数": "taaan_deals",
                                        "承認数": "approved_deals",
                                        "確定売上": "total_revenue"
                                    }
                                    
                                    metric_key = metric_mapping[analysis_metric]
                                    metric_data = cross_data.get(metric_key, {})
                                    
                                    if metric_data:
                                        # DataFrameに変換
                                        records = []
                                        for branch, products in metric_data.items():
                                            for product, value in products.items():
                                                records.append({
                                                    'branch': branch,
                                                    'product': product,
                                                    'value': value
                                                })
                                        
                                        if records:
                                            df_cross = pd.DataFrame(records)
                                            
                                            # ピボットテーブルを作成
                                            cross_analysis = df_cross.pivot_table(
                                                values='value',
                                                index='branch',
                                                columns='product',
                                                aggfunc='sum',
                                                fill_value=0
                                            )
                                            
                                            # 合計行と列を追加
                                            cross_analysis['合計'] = cross_analysis.sum(axis=1)
                                            cross_analysis.loc['合計'] = cross_analysis.sum()
                                            
                                            # 1. ヒートマップの数値をカンマ区切りで表示
                                            z = cross_analysis.iloc[:-1, :-1].values  # 数値
                                            z_text = cross_analysis.iloc[:-1, :-1].copy()
                                            for col in z_text.columns:
                                                z_text[col] = z_text[col].apply(lambda v: f"{int(v):,}" if analysis_metric != "確定売上" else f"¥{int(v):,}")
                                            text = z_text.values  # カンマ区切り文字列
                                            
                                            import plotly.graph_objects as go
                                            fig_cross = go.Figure(
                                                data=go.Heatmap(
                                                    z=z,
                                                    x=cross_analysis.columns[:-1],
                                                    y=cross_analysis.index[:-1],
                                                    text=text,
                                                    texttemplate="%{text}",
                                                    colorscale="Blues",
                                                    colorbar=dict(title=analysis_metric)
                                                )
                                            )
                                            # ホバー時の情報を日本語に設定
                                            fig_cross.update_traces(
                                                hovertemplate="<b>支部</b>: %{y}<br><b>商材</b>: %{x}<br><b>" + analysis_metric + "</b>: %{z:,.0f}<extra></extra>"
                                            )
                                            
                                            fig_cross.update_layout(
                                                title=f"{analysis_metric}の支部×商材クロス分析",
                                                height=500,
                                                xaxis_title="商材",
                                                yaxis_title="支部"
                                            )
                                            st.plotly_chart(fig_cross, use_container_width=True)
                                            
                                            # クロス分析テーブルを表示
                                            st.subheader("支部×商材クロス分析テーブル")
                                            
                                            # 数値フォーマットを改善（カンマ区切り）
                                            def format_cross_table_value(value):
                                                if pd.isna(value):
                                                    return ""
                                                elif isinstance(value, (int, float)):
                                                    if analysis_metric == "確定売上":
                                                        return f"¥{value:,.0f}"
                                                    else:
                                                        return f"{value:,.0f}"
                                                return str(value)
                                            
                                            # フォーマットされたテーブルを表示
                                            formatted_cross_analysis = cross_analysis.copy()
                                            for col in formatted_cross_analysis.columns:
                                                formatted_cross_analysis[col] = formatted_cross_analysis[col].apply(format_cross_table_value)
                                            
                                            st.dataframe(
                                                formatted_cross_analysis,
                                                use_container_width=True
                                            )
                                            
                                            # 統計情報（カードスタイル）
                                            st.subheader("📊 統計情報")
                                            
                                            # 2. 統計情報カードのCSSを修正
                                            card_style = """
                                            <style>
                                            .metric-card {
                                                background-color: #f0f2f6;
                                                padding: 1rem;
                                                border-radius: 0.5rem;
                                                border-left: 4px solid #1f77b4;
                                                margin: 0.5rem 0;
                                                min-height: 110px;
                                                display: flex;
                                                flex-direction: column;
                                                align-items: center;
                                                justify-content: center;
                                            }
                                            .metric-title {
                                                font-size: 0.9rem;
                                                color: #666;
                                                margin-bottom: 0.5rem;
                                            }
                                            .metric-value {
                                                font-size: 1.5rem;
                                                font-weight: bold;
                                                color: #1f77b4;
                                            }
                                            </style>
                                            """
                                            st.markdown(card_style, unsafe_allow_html=True)
                                            
                                            col1, col2, col3 = st.columns(3)
                                            
                                            with col1:
                                                total_value = cross_analysis.loc['合計', '合計']
                                                total_display = f"{total_value:,}" if analysis_metric != "確定売上" else f"¥{total_value:,}"
                                                st.markdown(f"""
                                                <div class="metric-card">
                                                    <div class="metric-title">総{analysis_metric}</div>
                                                    <div class="metric-value">{total_display}</div>
                                                </div>
                                                """, unsafe_allow_html=True)
                                            
                                            with col2:
                                                max_branch = cross_analysis.iloc[:-1, :-1].sum(axis=1).idxmax()
                                                max_branch_value = cross_analysis.loc[max_branch, '合計']
                                                branch_display = f"{max_branch_value:,}" if analysis_metric != "確定売上" else f"¥{max_branch_value:,}"
                                                st.markdown(f"""
                                                <div class="metric-card">
                                                    <div class="metric-title">最高{analysis_metric}支部</div>
                                                    <div class="metric-value">{max_branch}<br><small>{branch_display}</small></div>
                                                </div>
                                                """, unsafe_allow_html=True)
                                            
                                            with col3:
                                                max_product = cross_analysis.iloc[:-1, :-1].sum().idxmax()
                                                max_product_value = cross_analysis.loc['合計', max_product]
                                                product_display = f"{max_product_value:,}" if analysis_metric != "確定売上" else f"¥{max_product_value:,}"
                                                st.markdown(f"""
                                                <div class="metric-card">
                                                    <div class="metric-title">最高{analysis_metric}商材</div>
                                                    <div class="metric-value">{max_product}<br><small>{product_display}</small></div>
                                                </div>
                                                """, unsafe_allow_html=True)
                                            
                                        else:
                                            st.warning("支部×商材のデータが見つかりません。")
                                    else:
                                        st.warning(f"{analysis_metric}の支部×商材クロス分析データが見つかりません。")
                                else:
                                    st.warning("月次サマリーデータに支部×商材クロス分析データが含まれていません。")
                                    
                            except Exception as e:
                                st.error(f"支部×商材クロス分析の実行中にエラーが発生しました: {str(e)}")
                                st.info("💡 データ構造の確認が必要です。")
                    
                    with subtab3:
                        # 商材別3ヶ月比較
                        st.subheader("商材別3ヶ月比較")
                        
                        # 現在の月から過去3ヶ月のデータを取得
                        def get_prev_months(month_str, n=3):
                            try:
                                from datetime import datetime, timedelta
                                import calendar
                                
                                # 月文字列をパース
                                year, month = map(int, month_str.split('-'))
                                months = []
                                
                                for i in range(n):
                                    if month - i <= 0:
                                        new_month = 12 + (month - i)
                                        new_year = year - 1
                                    else:
                                        new_month = month - i
                                        new_year = year
                                    months.append(f"{new_year:04d}-{new_month:02d}")
                                
                                return months[::-1]  # 古い順に並び替え
                            except:
                                return [month_str]
                        
                        target_months = get_prev_months(selected_month, 3)
                        
                        # 過去3ヶ月のTAAANデータを読み込み
                        monthly_taaan_data = {}  # TAAANデータ
                        
                        for month in target_months:
                            try:
                                basic_data, detail_data, summary_data = load_data(month)
                                
                                # TAAANデータ（月次サマリー）を取得
                                if summary_data and 'product_performance' in summary_data:
                                    taaan_product_data = []
                                    for product, data in summary_data['product_performance'].items():
                                        # TAAANデータのみを使用（日報データは除外）
                                        # total_deals, total_approved, total_revenueはTAAANデータ
                                        # total_calls, total_hours, total_appointmentsは日報データ
                                        taaan_product_data.append({
                                            'product': product,
                                            'taaan_deals': data.get('total_deals', 0),  # TAAAN商談数
                                            'approved_deals': data.get('total_approved', 0),  # TAAAN承認数
                                            'total_revenue': data.get('total_revenue', 0),  # TAAAN確定売上
                                            'month': month
                                        })
                                    if taaan_product_data:
                                        taaan_summary = pd.DataFrame(taaan_product_data)
                                        monthly_taaan_data[month] = taaan_summary
                                    
                            except Exception as e:
                                st.warning(f"⚠️ {month}のデータ読み込みに失敗: {str(e)}")
                                continue
                        
                        # デバッグ情報
                        st.info(f"🔍 **対象月**: {', '.join(target_months)}")
                        st.info(f"💼 **TAAANデータ読み込み成功月**: {', '.join(monthly_taaan_data.keys()) if monthly_taaan_data else 'なし'}")
                        
                        # TAAANデータの3ヶ月比較
                        if not monthly_taaan_data:
                            st.warning("過去3ヶ月のTAAANデータが見つかりません。")
                        else:
                            st.markdown("### 💼 TAAANデータ（TAAAN商談数、承認数、確定売上）の3ヶ月推移")
                            st.info("📊 **データソース**: この分析ではTAAANシステムからの商談データ（total_deals、total_approved、total_revenue）のみを使用しています。日報データ（total_calls、total_hours、total_appointments）は含まれていません。")
                            
                            # 全ての月のTAAANデータを結合
                            all_taaan_data = pd.concat(monthly_taaan_data.values(), ignore_index=True)
                            
                            # 指標選択ボタン
                            st.markdown("#### 比較指標")
                            taaan_metric_options = ["TAAAN商談数", "承認数", "確定売上"]
                            taaan_metric_cols = st.columns(len(taaan_metric_options))
                            
                            # セッション状態で選択された指標を管理
                            if 'taaan_selected_metric' not in st.session_state:
                                st.session_state.taaan_selected_metric = "TAAAN商談数"
                            
                            for i, metric in enumerate(taaan_metric_options):
                                with taaan_metric_cols[i]:
                                    if st.button(
                                        metric,
                                        key=f"taaan_metric_{metric}",
                                        use_container_width=True,
                                        type="primary" if st.session_state.taaan_selected_metric == metric else "secondary"
                                    ):
                                        st.session_state.taaan_selected_metric = metric
                            
                            taaan_comparison_metric = st.session_state.taaan_selected_metric
                            
                            # 商材選択 - 3ヶ月間で1件以上データがある商材のみデフォルト選択
                            available_taaan_products = sorted(all_taaan_data['product'].unique())
                            
                            # 3ヶ月間で1件以上データがある商材を動的に抽出
                            try:
                                # 各商材の3ヶ月間合計を計算
                                product_totals = all_taaan_data.groupby('product')[['taaan_deals', 'approved_deals', 'total_revenue']].sum()
                                # いずれかの指標で1以上の値がある商材を抽出
                                active_products = product_totals[(product_totals > 0).any(axis=1)].index.tolist()
                                # 商材名でソート
                                active_products = sorted(active_products)
                                
                                # デバッグ情報を表示
                                st.info(f"💡 **自動選択**: 3ヶ月間でデータがある商材（{len(active_products)}件）をデフォルト選択しています。全{len(available_taaan_products)}件から選択可能です。")
                                
                            except Exception as e:
                                # エラーが発生した場合は全商材をデフォルト選択
                                active_products = available_taaan_products
                                st.warning(f"⚠️ 商材の動的選択に失敗しました。全商材を表示します。エラー: {str(e)}")
                            
                            selected_taaan_products = st.multiselect(
                                "比較したい商材を選択（複数選択可）",
                                available_taaan_products,
                                default=active_products,
                                key="taaan_products"
                            )
                            
                            if selected_taaan_products:
                                # 選択された商材のデータをフィルタ
                                filtered_taaan_data = all_taaan_data[all_taaan_data['product'].isin(selected_taaan_products)]
                                
                                taaan_metric_col_mapping = {
                                    "TAAAN商談数": "taaan_deals",
                                    "承認数": "approved_deals",
                                    "確定売上": "total_revenue"
                                }
                                
                                # 月次推移グラフ
                                fig_taaan_trend = px.line(
                                    filtered_taaan_data,
                                    x='month',
                                    y=taaan_metric_col_mapping[taaan_comparison_metric],
                                    color='product',
                                    title=f"TAAANデータ: 商材別{taaan_comparison_metric}の3ヶ月推移",
                                    markers=True
                                )
                                fig_taaan_trend.update_layout(
                                    height=400,
                                    xaxis_title="月",
                                    yaxis_title=taaan_comparison_metric,
                                    # Y軸の数字表記をカンマ区切りに設定
                                    yaxis=dict(
                                        tickformat=',',
                                        separatethousands=True
                                    ),
                                    # X軸を月次ベースに設定
                                    xaxis=dict(
                                        type='category',
                                        categoryorder='category ascending'
                                    )
                                )
                                
                                # ホバー時の情報を日本語に設定
                                fig_taaan_trend.update_traces(
                                    hovertemplate="<b>月</b>: %{x}<br><b>商材</b>: %{fullData.name}<br><b>" + taaan_comparison_metric + "</b>: %{y:,.0f}<extra></extra>"
                                )
                                st.plotly_chart(fig_taaan_trend, use_container_width=True)
                                
                                # 月次比較テーブル
                                st.subheader("月次比較テーブル")
                                pivot_taaan_comparison = filtered_taaan_data.pivot_table(
                                    values=taaan_metric_col_mapping[taaan_comparison_metric],
                                    index='product',
                                    columns='month',
                                    aggfunc='sum',
                                    fill_value=0
                                )
                                
                                # 増減率の計算
                                if len(pivot_taaan_comparison.columns) >= 2:
                                    latest_month = pivot_taaan_comparison.columns[-1]
                                    prev_month = pivot_taaan_comparison.columns[-2]
                                    pivot_taaan_comparison['増減率(%)'] = (
                                        (pivot_taaan_comparison[latest_month] - pivot_taaan_comparison[prev_month]) / 
                                        pivot_taaan_comparison[prev_month].replace(0, float('nan')) * 100
                                    ).round(1)
                                
                                # 数値フォーマットを改善（カンマ区切り）
                                def format_number(value):
                                    if pd.isna(value):
                                        return ""
                                    elif isinstance(value, (int, float)):
                                        if taaan_comparison_metric == "確定売上":
                                            return f"¥{value:,.0f}"
                                        else:
                                            return f"{value:,.0f}"
                                    return str(value)
                                
                                # フォーマットされたテーブルを表示
                                formatted_pivot = pivot_taaan_comparison.copy()
                                for col in formatted_pivot.columns:
                                    if col != '増減率(%)':
                                        formatted_pivot[col] = formatted_pivot[col].apply(format_number)
                                    else:
                                        formatted_pivot[col] = formatted_pivot[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
                                
                                st.dataframe(formatted_pivot, use_container_width=True)
                            else:
                                st.info("比較したい商材を選択してください。")
                    
                    with subtab4:
                        # 商材別詳細
                        st.subheader("商材別詳細")
                        
                        # TAAANデータの詳細テーブル
                        if not taaan_product_summary.empty:
                            st.subheader("📈 TAAANデータ（TAAAN商談数・承認数・確定売上）")
                            
                            # 承認率の計算
                            taaan_product_summary['approval_rate'] = (
                                (taaan_product_summary['approved_deals'] / taaan_product_summary['taaan_deals'] * 100)
                                .fillna(0)
                                .round(1)
                            )
                            
                            # 表示するカラムを選択
                            taaan_display_columns = [
                                'product', 'taaan_deals', 'approved_deals', 'total_revenue', 'total_potential_revenue',
                                'approval_rate'
                            ]
                            
                            # カラム名の日本語マッピング
                            taaan_column_labels = {
                                'product': '商材',
                                'taaan_deals': 'TAAAN商談数',
                                'approved_deals': '承認数',
                                'total_revenue': '確定売上',
                                'total_potential_revenue': '潜在売上',
                                'approval_rate': '承認率(%)'
                            }
                            
                            # 合計行を追加
                            taaan_total_row = {
                                'product': '合計',
                                'taaan_deals': taaan_product_summary['taaan_deals'].sum(),
                                'approved_deals': taaan_product_summary['approved_deals'].sum(),
                                'total_revenue': taaan_product_summary['total_revenue'].sum(),
                                'total_potential_revenue': taaan_product_summary['total_potential_revenue'].sum(),
                                'approval_rate': 0  # 合計行では計算しない
                            }
                            
                            # 合計行を追加
                            taaan_display_data = pd.concat([
                                taaan_product_summary[taaan_display_columns],
                                pd.DataFrame([taaan_total_row])
                            ], ignore_index=True)
                            
                            # テーブル表示
                            st.dataframe(
                                taaan_display_data.rename(columns=taaan_column_labels),
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.warning("⚠️ TAAANデータが見つかりません。商材別詳細を表示するにはTAAANデータが必要です。")
                
                with tab5:
                    st.subheader("詳細データ")
                    
                    # フィルター
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # 支部名を正規化（nullを「未設定」に変更）
                        branch_options = ['全て'] + [b if pd.notna(b) else '未設定' for b in df_basic['branch'].unique()]
                        selected_branch = st.selectbox(
                            "支部でフィルター",
                            branch_options
                        )
                    
                    with col2:
                        selected_staff = st.selectbox(
                            "スタッフでフィルター",
                            ['全て'] + list(df_basic['staff_name'].unique())
                        )
                    
                    # フィルター適用
                    filtered_df = df_basic.copy()
                    if selected_branch != '全て':
                        # 支部名の正規化を考慮
                        if selected_branch == '未設定':
                            filtered_df = filtered_df[filtered_df['branch'].isna()]
                        else:
                            filtered_df = filtered_df[filtered_df['branch'] == selected_branch]
                    if selected_staff != '全て':
                        filtered_df = filtered_df[filtered_df['staff_name'] == selected_staff]
                    
                    # 詳細テーブルの日本語ヘッダーマッピング
                    detail_column_labels = {
                        'date': '日付',
                        'product': '商材',
                        'call_hours': '架電時間(h)',
                        'call_count': '架電数',
                        'reception_bk': '受付ブロック',
                        'no_one_in_charge': '担当者不在',
                        'disconnect': '切断',
                        'charge_connected': '担当コネクト',
                        'charge_bk': '担当ブロック',
                        'get_appointment': 'アポ獲得',
                        'staff_name': 'スタッフ名',
                        'branch': '支部',
                        'join_date': '入社日',
                        'product_type': '商材タイプ'
                    }
                    
                    # 表示用DataFrameを作成（カラム名を日本語化）
                    display_df = filtered_df.sort_values('date', ascending=False).copy()
                    display_df.columns = [detail_column_labels.get(col, col) for col in display_df.columns]
                    
                    # 数値データを日本語フォーマットに変更
                    numeric_columns = ['架電数', '受付ブロック', '担当者不在', '切断', '担当コネクト', '担当ブロック', 'アポ獲得']
                    for col in numeric_columns:
                        if col in display_df.columns:
                            display_df[col] = display_df[col].fillna(0).astype(int)
                    
                    # 架電時間は小数点1桁表示
                    if '架電時間(h)' in display_df.columns:
                        display_df['架電時間(h)'] = display_df['架電時間(h)'].fillna(0).round(1)
                    
                    # 詳細テーブル
                    st.dataframe(
                        display_df,
                        use_container_width=True
                    )
                    
                    # CSVダウンロード（日本語ヘッダー付き）
                    csv = display_df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 CSVダウンロード",
                        data=csv,
                        file_name=f'架電データ_{selected_month}.csv',
                        mime='text/csv'
                    )
        else:
            st.error("❌ 単月詳細データの読み込みに失敗しました")



# フッター
st.divider()
st.caption("© 2025 架電ダッシュボード - Streamlit版")