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
            # データディレクトリの存在確認
            data_dir = get_data_dir()
            if data_dir is None:
                st.error("❌ データディレクトリが見つかりません")
                return None, None, None
            
            # ファイルパスの構築
            basic_file = os.path.join(data_dir, f'基本分析_{month}.json')
            detail_file = os.path.join(data_dir, f'詳細分析_{month}.json')
            summary_file = os.path.join(data_dir, f'月次サマリー_{month}.json')
            
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
            
            # 基本分析データ
            with open(basic_file, 'r', encoding='utf-8') as f:
                basic_data = json.load(f)
            
            # 詳細分析データ
            with open(detail_file, 'r', encoding='utf-8') as f:
                detail_data = json.load(f)
            
            # 月次サマリーデータ
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
                
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
        'taaaan_deals_per_staff': '1人あたりTAAAN商談数',
        'approved_deals_per_staff': '1人あたり承認数',
        'revenue_per_staff': '1人あたり報酬合計額',
        'total_calls_per_hour': '時間あたり架電数',
        'charge_connected_per_hour': '時間あたり担当コネクト数',
        'appointments_per_hour': '時間あたりアポ獲得数',
        'taaaan_deals_per_hour': '時間あたりTAAAN商談数',
        'approved_deals_per_hour': '時間あたり承認数',
        'revenue_per_hour': '時間あたり報酬合計額'
    }

    # --- 実数・単位あたり分析のグラフ描画部 ---
    # 例: fig = px.bar(..., title=..., ...); fig = update_legend(fig); st.plotly_chart(fig, ...)
    # trace名はbranch（支部名）なので豆腐化しないが、指標名はtitleで日本語化

    # --- 3ヶ月比較グラフ部 ---
    # アコーディオンをやめ、forループで全指標を縦並び一括表示
    # x軸は月次表記（例: 2024-05, 2024-06, 2024-07）
    # legendは下部・日本語化
    #
    # 例:
    # for col, label, color in indicators:
    #     st.markdown(f"#### {label}（支部別3ヶ月比較）")
    #     ...
    #     fig = px.line(..., title=..., ...)
    #     fig.update_xaxes(type='category', tickvals=compare_months, ticktext=compare_months)
    #     fig = update_legend(fig)
    #     st.plotly_chart(fig, ...)
    #
    # --- 既存のアコーディオン/expander部分は削除 ---

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
                total_revenue = summary_data['key_metrics'].get('total_revenue', 0) if 'key_metrics' in summary_data else 0
                total_potential_revenue = summary_data['key_metrics'].get('total_potential_revenue', 0) if 'key_metrics' in summary_data else 0

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
                appointment_to_taaaan = (total_deals / appointments * 100) if appointments > 0 else 0
                taaaan_to_approved = (total_approved / total_deals * 100) if total_deals > 0 else 0

                # (c) 変換率セット（オレンジ系グラデーション）
                rate_card_data = [
                    {"label": "架電→担当率", "value": f"{call_to_connect:.1f}%", "desc": "日報上で報告された担当コネクト数÷架電数", "color": "#9e5102"},
                    {"label": "担当→アポ率", "value": f"{connect_to_appointment:.1f}%", "desc": "日報上で報告されたアポ獲得数÷担当コネクト数", "color": "#f57c00"},
                    {"label": "アポ→TAAAN率", "value": f"{appointment_to_taaaan:.1f}%", "desc": "アポ獲得数÷TAAAN商談数", "color": "#ffb300"},
                    {"label": "TAAAN→承認率", "value": f"{taaaan_to_approved:.1f}%", "desc": "TAAANに入力された件数のうち、商談ステータスが「承認」の割合", "color": "#ffe082"},
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
                        taaaan_branch_data = {}
                        for branch, data in summary_data['branch_performance'].items():
                            taaaan_branch_data[branch] = {
                                'total_deals': data.get('total_deals', 0),
                                'total_approved': data.get('total_approved', 0),
                                'total_revenue': data.get('total_revenue', 0),
                                'total_potential_revenue': data.get('total_potential_revenue', 0)
                            }
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
                        branch_summary['taaaan_deals'] = 0
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
                        (branch_summary['approved_deals'] / branch_summary['taaaan_deals'] * 100)
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
                                    showlegend=False
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
                                        showlegend=False
                                    ))
                                fig_branch_hours.update_layout(
                                    title=indicator_labels.get('call_hours', '架電時間数'),
                                    yaxis_title=indicator_labels.get('call_hours', '架電時間数'),
                                    showlegend=False
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
                                    showlegend=False
                                ))
                            fig_branch_connect.update_layout(
                                title=indicator_labels.get('charge_connected', '担当コネクト数'),
                                yaxis_title=indicator_labels.get('charge_connected', '担当コネクト数'),
                                showlegend=False
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
                                    showlegend=False
                                ))
                            fig_branch_appointments.update_layout(
                                title=indicator_labels.get('get_appointment', 'アポ獲得数'),
                                yaxis_title=indicator_labels.get('get_appointment', 'アポ獲得数'),
                                showlegend=False
                            )
                            st.plotly_chart(fig_branch_appointments, use_container_width=True)
                        with col5:
                            # go.Figureを使用して手動で凡例を追加
                            fig_branch_taaaan = go.Figure()
                            # 支部ごとに異なる色でバーを作成
                            for branch in branch_summary['branch']:
                                branch_data = branch_summary[branch_summary['branch'] == branch]
                                fig_branch_taaaan.add_trace(go.Bar(
                                    x=[branch],
                                    y=branch_data['taaaan_deals'],
                                    name=branch,
                                    marker_color=branch_colors.get(branch, '#95a5a6'),
                                    showlegend=False
                                ))
                            fig_branch_taaaan.update_layout(
                                title=indicator_labels.get('total_deals', 'TAAAN商談数'),
                                yaxis_title=indicator_labels.get('total_deals', 'TAAAN商談数'),
                                showlegend=False
                            )
                            st.plotly_chart(fig_branch_taaaan, use_container_width=True)
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
                                    showlegend=False
                                ))
                            fig_branch_approved.update_layout(
                                title=indicator_labels.get('total_approved', '承認数'),
                                yaxis_title=indicator_labels.get('total_approved', '承認数'),
                                showlegend=False
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
                                    showlegend=False
                                ))
                            fig_branch_reward.update_layout(
                                title=indicator_labels.get('total_revenue', '報酬合計額'),
                                yaxis_title=indicator_labels.get('total_revenue', '報酬合計額'),
                                showlegend=False
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
                                    showlegend=False
                                ))
                            fig_branch_staff.update_layout(
                                title=indicator_labels.get('unique_staff_count', 'ユニーク稼働者数'),
                                yaxis_title=indicator_labels.get('unique_staff_count', 'ユニーク稼働者数'),
                                showlegend=False
                            )
                            st.plotly_chart(fig_branch_staff, use_container_width=True)

                    with subtab2:
                        st.markdown("##### 1人あたり指標")
                        unit_df = branch_summary.copy()
                        unit_df['total_calls_per_staff'] = unit_df['total_calls'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['call_hours_per_staff'] = unit_df['call_hours'] / unit_df['unique_staff_count'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['charge_connected_per_staff'] = unit_df['charge_connected'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['appointments_per_staff'] = unit_df['appointments'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['taaaan_deals_per_staff'] = unit_df['taaaan_deals'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['approved_deals_per_staff'] = unit_df['approved_deals'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        unit_df['revenue_per_staff'] = unit_df['total_revenue'] / unit_df['unique_staff_count'].replace(0, float('nan'))
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            for y_col, label in [
                                ('total_calls_per_staff', indicator_labels['total_calls_per_staff']),
                                ('taaaan_deals_per_staff', indicator_labels['taaaan_deals_per_staff'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False
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
                                        showlegend=False
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        with col3:
                            for y_col, label in [
                                ('charge_connected_per_staff', indicator_labels['charge_connected_per_staff']),
                                ('appointments_per_staff', indicator_labels['appointments_per_staff']),
                                ('revenue_per_staff', indicator_labels['revenue_per_staff'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False
                                )
                                st.plotly_chart(fig, use_container_width=True)

                        st.markdown("##### 時間あたり指標")
                        unit_df['total_calls_per_hour'] = unit_df['total_calls'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['charge_connected_per_hour'] = unit_df['charge_connected'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['appointments_per_hour'] = unit_df['appointments'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['taaaan_deals_per_hour'] = unit_df['taaaan_deals'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['approved_deals_per_hour'] = unit_df['approved_deals'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        unit_df['revenue_per_hour'] = unit_df['total_revenue'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
                        col4, col5, col6 = st.columns(3)
                        with col4:
                            for y_col, label in [
                                ('total_calls_per_hour', indicator_labels['total_calls_per_hour']),
                                ('taaaan_deals_per_hour', indicator_labels['taaaan_deals_per_hour'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False
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
                                        showlegend=False
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        with col6:
                            for y_col, label in [
                                ('appointments_per_hour', indicator_labels['appointments_per_hour']),
                                ('revenue_per_hour', indicator_labels['revenue_per_hour'])
                            ]:
                                fig = go.Figure()
                                for branch in unit_df['branch']:
                                    branch_data = unit_df[unit_df['branch'] == branch]
                                    fig.add_trace(go.Bar(
                                        x=[branch],
                                        y=branch_data[y_col],
                                        name=branch,
                                        marker_color=branch_colors.get(branch, '#95a5a6'),
                                        showlegend=False
                                    ))
                                fig.update_layout(
                                    title=label,
                                    yaxis_title=label,
                                    showlegend=False
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
                                        fig = px.line(
                                            plot_df, x='month', y='value', color='branch', markers=True,
                                            color_discrete_sequence=color_sequence,
                                            labels={"value": label, "month": "月", "branch": "支部"}
                                        )
                                        fig.update_xaxes(type='category', tickvals=compare_months, ticktext=compare_months)
                                        fig.update_layout(
                                            yaxis_title=label,
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
                            ('taaaan_deals_per_staff', '1人あたりTAAAN商談数', 'Purples'),
                            ('approved_deals_per_staff', '1人あたり承認数', 'Reds'),
                            ('revenue_per_staff', '1人あたり報酬合計額', 'Greens'),
                            ('total_calls_per_hour', '時間あたり架電数', 'Blues'),
                            ('charge_connected_per_hour', '時間あたり担当コネクト数', 'Greens'),
                            ('appointments_per_hour', '時間あたりアポ獲得数', 'Oranges'),
                            ('taaaan_deals_per_hour', '時間あたりTAAAN商談数', 'Purples'),
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
                                u['taaaan_deals_per_staff'] = u['total_deals'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['approved_deals_per_staff'] = u['total_approved'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['revenue_per_staff'] = u['total_revenue'] / u['unique_staff_count'].replace(0, float('nan'))
                                u['total_calls_per_hour'] = u['call_count'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['charge_connected_per_hour'] = u['charge_connected'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['appointments_per_hour'] = u['get_appointment'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                                u['taaaan_deals_per_hour'] = u['total_deals'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
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
                                        fig = px.line(
                                            plot_df, x='month', y='value', color='branch', markers=True,
                                            color_discrete_sequence=color_sequence,
                                            labels={"value": label, "month": "月", "branch": "支部"}
                                        )
                                        fig.update_xaxes(type='category', tickvals=compare_months, ticktext=compare_months)
                                        fig.update_layout(
                                            yaxis_title=label,
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
                        fig_product_calls.update_layout(
                            height=350,
                            yaxis=dict(tickformat=',', separatethousands=True)
                        )
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
                        fig_product_connect.update_layout(
                            height=350,
                            yaxis=dict(tickformat=',', separatethousands=True)
                        )
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
                        fig_product_appointments.update_layout(
                            height=350,
                            yaxis=dict(tickformat=',', separatethousands=True)
                        )
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
                        fig_product_taaaan.update_layout(
                            height=350,
                            yaxis=dict(tickformat=',', separatethousands=True)
                        )
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
                        fig_product_approved.update_layout(
                            height=350,
                            yaxis=dict(tickformat=',', separatethousands=True)
                        )
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
                        fig_product_revenue.update_layout(
                            height=350,
                            yaxis=dict(tickformat=',', separatethousands=True)
                        )
                        st.plotly_chart(fig_product_revenue, use_container_width=True)
                    
                    # 商材別詳細テーブル
                    st.subheader("商材別詳細")
                    
                    # 表示するカラムを選択
                    display_columns = [
                        'product', 'total_calls', 'charge_connected', 'appointments', 
                        'taaaan_deals', 'approved_deals', 'total_revenue', 'total_potential_revenue',
                        'connect_rate', 'appointment_rate', 'approval_rate'
                    ]
                    
                    # カラム名の日本語マッピング
                    column_labels = {
                        'product': '商材',
                        'total_calls': '総架電数',
                        'charge_connected': '担当コネクト数',
                        'appointments': 'アポ獲得数',
                        'taaaan_deals': 'TAAAN商談数',
                        'approved_deals': '承認数',
                        'total_revenue': '確定売上',
                        'total_potential_revenue': '潜在売上',
                        'connect_rate': '担当コネクト率(%)',
                        'appointment_rate': 'アポ獲得率(%)',
                        'approval_rate': '承認率(%)'
                    }
                    
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
                    
                    # 数値のフォーマット
                    for col in ['total_calls', 'charge_connected', 'appointments', 'taaaan_deals', 'approved_deals']:
                        product_summary_with_total[col] = product_summary_with_total[col].apply(lambda x: f"{x:,}")
                    
                    for col in ['total_revenue', 'total_potential_revenue']:
                        product_summary_with_total[col] = product_summary_with_total[col].apply(lambda x: f"¥{x:,}")
                    
                    for col in ['connect_rate', 'appointment_rate', 'approval_rate']:
                        product_summary_with_total[col] = product_summary_with_total[col].apply(lambda x: f"{x}%")
                    
                    # カラム名を日本語に変更
                    product_summary_with_total.columns = [column_labels.get(col, col) for col in product_summary_with_total.columns]
                    
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