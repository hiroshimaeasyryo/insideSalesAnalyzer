import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# ページ設定
st.set_page_config(
    page_title="架電ダッシュボード",
    page_icon="📊",
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

# ここからデバッグ情報を必ず表示

def show_debug_info():
    try:
        cwd = os.getcwd()
        data_exists = os.path.exists('dataset')
        data_list = os.listdir('dataset') if data_exists else []
        st.markdown(
            f'''
            <div style="border:3px solid red; padding:16px; background:#fff3cd; color:#000; font-size:18px; margin-bottom:24px;">
            <b>【デバッグ情報】</b><br>
            <b>現在のディレクトリ:</b> {cwd}<br>
            <b>datasetディレクトリの存在:</b> {data_exists}<br>
            <b>datasetディレクトリ内のファイル数:</b> {len(data_list)}<br>
            <b>datasetディレクトリ内のファイル:</b><br>
            {'<br>'.join(data_list[:10]) if data_list else '（なし）'}
            </div>
            ''',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.markdown(f'<div style="border:3px solid red; padding:16px; background:#fff3cd; color:#000; font-size:18px;">デバッグ情報の取得に失敗: {e}</div>', unsafe_allow_html=True)

show_debug_info()

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
        analysis_type = st.selectbox(
            "分析タイプを選択",
            ["📈 月次分析", "📊 単月詳細"],
            index=0
        )
        
        # 月選択（単月詳細の場合のみ表示）
        if analysis_type == "📊 単月詳細":
            st.subheader("📅 月選択")
            # 直近6ヶ月のリストを作成
            current_date = datetime.now()
            months = []
            for i in range(6):
                date = current_date - timedelta(days=30*i)
                month_str = date.strftime('%Y-%m')
                months.append(month_str)
            selected_month = st.selectbox(
                "表示する月を選択",
                months,
                index=0
            )
        else:
            # 月次分析の場合は最新月を自動選択
            current_date = datetime.now()
            selected_month = current_date.strftime('%Y-%m')
        
        st.divider()
        
        # ヘルプ
        st.subheader("ℹ️ ヘルプ")
        if analysis_type == "📈 月次分析":
            st.markdown("""
            - **月次分析**: 全期間の月次推移データ
            - **PDF出力**: ブラウザの印刷機能を使用
            """)
        else:
            st.markdown("""
            - **単月詳細**: 選択月の詳細分析
            - **PDF出力**: ブラウザの印刷機能を使用
            """)

    # メインコンテンツ
    st.title("📊 架電ダッシュボード")
    
    # データディレクトリの取得関数
    def get_data_dir():
        """データディレクトリのパスを取得"""
        current_dir = os.getcwd()
        data_dir = os.path.join(current_dir, 'dataset')
        if not os.path.exists(data_dir):
            # 代替パスを試す
            alt_data_dir = 'dataset'
            if os.path.exists(alt_data_dir):
                data_dir = alt_data_dir
            else:
                return None
        return data_dir
    
    # データ読み込み関数
    @st.cache_data
    def load_data(month):
        """指定月のデータを読み込み"""
        try:
            # 現在のディレクトリを確認
            current_dir = os.getcwd()
            st.write(f"🔍 データ読み込み開始: {month}")
            st.write(f"現在のディレクトリ: {current_dir}")
            
            # データディレクトリの存在確認
            data_dir = get_data_dir()
            if data_dir is None:
                st.error("❌ データディレクトリが見つかりません")
                st.write("利用可能なディレクトリ:")
                try:
                    for item in os.listdir(current_dir):
                        if os.path.isdir(item):
                            st.write(f"  📁 {item}")
                        else:
                            st.write(f"  📄 {item}")
                except Exception as e:
                    st.error(f"ディレクトリ一覧の取得に失敗: {e}")
                return None, None, None
            
            st.write(f"✅ データディレクトリ: {data_dir}")
            
            # ファイルパスの構築
            basic_file = os.path.join(data_dir, f'基本分析_{month}.json')
            detail_file = os.path.join(data_dir, f'詳細分析_{month}.json')
            summary_file = os.path.join(data_dir, f'月次サマリー_{month}.json')
            
            st.write(f"📄 基本分析ファイル: {basic_file}")
            st.write(f"📄 詳細分析ファイル: {detail_file}")
            st.write(f"📄 月次サマリーファイル: {summary_file}")
            
            # ファイルの存在確認
            if not os.path.exists(basic_file):
                st.error(f"❌ 基本分析ファイルが見つかりません: {basic_file}")
                return None, None, None
            if not os.path.exists(detail_file):
                st.error(f"❌ 詳細分析ファイルが見つかりません: {detail_file}")
                return None, None, None
            if not os.path.exists(summary_file):
                st.error(f"❌ 月次サマリーファイルが見つかりません: {summary_file}")
                return None, None, None
            
            st.write("✅ すべてのファイルが存在します")
            
            # ファイルサイズの確認
            basic_size = os.path.getsize(basic_file)
            detail_size = os.path.getsize(detail_file)
            summary_size = os.path.getsize(summary_file)
            st.write(f"📊 ファイルサイズ: 基本分析({basic_size} bytes), 詳細分析({detail_size} bytes), 月次サマリー({summary_size} bytes)")
            
            # 基本分析データ
            with open(basic_file, 'r', encoding='utf-8') as f:
                basic_data = json.load(f)
            
            # 詳細分析データ
            with open(detail_file, 'r', encoding='utf-8') as f:
                detail_data = json.load(f)
            
            # 月次サマリーデータ
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
                
            st.success(f"✅ {month}のデータを正常に読み込みました")
            return basic_data, detail_data, summary_data
            
        except FileNotFoundError as e:
            st.error(f"❌ ファイルが見つかりません: {e}")
            return None, None, None
        except json.JSONDecodeError as e:
            st.error(f"❌ JSONファイルの解析に失敗しました: {e}")
            return None, None, None
        except Exception as e:
            st.error(f"❌ 予期しないエラーが発生しました: {e}")
            st.write(f"エラーの詳細: {type(e).__name__}")
            return None, None, None
    
    # 分析タイプに応じたコンテンツ表示
    if analysis_type == "📈 月次分析":
        st.header("📈 月次分析")
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
                    if 'taaaan_entries' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['taaaan_entries'], mode='lines+markers', name='TAAAN入力'))
                    if 'approved_deals' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['approved_deals'], mode='lines+markers', name='メーカーからの承認'))
                    if 'taaaan_rate' in conv_total.columns:
                        fig.add_trace(go.Scatter(x=conv_total['month'], y=conv_total['taaaan_rate']*100, mode='lines+markers', name='アポ→TAAAN率(%)', yaxis='y2'))
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
                               int(latest.get('taaaan_entries', 0)) if pd.notnull(latest.get('taaaan_entries')) else 0)
                    col3.metric("メーカーからの承認", 
                               int(latest.get('approved_deals', 0)) if pd.notnull(latest.get('approved_deals')) else 0)
                    col4.metric("アポ→TAAAN率", 
                               f"{latest.get('taaaan_rate', 0)*100:.1f}%" if pd.notnull(latest.get('taaaan_rate')) else 'N/A')
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
    
    else:  # 単月詳細
        st.header("📊 単月詳細分析")
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
                        # メイン商材の処理
                        main = activity.get("main_product", {})
                        if main.get("call_count", 0) > 0:  # 架電数が0より大きい場合のみ追加
                            record = {
                                "date": activity.get("date"),
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
                                    "date": activity.get("date"),
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
                total_revenue = summary_data['key_metrics'].get('total_revenue', 0) if 'key_metrics' in summary_data else 0
                total_potential_revenue = summary_data['key_metrics'].get('total_potential_revenue', 0) if 'key_metrics' in summary_data else 0

                # --- カードスタイルで指標を表示 ---
                card_cols = st.columns(4)
                card_cols[0].metric("架電数", f"{total_calls:,}件")
                card_cols[1].metric("担当コネクト数", f"{charge_connected:,}件")
                card_cols[2].metric("アポ獲得数", f"{appointments:,}件")
                card_cols[3].metric("TAAAN商談数", f"{total_deals:,}件")

                # --- 売上指標を表示 ---
                revenue_cols = st.columns(3)
                revenue_cols[0].metric("確定売上", f"¥{total_revenue:,}", help="承認済み商談の売上")
                revenue_cols[1].metric("潜在売上", f"¥{total_potential_revenue:,}", help="承認待ち・要対応商談の売上")
                revenue_cols[2].metric("総売上", f"¥{total_revenue + total_potential_revenue:,}", help="確定売上 + 潜在売上")

                # --- 変換率の計算 ---
                call_to_connect = (charge_connected / total_calls * 100) if total_calls > 0 else 0
                connect_to_appointment = (appointments / charge_connected * 100) if charge_connected > 0 else 0
                appointment_to_taaaan = (total_deals / appointments * 100) if appointments > 0 else 0
                taaaan_to_approved = (total_approved / total_deals * 100) if total_deals > 0 else 0

                # --- 変換率をカードで表示 ---
                rate_cols = st.columns(4)
                rate_cols[0].metric("架電→担当率", f"{call_to_connect:.1f}%")
                rate_cols[1].metric("担当→アポ率", f"{connect_to_appointment:.1f}%")
                rate_cols[2].metric("アポ→TAAAN率", f"{appointment_to_taaaan:.1f}%")
                rate_cols[3].metric("TAAAN→承認率", f"{taaaan_to_approved:.1f}%")

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
                    
                    # 日付をdatetimeに変換
                    daily_trend['date'] = pd.to_datetime(daily_trend['date'])
                    daily_trend = daily_trend.sort_values('date')
                    
                    # 土日判定を追加
                    daily_trend['is_weekend'] = daily_trend['date'].dt.dayofweek.isin([5, 6])  # 5=土曜日, 6=日曜日
                    
                    with trend_tab1:
                        # 日別トレンドグラフ
                        fig_trend = go.Figure()
                        
                        # 土日の背景色を追加
                        for i, row in daily_trend.iterrows():
                            if row['is_weekend']:
                                fig_trend.add_vrect(
                                    x0=row['date'] - pd.Timedelta(hours=12),
                                    x1=row['date'] + pd.Timedelta(hours=12),
                                    fillcolor="lightgray",
                                    opacity=0.3,
                                    layer="below",
                                    line_width=0,
                                    annotation_text="" if i == daily_trend.index[0] or not daily_trend.loc[i-1, 'is_weekend'] else "",
                                    annotation_position="top left"
                                )
                        
                        # 総架電数
                        fig_trend.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['total_calls'],
                            mode='lines+markers',
                            name='総架電数',
                            line=dict(color='blue', width=2),
                            yaxis='y1'
                        ))
                        # 担当コネクト数
                        fig_trend.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['successful_calls'],
                            mode='lines+markers',
                            name='担当コネクト数',
                            line=dict(color='green', width=2),
                            yaxis='y1'
                        ))
                        # アポ獲得数（右軸）
                        fig_trend.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['appointments'],
                            mode='lines+markers',
                            name='アポ獲得数(右軸)',
                            line=dict(color='red', width=2, dash='dot'),
                            yaxis='y2'
                        ))
                        
                        fig_trend.update_layout(
                            title="日別架電トレンド",
                            xaxis_title="日付",
                            yaxis=dict(title='件数', side='left', showgrid=True, zeroline=True),
                            yaxis2=dict(title='アポ獲得数', side='right', overlaying='y', showgrid=False, zeroline=False),
                            height=400,
                            legend=dict(orientation='h')
                        )
                        
                        st.plotly_chart(fig_trend, use_container_width=True)
                    
                    with trend_tab2:
                        # 累計値トレンドグラフ
                        daily_trend['cumulative_calls'] = daily_trend['total_calls'].cumsum()
                        daily_trend['cumulative_connects'] = daily_trend['successful_calls'].cumsum()
                        daily_trend['cumulative_appointments'] = daily_trend['appointments'].cumsum()
                        
                        fig_cumulative = go.Figure()
                        
                        # 土日の背景色を追加
                        for i, row in daily_trend.iterrows():
                            if row['is_weekend']:
                                fig_cumulative.add_vrect(
                                    x0=row['date'] - pd.Timedelta(hours=12),
                                    x1=row['date'] + pd.Timedelta(hours=12),
                                    fillcolor="lightgray",
                                    opacity=0.3,
                                    layer="below",
                                    line_width=0,
                                    annotation_text="" if i == daily_trend.index[0] or not daily_trend.loc[i-1, 'is_weekend'] else "",
                                    annotation_position="top left"
                                )
                        
                        # 累計総架電数
                        fig_cumulative.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['cumulative_calls'],
                            mode='lines+markers',
                            name='累計総架電数',
                            line=dict(color='blue', width=2),
                            yaxis='y1'
                        ))
                        # 累計担当コネクト数
                        fig_cumulative.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['cumulative_connects'],
                            mode='lines+markers',
                            name='累計担当コネクト数',
                            line=dict(color='green', width=2),
                            yaxis='y1'
                        ))
                        # 累計アポ獲得数（右軸）
                        fig_cumulative.add_trace(go.Scatter(
                            x=daily_trend['date'],
                            y=daily_trend['cumulative_appointments'],
                            mode='lines+markers',
                            name='累計アポ獲得数(右軸)',
                            line=dict(color='red', width=2, dash='dot'),
                            yaxis='y2'
                        ))
                        
                        fig_cumulative.update_layout(
                            title="累計値トレンド",
                            xaxis_title="日付",
                            yaxis=dict(title='累計件数', side='left', showgrid=True, zeroline=True),
                            yaxis2=dict(title='累計アポ獲得数', side='right', overlaying='y', showgrid=False, zeroline=False),
                            height=400,
                            legend=dict(orientation='h')
                        )
                        
                        st.plotly_chart(fig_cumulative, use_container_width=True)
                
                with tab2:
                    st.subheader("支部別分析")
                    
                    # データソースの説明
                    st.info("ℹ️ **データソース**: 支部別分析は各スタッフの日次活動データから集計しています（メイン商材 + サブ商材）")
                    
                    # 支部別集計 - カラム名を動的に決定
                    call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_basic.columns else 'successful_calls'
                    
                    # 支部名の正規化（nullを「未設定」に変更）を先に行う
                    df_basic_for_branch = df_basic.copy()
                    df_basic_for_branch['branch'] = df_basic_for_branch['branch'].fillna('未設定')
                    
                    # ユニーク稼働者数を計算
                    unique_staff_by_branch = df_basic_for_branch.groupby('branch')['staff_name'].nunique().reset_index()
                    unique_staff_by_branch.columns = ['branch', 'unique_staff_count']
                    
                    branch_summary = df_basic_for_branch.groupby('branch').agg({
                        call_col: 'sum',
                        success_col: 'sum',
                        appointment_col: 'sum'
                    }).reset_index()
                
                    # カラム名を統一
                    branch_summary.columns = ['branch', 'total_calls', 'charge_connected', 'appointments']
                    
                    # ユニーク稼働者数を結合
                    branch_summary = branch_summary.merge(unique_staff_by_branch, on='branch', how='left')
                    
                    # TAAANデータを先に処理
                    if 'branch_performance' in summary_data:
                        taaaan_branch_data = {}
                        for branch, data in summary_data['branch_performance'].items():
                            taaaan_branch_data[branch] = {
                                'total_deals': data.get('total_deals', 0),
                                'total_approved': data.get('total_approved', 0),
                                'total_revenue': data.get('total_revenue', 0),
                                'total_potential_revenue': data.get('total_potential_revenue', 0)
                            }
                                
                            # デバッグ情報を表示
                            st.info(f"ℹ️ **TAAANデータ確認**: {len(taaaan_branch_data)}支部のデータを読み込みました")
                            
                            # 支部別データにTAAAN情報を追加
                            branch_summary['taaaan_deals'] = branch_summary['branch'].map(
                                lambda x: taaaan_branch_data.get(x, {}).get('total_deals', 0)
                            )
                            branch_summary['approved_deals'] = branch_summary['branch'].map(
                                lambda x: taaaan_branch_data.get(x, {}).get('total_approved', 0)
                            )
                            branch_summary['total_revenue'] = branch_summary['branch'].map(
                                lambda x: taaaan_branch_data.get(x, {}).get('total_revenue', 0)
                            )
                            branch_summary['total_potential_revenue'] = branch_summary['branch'].map(
                                lambda x: taaaan_branch_data.get(x, {}).get('total_potential_revenue', 0)
                            )
                    else:
                        # TAAANデータが存在しない場合
                        branch_summary['taaaan_deals'] = 0
                        branch_summary['approved_deals'] = 0
                        branch_summary['total_revenue'] = 0
                        branch_summary['total_potential_revenue'] = 0
                        st.warning("⚠️ **TAAANデータが見つかりません**: 支部別分析ではTAAAN関連の指標を表示できません")
                    
                    # 変換率の計算
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
                        (branch_summary['approved_deals'] / branch_summary['taaaan_deals'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    
                    # データ整合性の警告
                    if 'key_metrics' in summary_data:
                        summary_total = summary_data['key_metrics'].get('total_calls', 0)
                        branch_total = branch_summary['total_calls'].sum()
                        summary_taaaan = summary_data['key_metrics'].get('total_deals', 0)
                        branch_taaaan = branch_summary['taaaan_deals'].sum()
                        summary_approved = summary_data['key_metrics'].get('total_approved', 0)
                        branch_approved = branch_summary['approved_deals'].sum()
                        
                        # 架電数の整合性チェック
                        if summary_total != branch_total:
                            diff = summary_total - branch_total
                            if diff > 0:
                                st.warning(f"⚠️ **架電数整合性**: 月次サマリー({summary_total:,}件)と支部別合計({branch_total:,}件)の差: {diff:,}件")
                            else:
                                st.info(f"ℹ️ **架電数整合性**: 支部別合計({branch_total:,}件)が月次サマリー({summary_total:,}件)より{abs(diff):,}件多い")
                        
                        # TAAAN商談数の整合性チェック
                        if summary_taaaan != branch_taaaan:
                            diff = summary_taaaan - branch_taaaan
                            st.warning(f"⚠️ **TAAAN商談数整合性**: 月次サマリー({summary_taaaan:,}件)と支部別合計({branch_taaaan:,}件)の差: {diff:,}件")
                            st.info("ℹ️ **原因**: 支部未設定のスタッフのTAAANデータが支部別集計に含まれていません")
                        
                        # 承認数の整合性チェック
                        if summary_approved != branch_approved:
                            diff = summary_approved - branch_approved
                            st.warning(f"⚠️ **承認数整合性**: 月次サマリー({summary_approved:,}件)と支部別合計({branch_approved:,}件)の差: {diff:,}件")
                            st.info("ℹ️ **原因**: 支部未設定のスタッフの承認データが支部別集計に含まれていません")
                        
                        # 報酬情報のデバッグ
                        summary_revenue = summary_data['key_metrics'].get('total_revenue', 0)
                        branch_revenue = branch_summary['total_revenue'].sum()
                        st.info(f"ℹ️ **報酬デバッグ**: 月次サマリー売上¥{summary_revenue:,}、支部別合計¥{branch_revenue:,}")
                    
                    # 支部別グラフ（5つのグラフを2行で表示）
                    st.subheader("支部別パフォーマンス")
                    
                    # 1行目: 架電数、担当コネクト数、アポ獲得数
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        fig_branch_calls = px.bar(
                            branch_summary,
                            x='branch',
                            y='total_calls',
                            title="支部別架電数",
                            color='total_calls',
                            color_continuous_scale='Blues'
                        )
                        fig_branch_calls.update_layout(height=350)
                        st.plotly_chart(fig_branch_calls, use_container_width=True)
                    
                    with col2:
                        fig_branch_connect = px.bar(
                            branch_summary,
                            x='branch',
                            y='charge_connected',
                            title="支部別担当コネクト数",
                            color='charge_connected',
                            color_continuous_scale='Greens'
                        )
                        fig_branch_connect.update_layout(height=350)
                        st.plotly_chart(fig_branch_connect, use_container_width=True)
                    
                    with col3:
                        fig_branch_appointments = px.bar(
                            branch_summary,
                            x='branch',
                            y='appointments',
                            title="支部別アポ獲得数",
                            color='appointments',
                            color_continuous_scale='Oranges'
                        )
                        fig_branch_appointments.update_layout(height=350)
                        st.plotly_chart(fig_branch_appointments, use_container_width=True)
                    
                    # 2行目: TAAAN商談数、承認数
                    col4, col5, col6 = st.columns(3)
                    
                    with col4:
                        fig_branch_taaaan = px.bar(
                            branch_summary,
                            x='branch',
                            y='taaaan_deals',
                            title="支部別TAAAN商談数",
                            color='taaaan_deals',
                            color_continuous_scale='Purples'
                        )
                        fig_branch_taaaan.update_layout(height=350)
                        st.plotly_chart(fig_branch_taaaan, use_container_width=True)
                    
                    with col5:
                        fig_branch_approved = px.bar(
                            branch_summary,
                            x='branch',
                            y='approved_deals',
                            title="支部別承認数",
                            color='approved_deals',
                            color_continuous_scale='Reds'
                        )
                        fig_branch_approved.update_layout(height=350)
                        st.plotly_chart(fig_branch_approved, use_container_width=True)
                    
                    with col6:
                        fig_branch_staff = px.bar(
                            branch_summary,
                            x='branch',
                            y='unique_staff_count',
                            title="支部別ユニーク稼働者数",
                            color='unique_staff_count',
                            color_continuous_scale='Viridis'
                        )
                        fig_branch_staff.update_layout(height=350)
                        st.plotly_chart(fig_branch_staff, use_container_width=True)
                    
                    # 支部別詳細テーブル
                    st.subheader("支部別詳細")
                    
                    # 表示するカラムを選択
                    display_columns = [
                        'branch', 'total_calls', 'charge_connected', 'appointments', 
                        'taaaan_deals', 'approved_deals', 'unique_staff_count', 'total_revenue', 'total_potential_revenue',
                        'connect_rate', 'appointment_rate', 'approval_rate'
                    ]
                    
                    # 合計行を追加
                    total_row = {
                        'branch': '合計',
                        'total_calls': branch_summary['total_calls'].sum(),
                        'charge_connected': branch_summary['charge_connected'].sum(),
                        'appointments': branch_summary['appointments'].sum(),
                        'taaaan_deals': branch_summary['taaaan_deals'].sum(),
                        'approved_deals': branch_summary['approved_deals'].sum(),
                        'unique_staff_count': branch_summary['unique_staff_count'].sum(),
                        'total_revenue': branch_summary['total_revenue'].sum(),
                        'total_potential_revenue': branch_summary['total_potential_revenue'].sum(),
                        'connect_rate': round((branch_summary['charge_connected'].sum() / branch_summary['total_calls'].sum() * 100), 1),
                        'appointment_rate': round((branch_summary['appointments'].sum() / branch_summary['charge_connected'].sum() * 100), 1),
                        'approval_rate': round((branch_summary['approved_deals'].sum() / branch_summary['taaaan_deals'].sum() * 100), 1)
                    }
                    
                    # 合計行をDataFrameに追加
                    total_df = pd.DataFrame([total_row])
                    display_df = pd.concat([branch_summary[display_columns].sort_values('total_calls', ascending=False), total_df], ignore_index=True)
                    
                    # カラム名を日本語に変更
                    display_df.columns = [
                        '支部', '架電数', '担当コネクト', 'アポ獲得', 
                        'TAAAN商談', '承認数', 'ユニーク稼働者数', '確定売上', '潜在売上',
                        '架電→担当率', '担当→アポ率', 'TAAAN→承認率'
                    ]
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True
                    )
                    
                    # データソースの説明
                    st.info("ℹ️ **データソース**: 架電数〜アポ獲得・ユニーク稼働者数は日報データ、TAAAN商談〜承認数はTAAANデータ")
                    
                    # データ整合性の警告
                    if 'key_metrics' in summary_data:
                        summary_total = summary_data['key_metrics'].get('total_calls', 0)
                        branch_total = branch_summary['total_calls'].sum()
                        summary_taaaan = summary_data['key_metrics'].get('total_deals', 0)
                        branch_taaaan = branch_summary['taaaan_deals'].sum()
                        summary_approved = summary_data['key_metrics'].get('total_approved', 0)
                        branch_approved = branch_summary['approved_deals'].sum()
                        
                        # 架電数の整合性チェック
                        if summary_total != branch_total:
                            diff = summary_total - branch_total
                            if diff > 0:
                                st.warning(f"⚠️ **架電数整合性**: 月次サマリー({summary_total:,}件)と支部別合計({branch_total:,}件)の差: {diff:,}件")
                            else:
                                st.info(f"ℹ️ **架電数整合性**: 支部別合計({branch_total:,}件)が月次サマリー({summary_total:,}件)より{abs(diff):,}件多い")
                        
                        # TAAAN商談数の整合性チェック
                        if summary_taaaan != branch_taaaan:
                            diff = summary_taaaan - branch_taaaan
                            st.warning(f"⚠️ **TAAAN商談数整合性**: 月次サマリー({summary_taaaan:,}件)と支部別合計({branch_taaaan:,}件)の差: {diff:,}件")
                            st.info("ℹ️ **原因**: 支部未設定のスタッフのTAAANデータが支部別集計に含まれていません")
                        
                        # 承認数の整合性チェック
                        if summary_approved != branch_approved:
                            diff = summary_approved - branch_approved
                            st.warning(f"⚠️ **承認数整合性**: 月次サマリー({summary_approved:,}件)と支部別合計({branch_approved:,}件)の差: {diff:,}件")
                            st.info("ℹ️ **原因**: 支部未設定のスタッフの承認データが支部別集計に含まれていません")
                        
                        # 報酬情報のデバッグ
                        summary_revenue = summary_data['key_metrics'].get('total_revenue', 0)
                        branch_revenue = branch_summary['total_revenue'].sum()
                        st.info(f"ℹ️ **報酬デバッグ**: 月次サマリー売上¥{summary_revenue:,}、支部別合計¥{branch_revenue:,}")
                
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
                    
                    # 支部別の色を定義
                    branch_colors = {
                        '東京': '#ff6b6b',
                        '横浜': '#4ecdc4',
                        '名古屋': '#45b7d1',
                        '福岡': '#96ceb4',
                        '新潟': '#feca57',
                        '大分': '#ff9ff3',
                        '未設定': '#95a5a6'
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
                    
                    # 商材別集計 - カラム名を動的に決定
                    call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_basic.columns else 'successful_calls'
                    
                    product_summary = df_basic.groupby('product').agg({
                        call_col: 'sum',
                        success_col: 'sum',
                        appointment_col: 'sum'
                    }).reset_index()
                    
                    # カラム名を統一
                    product_summary.columns = ['product', 'total_calls', 'charge_connected', 'appointments']
                    
                    # TAAANデータも含めた商材別集計
                    if 'product_performance' in summary_data:
                        taaaan_product_data = {}
                        for product, data in summary_data['product_performance'].items():
                            taaaan_product_data[product] = {
                                'total_deals': data.get('total_deals', 0),
                                'total_approved': data.get('total_approved', 0),
                                'total_revenue': data.get('total_revenue', 0),
                                'total_potential_revenue': data.get('total_potential_revenue', 0)
                            }
                        
                        # デバッグ情報を表示
                        st.info(f"ℹ️ **TAAANデータ確認**: {len(taaaan_product_data)}商材のデータを読み込みました")
                        
                        # 商材別データにTAAAN情報を追加
                        product_summary['taaaan_deals'] = product_summary['product'].map(
                            lambda x: taaaan_product_data.get(x, {}).get('total_deals', 0)
                        )
                        product_summary['approved_deals'] = product_summary['product'].map(
                            lambda x: taaaan_product_data.get(x, {}).get('total_approved', 0)
                        )
                        product_summary['total_revenue'] = product_summary['product'].map(
                            lambda x: taaaan_product_data.get(x, {}).get('total_revenue', 0)
                        )
                        product_summary['total_potential_revenue'] = product_summary['product'].map(
                            lambda x: taaaan_product_data.get(x, {}).get('total_potential_revenue', 0)
                        )
                    else:
                        # TAAANデータが存在しない場合
                        product_summary['taaaan_deals'] = 0
                        product_summary['approved_deals'] = 0
                        product_summary['total_revenue'] = 0
                        product_summary['total_potential_revenue'] = 0
                        st.warning("⚠️ **TAAANデータが見つかりません**: 商材別分析ではTAAAN関連の指標を表示できません")
                        
                    # 変換率の計算
                    product_summary['connect_rate'] = (
                        (product_summary['charge_connected'] / product_summary['total_calls'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    product_summary['appointment_rate'] = (
                        (product_summary['appointments'] / product_summary['charge_connected'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    product_summary['approval_rate'] = (
                        (product_summary['approved_deals'] / product_summary['taaaan_deals'] * 100)
                        .fillna(0)
                        .round(1)
                    )
                    
                    # 商材別グラフ（4つのグラフを2行で表示）
                    st.subheader("商材別パフォーマンス")
                    
                    # 1行目: 架電数、担当コネクト数、アポ獲得数
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        fig_product_calls = px.bar(
                            product_summary,
                            x='product',
                            y='total_calls',
                            title="商材別架電数",
                            color='total_calls',
                            color_continuous_scale='Blues'
                        )
                        fig_product_calls.update_layout(height=350)
                        st.plotly_chart(fig_product_calls, use_container_width=True)
                    
                    with col2:
                        fig_product_connect = px.bar(
                            product_summary,
                            x='product',
                            y='charge_connected',
                            title="商材別担当コネクト数",
                            color='charge_connected',
                            color_continuous_scale='Greens'
                        )
                        fig_product_connect.update_layout(height=350)
                        st.plotly_chart(fig_product_connect, use_container_width=True)
                    
                    with col3:
                        fig_product_appointments = px.bar(
                            product_summary,
                            x='product',
                            y='appointments',
                            title="商材別アポ獲得数",
                            color='appointments',
                            color_continuous_scale='Oranges'
                        )
                        fig_product_appointments.update_layout(height=350)
                        st.plotly_chart(fig_product_appointments, use_container_width=True)
                    
                    # 2行目: TAAAN商談数、承認数、売上
                    col4, col5, col6 = st.columns(3)
                    
                    with col4:
                        fig_product_taaaan = px.bar(
                            product_summary,
                            x='product',
                            y='taaaan_deals',
                            title="商材別TAAAN商談数",
                            color='taaaan_deals',
                            color_continuous_scale='Purples'
                        )
                        fig_product_taaaan.update_layout(height=350)
                        st.plotly_chart(fig_product_taaaan, use_container_width=True)
                    
                    with col5:
                        fig_product_approved = px.bar(
                            product_summary,
                            x='product',
                            y='approved_deals',
                            title="商材別承認数",
                            color='approved_deals',
                            color_continuous_scale='Reds'
                        )
                        fig_product_approved.update_layout(height=350)
                        st.plotly_chart(fig_product_approved, use_container_width=True)
                    
                    with col6:
                        fig_product_revenue = px.bar(
                            product_summary,
                            x='product',
                            y='total_revenue',
                            title="商材別確定売上",
                            color='total_revenue',
                            color_continuous_scale='Greens'
                        )
                        fig_product_revenue.update_layout(height=350)
                        st.plotly_chart(fig_product_revenue, use_container_width=True)
                    
                    # 商材別詳細テーブル
                    st.subheader("商材別詳細")
                    
                    # 表示するカラムを選択
                    display_columns = [
                        'product', 'total_calls', 'charge_connected', 'appointments', 
                        'taaaan_deals', 'approved_deals', 'total_revenue', 'total_potential_revenue',
                        'connect_rate', 'appointment_rate', 'approval_rate'
                    ]
                    
                    # 合計行を追加
                    total_row = {
                        'product': '合計',
                        'total_calls': product_summary['total_calls'].sum(),
                        'charge_connected': product_summary['charge_connected'].sum(),
                        'appointments': product_summary['appointments'].sum(),
                        'taaaan_deals': product_summary['taaaan_deals'].sum(),
                        'approved_deals': product_summary['approved_deals'].sum(),
                        'total_revenue': product_summary['total_revenue'].sum(),
                        'total_potential_revenue': product_summary['total_potential_revenue'].sum(),
                        'connect_rate': round((product_summary['charge_connected'].sum() / product_summary['total_calls'].sum() * 100), 1),
                        'appointment_rate': round((product_summary['appointments'].sum() / product_summary['charge_connected'].sum() * 100), 1),
                        'approval_rate': round((product_summary['approved_deals'].sum() / product_summary['taaaan_deals'].sum() * 100), 1)
                    }
                    
                    # 合計行を追加してテーブル表示
                    product_summary_with_total = product_summary[display_columns].copy()
                    product_summary_with_total = pd.concat([
                        product_summary_with_total,
                        pd.DataFrame([total_row])
                    ], ignore_index=True)
                    
                    st.dataframe(
                        product_summary_with_total,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # データ整合性の警告
                    if 'key_metrics' in summary_data:
                        summary_taaaan = summary_data['key_metrics'].get('total_deals', 0)
                        product_taaaan = product_summary['taaaan_deals'].sum()
                        summary_approved = summary_data['key_metrics'].get('total_approved', 0)
                        product_approved = product_summary['approved_deals'].sum()
                        summary_revenue = summary_data['key_metrics'].get('total_revenue', 0)
                        product_revenue = product_summary['total_revenue'].sum()
                        
                        # TAAAN商談数の整合性チェック
                        if summary_taaaan != product_taaaan:
                            diff = summary_taaaan - product_taaaan
                            st.warning(f"⚠️ **TAAAN商談数整合性**: 月次サマリー({summary_taaaan:,}件)と商材別合計({product_taaaan:,}件)の差: {diff:,}件")
                            st.info("ℹ️ **原因**: 商材未設定のTAAANデータが商材別集計に含まれていません")
                        
                        # 承認数の整合性チェック
                        if summary_approved != product_approved:
                            diff = summary_approved - product_approved
                            st.warning(f"⚠️ **承認数整合性**: 月次サマリー({summary_approved:,}件)と商材別合計({product_approved:,}件)の差: {diff:,}件")
                            st.info("ℹ️ **原因**: 商材未設定の承認データが商材別集計に含まれていません")
                        
                        # 報酬情報のデバッグ
                        st.info(f"ℹ️ **報酬デバッグ**: 月次サマリー売上¥{summary_revenue:,}、商材別合計¥{product_revenue:,}")
                
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
                    
                    # 詳細テーブル
                    st.dataframe(
                        filtered_df.sort_values('date', ascending=False),
                        use_container_width=True
                    )
                    
                    # CSVダウンロード
                    csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
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