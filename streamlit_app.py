import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import zipfile
import tempfile
import io
from pathlib import Path
import numpy as np

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

def extract_zip_data(uploaded_file):
    """ZipファイルからJSONデータを抽出"""
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
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
                                st.error(f"JSONファイル読み込みエラー {file}: {e}")
                
                return json_files
    except Exception as e:
        st.error(f"Zipファイル処理エラー: {e}")
        return {}

def get_available_months_from_data(json_data):
    """JSONデータから利用可能な月を抽出"""
    months = set()
    for filename, data in json_data.items():
        # ファイル名から月を抽出（例: 基本分析_2024-09.json）
        if '_' in filename and '.json' in filename:
            parts = filename.split('_')
            if len(parts) >= 2:
                month_part = parts[-1].replace('.json', '')
                if len(month_part) == 7 and month_part[4] == '-':  # YYYY-MM形式
                    months.add(month_part)
    return sorted(list(months), reverse=True)

def load_analysis_data_from_json(json_data, month):
    """指定月の分析データをJSONデータから読み込み"""
    basic_data = None
    detail_data = None
    summary_data = None
    
    for filename, data in json_data.items():
        if f'基本分析_{month}.json' in filename:
            basic_data = data
        elif f'詳細分析_{month}.json' in filename:
            detail_data = data
        elif f'月次サマリー_{month}.json' in filename:
            summary_data = data
    
    return basic_data, detail_data, summary_data

def load_retention_data_from_json(json_data, month):
    """指定月の定着率分析データをJSONデータから読み込み"""
    for filename, data in json_data.items():
        if f'定着率分析_{month}.json' in filename:
            return data
    return None

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

def get_prev_months(month_str, n=3):
    """
    指定月から過去n月分の月リストを生成
    
    Args:
        month_str: 基準月 (YYYY-MM形式)
        n: 取得する月数
        
    Returns:
        list: 月のリスト (YYYY-MM形式)
    """
    try:
        from datetime import datetime, timedelta
        import calendar
        
        # 月文字列をパース
        year, month = map(int, month_str.split('-'))
        months = []
        
        for i in range(n):
            if month - i <= 0:
                # 前年に遡る
                new_year = year - 1
                new_month = 12 + (month - i)
            else:
                new_year = year
                new_month = month - i
            
            months.append(f"{new_year:04d}-{new_month:02d}")
        
        return list(reversed(months))  # 古い順にソート
        
    except Exception as e:
        st.error(f"月リスト生成エラー: {e}")
        return []

def display_ranking_with_ties(df, ranking_column, display_columns, max_rank=10, 
                             branch_colors=None, show_branch=True, format_func=None):
    """
    同順位を反映したランキング表示関数
    
    Args:
        df: DataFrame
        ranking_column: ランキング基準の列名
        display_columns: 表示する列のリスト
        max_rank: 表示する最大順位
        branch_colors: 支部の色設定辞書
        show_branch: 支部タグを表示するか
        format_func: 値のフォーマット関数
    """
    # 同順位を反映した順位を計算
    df_sorted = df.copy()
    df_sorted['rank'] = df_sorted[ranking_column].rank(method='min', ascending=False).astype(int)
    df_sorted = df_sorted.sort_values([ranking_column, 'staff_name'], ascending=[False, True])
    
    # 指定順位以内のデータのみ取得
    df_display = df_sorted[df_sorted['rank'] <= max_rank]
    
    # ランキング表示
    for _, row in df_display.iterrows():
        rank = row['rank']
        staff_name = row['staff_name']
        
        # 支部タグの作成
        if show_branch and branch_colors and 'branch' in row:
            branch_color = branch_colors.get(row['branch'], '#95a5a6')
            branch_tag = f'<span style="background-color: {branch_color}; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-left: 8px;">{row["branch"]}</span>'
        else:
            branch_tag = ''
        
        # 表示値の作成
        display_values = []
        for col in display_columns:
            value = row[col]
            if format_func:
                formatted_value = format_func(col, value)
            else:
                # デフォルトフォーマット
                if col == 'total_revenue':
                    formatted_value = f"¥{value:,}"
                elif col == 'revenue_per_hour':
                    formatted_value = f"¥{value:,.0f}/時間"
                elif col == 'revenue_per_working_day':
                    formatted_value = f"¥{value:,.0f}/日"
                elif col == 'total_hours':
                    formatted_value = f"総{value:.1f}h"
                elif col == 'working_days':
                    formatted_value = f"{value:.0f}日"
                elif col == 'appointments':
                    formatted_value = f"総{value:,.0f}件"
                elif col == 'taaan_deals':
                    formatted_value = f"総{value:,.0f}件"
                elif col == 'approved_deals':
                    formatted_value = f"総{value:,.0f}件"
                elif 'rate' in col.lower():
                    formatted_value = f"{value:.1f}%"
                elif 'per_hour' in col.lower():
                    formatted_value = f"{value:.1f}件/時間"
                elif 'per_day' in col.lower():
                    formatted_value = f"{value:.1f}件/日"
                elif isinstance(value, (int, float)):
                    formatted_value = f"{value:,}件" if value >= 1000 or value == int(value) else f"{value:.1f}"
                else:
                    formatted_value = str(value)
            display_values.append(formatted_value)
        
        # 表示文字列の作成
        if len(display_values) == 1:
            display_text = f"{rank}. {staff_name}{branch_tag} : {display_values[0]}"
        else:
            display_text = f"{rank}. {staff_name}{branch_tag} : {display_values[0]} ({display_values[1]})"
        st.markdown(display_text, unsafe_allow_html=True)

def load_multi_month_data(json_data, target_months):
    """
    複数月のデータを読み込んで統合
    
    Args:
        json_data: JSONデータ
        target_months: 対象月のリスト
        
    Returns:
        dict: 月別データ辞書
    """
    monthly_data = {}
    
    for month in target_months:
        try:
            basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, month)
            
            if basic_data and summary_data:
                # スタッフ別データの抽出
                if 'monthly_analysis' in basic_data and month in basic_data['monthly_analysis']:
                    staff_dict = basic_data['monthly_analysis'][month]['staff']
                    df_basic = extract_daily_activity_from_staff(staff_dict)
                    
                    if not df_basic.empty:
                        # 集計処理
                        df_basic['branch'] = df_basic['branch'].fillna('未設定')
                        
                        # 日報データ集計
                        agg_dict = {
                            'call_count': 'sum',
                            'charge_connected': 'sum', 
                            'get_appointment': 'sum',
                            'call_hours': 'sum'
                        }
                        
                        staff_summary = df_basic.groupby('staff_name').agg(agg_dict).reset_index()
                        
                        # 支部情報の追加
                        branch_mapping = df_basic.groupby('staff_name')['branch'].first().to_dict()
                        staff_summary['branch'] = staff_summary['staff_name'].map(branch_mapping)
                        
                        # TAAANデータの追加
                        taaan_staff_data = {}
                        
                        # 基本分析データから直接取得
                        if 'monthly_analysis' in basic_data and month in basic_data['monthly_analysis']:
                            for staff_name, staff_data in basic_data['monthly_analysis'][month]['staff'].items():
                                taaan_staff_data[staff_name] = {
                                    'taaan_deals': staff_data.get('total_deals', 0),
                                    'approved_deals': staff_data.get('total_approved', 0),
                                    'total_revenue': staff_data.get('total_revenue', 0)
                                }
                        
                        # フォールバック: staff_performanceから取得
                        if 'staff_performance' in summary_data:
                            for staff_name, data in summary_data['staff_performance'].items():
                                if staff_name not in taaan_staff_data:
                                    taaan_staff_data[staff_name] = {
                                        'taaan_deals': data.get('total_deals', 0),
                                        'approved_deals': data.get('total_approved', 0),
                                        'total_revenue': data.get('total_revenue', 0)
                                    }
                        
                        # TAAANデータを結合
                        for col_name, taaan_key in [('taaan_deals', 'taaan_deals'), 
                                                  ('approved_deals', 'approved_deals'), 
                                                  ('total_revenue', 'total_revenue')]:
                            staff_summary[col_name] = staff_summary['staff_name'].map(
                                lambda x: taaan_staff_data.get(x, {}).get(taaan_key, 0)
                            )
                        
                        # カラム名の統一
                        staff_summary = staff_summary.rename(columns={
                            'call_count': 'total_calls',
                            'get_appointment': 'appointments',
                            'call_hours': 'total_hours'
                        })
                        
                        # 稼働日数計算
                        working_days_df = df_basic.groupby('staff_name')['date'].nunique().reset_index()
                        working_days_df.columns = ['staff_name', 'working_days']
                        staff_summary = staff_summary.merge(working_days_df, on='staff_name', how='left')
                        staff_summary['working_days'] = staff_summary['working_days'].fillna(0)
                        
                        # 効率性指標の計算
                        staff_summary['calls_per_hour'] = staff_summary.apply(
                            lambda row: row['total_calls'] / row['total_hours'] if row['total_hours'] > 0 else 0, axis=1
                        )
                        staff_summary['appointments_per_hour'] = staff_summary.apply(
                            lambda row: row['appointments'] / row['total_hours'] if row['total_hours'] > 0 else 0, axis=1
                        )
                        staff_summary['deals_per_hour'] = staff_summary.apply(
                            lambda row: row['taaan_deals'] / row['total_hours'] if row['total_hours'] > 0 else 0, axis=1
                        )
                        staff_summary['revenue_per_hour'] = staff_summary.apply(
                            lambda row: row['total_revenue'] / row['total_hours'] if row['total_hours'] > 0 else 0, axis=1
                        )
                        staff_summary['calls_per_working_day'] = staff_summary.apply(
                            lambda row: row['total_calls'] / row['working_days'] if row['working_days'] > 0 else 0, axis=1
                        )
                        staff_summary['appointments_per_working_day'] = staff_summary.apply(
                            lambda row: row['appointments'] / row['working_days'] if row['working_days'] > 0 else 0, axis=1
                        )
                        staff_summary['deals_per_working_day'] = staff_summary.apply(
                            lambda row: row['taaan_deals'] / row['working_days'] if row['working_days'] > 0 else 0, axis=1
                        )
                        staff_summary['approved_per_working_day'] = staff_summary.apply(
                            lambda row: row['approved_deals'] / row['working_days'] if row['working_days'] > 0 else 0, axis=1
                        )
                        staff_summary['revenue_per_working_day'] = staff_summary.apply(
                            lambda row: row['total_revenue'] / row['working_days'] if row['working_days'] > 0 else 0, axis=1
                        )
                        
                        monthly_data[month] = staff_summary
                        
        except Exception as e:
            st.warning(f"⚠️ {month}のデータ読み込みに失敗: {str(e)}")
            continue
    
    return monthly_data

def create_trend_chart(monthly_data, metric_column, metric_name, staff_filter=None, branch_colors=None):
    """
    月別推移チャートを作成（人ごとの色分け、月次表示対応）
    
    Args:
        monthly_data: 月別データ辞書
        metric_column: 指標列名
        metric_name: 指標表示名
        staff_filter: スタッフフィルター（Noneの場合は全スタッフ）
        branch_colors: 支部色設定（人ごと色分けのため現在未使用）
        
    Returns:
        plotly figure
    """
    fig = go.Figure()
    
    # 全スタッフのデータを統合
    all_staff_data = {}
    months = sorted(monthly_data.keys())
    
    for month, df in monthly_data.items():
        if staff_filter:
            df = df[df['staff_name'].isin(staff_filter)]
        
        for _, row in df.iterrows():
            staff_name = row['staff_name']
            branch = row['branch']
            value = row[metric_column]
            
            if staff_name not in all_staff_data:
                all_staff_data[staff_name] = {
                    'months': [],
                    'values': [],
                    'branch': branch
                }
            
            all_staff_data[staff_name]['months'].append(month)
            all_staff_data[staff_name]['values'].append(value)
    
    # 人数に応じた色パレットを生成
    staff_names = list(all_staff_data.keys())
    num_staff = len(staff_names)
    
    if num_staff <= 10:
        # 10人以下の場合はplotlyの標準カラーを使用
        colors = px.colors.qualitative.Plotly
    else:
        # 10人以上の場合はより多くの色を生成
        colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel + px.colors.qualitative.Set1
    
    # 各スタッフの推移線を追加（人ごとに異なる色）
    for i, (staff_name, data) in enumerate(all_staff_data.items()):
        branch = data['branch']
        color = colors[i % len(colors)]  # 色をローテーション
        
        # データが3ヶ月分揃っていない場合の補完
        complete_months = []
        complete_values = []
        for month in months:
            if month in data['months']:
                idx = data['months'].index(month)
                complete_months.append(month)
                complete_values.append(data['values'][idx])
            else:
                complete_months.append(month)
                complete_values.append(None)  # 欠損値
        
        fig.add_trace(go.Scatter(
            x=complete_months,
            y=complete_values,
            mode='lines+markers',
            name=f"{staff_name} ({branch})",
            line=dict(color=color, width=2),
            marker=dict(size=8, color=color),
            connectgaps=False,  # 欠損値は接続しない
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         '月: %{x}<br>' +
                         f'{metric_name}: %{{y}}<br>' +
                         '<extra></extra>'
        ))
    
    # 月次表示のためのx軸フォーマット設定
    fig.update_layout(
        title=f"📈 {metric_name} - 3ヶ月推移",
        xaxis=dict(
            title="月",
            type='category',  # カテゴリ軸として扱う
            categoryorder='array',
            categoryarray=months,
            tickangle=45
        ),
        yaxis_title=metric_name,
        hovermode='x unified',
        showlegend=True,
        height=600,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        margin=dict(r=150)  # 凡例のためのマージン
    )
    
    return fig

def create_monthly_histogram(monthly_data, metric_column, metric_name, staff_filter=None):
    """
    月別ヒストグラムを作成（月ごとに色分けし、最適なbinサイズで統一）
    
    Args:
        monthly_data: 月別データ辞書
        metric_column: 指標列名
        metric_name: 指標表示名
        staff_filter: スタッフフィルター
        
    Returns:
        plotly figure
    """
    import numpy as np
    
    fig = go.Figure()
    
    months = sorted(monthly_data.keys())
    # 月ごとに区別しやすい色（Plotlyのカテゴリカルカラーパレット）
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # 全データを収集してbinサイズを計算
    all_values = []
    monthly_values = {}
    
    for month in months:
        if month in monthly_data:
            df = monthly_data[month]
            if staff_filter:
                df = df[df['staff_name'].isin(staff_filter)]
            
            values = df[metric_column].dropna().tolist()
            if values:
                monthly_values[month] = values
                all_values.extend(values)
    
    if not all_values:
        return go.Figure()
    
    # 最適なbinサイズを計算（Sturgesの法則とFreedman-Diaconisの法則の中間値）
    n_data = len(all_values)
    sturges_bins = int(np.log2(n_data) + 1)
    
    # データの範囲とIQRを計算
    q75, q25 = np.percentile(all_values, [75, 25])
    iqr = q75 - q25
    
    if iqr > 0:
        # Freedman-Diaconisの法則
        h = 2 * iqr / (n_data ** (1/3))
        fd_bins = int((max(all_values) - min(all_values)) / h) if h > 0 else sturges_bins
        # 適切な範囲内に制限
        optimal_bins = max(5, min(30, int((sturges_bins + fd_bins) / 2)))
    else:
        optimal_bins = sturges_bins
    
    # 共通のbinエッジを計算
    data_min, data_max = min(all_values), max(all_values)
    bin_edges = np.linspace(data_min, data_max, optimal_bins + 1)
    
    # 各月のヒストグラムを作成
    for i, month in enumerate(months):
        if month in monthly_values:
            values = monthly_values[month]
            
            fig.add_trace(go.Histogram(
                x=values,
                name=f"{month} (n={len(values)})",
                opacity=0.7,
                marker_color=colors[i % len(colors)],
                xbins=dict(
                    start=data_min,
                    end=data_max,
                    size=(data_max - data_min) / optimal_bins
                ),
                histnorm='probability density',  # 確率密度で正規化
                legendgroup=month
            ))
    
    fig.update_layout(
        title=dict(
            text=f"📊 {metric_name} - 月別分布比較",
            x=0.5,
            font=dict(size=16)
        ),
        xaxis_title=metric_name,
        yaxis_title="確率密度",
        barmode='overlay',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified'
    )
    
    return fig

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
        
        # データアップロードセクション
        st.subheader("📁 データアップロード")
        uploaded_file = st.file_uploader(
            "JSONファイルを含むZipファイルをアップロード",
            type=['zip'],
            help="複数のJSONファイルをZip形式でアップロードしてください"
        )
        
        # アップロードされたデータをセッションに保存
        if uploaded_file is not None:
            if 'json_data' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
                with st.spinner("Zipファイルを処理中..."):
                    json_data = extract_zip_data(uploaded_file)
                    st.session_state['json_data'] = json_data
                    st.session_state['uploaded_file_name'] = uploaded_file.name
                    st.session_state['available_months'] = get_available_months_from_data(json_data)
                
                if json_data:
                    st.success(f"✅ {len(json_data)}個のJSONファイルを読み込みました")
                    st.write(f"利用可能な月: {', '.join(st.session_state['available_months'])}")
                else:
                    st.error("❌ JSONファイルが見つかりませんでした")
        
        # データがアップロードされている場合のみ分析オプションを表示
        if 'json_data' in st.session_state and st.session_state['json_data']:
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
            
            # 月選択
            if st.session_state.get('available_months'):
                selected_month = st.selectbox(
                    "分析月を選択",
                    st.session_state['available_months'],
                    index=0
                )
                st.session_state['selected_month'] = selected_month
        else:
            st.info("📁 データをアップロードして分析を開始してください")
            selected_analysis = None
            selected_month = None

    # メインコンテンツエリア
    if 'json_data' in st.session_state and st.session_state['json_data']:
        json_data = st.session_state['json_data']
        selected_month = st.session_state.get('selected_month')
        
        if selected_analysis == "basic_analysis":
            st.header("📊 月次サマリー分析")
            st.caption("全期間の月次推移データを表示します")
            
            if selected_month:
                basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, selected_month)
                
                if basic_data and detail_data and summary_data:
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
                        retention_data = load_retention_data_from_json(json_data, selected_month)
                        if retention_data and "monthly_retention_rates" in retention_data:
                            trend = []
                            for month, r in retention_data["monthly_retention_rates"].items():
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
                        
                        if 'deal_status_breakdown' in summary_data:
                            deal_status = summary_data['deal_status_breakdown']
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
                                    title=f"{selected_month}の商談ステータス分布",
                                    height=400
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("ℹ️ 商談データがありません")
                        else:
                            st.info("ℹ️ 商談ステータスデータが見つかりません")
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
            
            if selected_month:
                retention_data = load_retention_data_from_json(json_data, selected_month)
                
                if retention_data:
                    # 定着率推移グラフ
                    st.subheader("📊 定着率推移")
                    
                    # 月次定着率データの抽出
                    monthly_retention = retention_data.get('monthly_retention_rates', {})
                    if monthly_retention:
                        # データフレーム作成
                        retention_df = []
                        for month, data in monthly_retention.items():
                            retention_df.append({
                                'month': month,
                                'active_staff': data.get('active_staff', 0),
                                'total_staff': data.get('total_staff', 0),
                                'retention_rate': float(data.get('retention_rate', 0))
                            })
                        
                        retention_df = pd.DataFrame(retention_df)
                        retention_df = retention_df.sort_values('month')
                        
                        # 定着率推移グラフ
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=retention_df['month'], 
                            y=retention_df['retention_rate'], 
                            mode='lines+markers', 
                            name='定着率(%)',
                            line=dict(color='blue', width=2)
                        ))
                        fig.update_layout(
                            title="月次定着率推移",
                            xaxis_title="月",
                            yaxis=dict(title='定着率(%)', range=[0,100]),
                            height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 最新月のメトリクス
                        if not retention_df.empty:
                            latest = retention_df.iloc[-1]
                            col1, col2, col3 = st.columns(3)
                            
                            col1.metric("最新月定着率", f"{latest['retention_rate']:.1f}%")
                            col2.metric("アクティブスタッフ数", f"{latest['active_staff']:,}人")
                            col3.metric("総スタッフ数", f"{latest['total_staff']:,}人")
                    
                    # スタッフ別定着率
                    staff_retention = retention_data.get('staff_retention', {})
                    if staff_retention:
                        st.subheader("👥 スタッフ別定着率")
                        
                        staff_df = []
                        for staff_name, data in staff_retention.items():
                            staff_df.append({
                                'staff_name': staff_name,
                                'branch': data.get('branch', '未設定'),
                                'join_date': data.get('join_date', ''),
                                'is_active': data.get('is_active', False),
                                'retention_rate': float(data.get('retention_rate', 0))
                            })
                        
                        staff_df = pd.DataFrame(staff_df)
                        
                        if not staff_df.empty:
                            # スタッフ別定着率グラフ
                            fig_staff = go.Figure()
                            
                            # アクティブ/非アクティブで色分け
                            active_staff = staff_df[staff_df['is_active'] == True]
                            inactive_staff = staff_df[staff_df['is_active'] == False]
                            
                            if not active_staff.empty:
                                fig_staff.add_trace(go.Bar(
                                    x=active_staff['staff_name'],
                                    y=active_staff['retention_rate'],
                                    name='アクティブ',
                                    marker_color='green'
                                ))
                            
                            if not inactive_staff.empty:
                                fig_staff.add_trace(go.Bar(
                                    x=inactive_staff['staff_name'],
                                    y=inactive_staff['retention_rate'],
                                    name='非アクティブ',
                                    marker_color='red'
                                ))
                            
                            fig_staff.update_layout(
                                title="スタッフ別定着率",
                                barmode='group',
                                height=400
                            )
                            
                            st.plotly_chart(fig_staff, use_container_width=True)
                            
                            # スタッフ別詳細テーブル
                            st.subheader("スタッフ別詳細")
                            st.dataframe(staff_df, use_container_width=True)
                    
                    # 支部別定着率
                    branch_retention = retention_data.get('branch_retention', {})
                    if branch_retention:
                        st.subheader("🏢 支部別定着率")
                        
                        branch_df = []
                        for branch_name, data in branch_retention.items():
                            branch_df.append({
                                'branch': branch_name,
                                'active_staff': data.get('active_staff', 0),
                                'total_staff': data.get('total_staff', 0),
                                'retention_rate': float(data.get('retention_rate', 0))
                            })
                        
                        branch_df = pd.DataFrame(branch_df)
                        
                        if not branch_df.empty:
                            # 支部別定着率グラフ
                            fig_branch = go.Figure()
                            
                            fig_branch.add_trace(go.Bar(
                                x=branch_df['branch'],
                                y=branch_df['retention_rate'],
                                name='定着率',
                                marker_color='blue'
                            ))
                            
                            fig_branch.update_layout(
                                title="支部別定着率",
                                height=400
                            )
                            
                            st.plotly_chart(fig_branch, use_container_width=True)
                            
                            # 支部別詳細テーブル
                            st.subheader("支部別詳細")
                            st.dataframe(branch_df, use_container_width=True)
                    
                    # 入社月別定着率
                    join_month_retention = retention_data.get('join_month_retention', {})
                    if join_month_retention:
                        st.subheader("📅 入社月別定着率")
                        
                        join_df = []
                        for join_month, data in join_month_retention.items():
                            join_df.append({
                                'join_month': join_month,
                                'active_staff': data.get('active_staff', 0),
                                'total_staff': data.get('total_staff', 0),
                                'retention_rate': float(data.get('retention_rate', 0))
                            })
                        
                        join_df = pd.DataFrame(join_df)
                        join_df = join_df.sort_values('join_month')
                        
                        if not join_df.empty:
                            # 入社月別定着率グラフ
                            fig_join = go.Figure()
                            
                            fig_join.add_trace(go.Scatter(
                                x=join_df['join_month'],
                                y=join_df['retention_rate'],
                                mode='lines+markers',
                                name='定着率',
                                line=dict(color='purple', width=2)
                            ))
                            
                            fig_join.update_layout(
                                title="入社月別定着率推移",
                                xaxis_title="入社月",
                                yaxis=dict(title='定着率(%)', range=[0,100]),
                                height=400
                            )
                            
                            st.plotly_chart(fig_join, use_container_width=True)
                            
                            # 入社月別詳細テーブル
                            st.subheader("入社月別詳細")
                            st.dataframe(join_df, use_container_width=True)
                    
                    # 詳細データ表示
                    st.subheader("📋 定着率詳細データ")
                    st.json(retention_data)
                    
                else:
                    st.warning("⚠️ 定着率データが見つかりませんでした")
        
        elif selected_analysis == "monthly_detail":
            st.header("📋 単月詳細データ")
            st.caption(f"選択月: {selected_month}")
            
            if selected_month:
                basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, selected_month)
                
                if basic_data and detail_data and summary_data:
                    # データフレーム作成
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
                                            title='架電数',
                                            yaxis_title='架電数',
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
                                                title='架電時間数',
                                                yaxis_title='架電時間数',
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
                                            title='担当コネクト数',
                                            yaxis_title='担当コネクト数',
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
                                            title='アポ獲得数',
                                            yaxis_title='アポ獲得数',
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
                                            title='TAAAN商談数',
                                            yaxis_title='TAAAN商談数',
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
                                            title='承認数',
                                            yaxis_title='承認数',
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
                                            title='報酬合計額',
                                            yaxis_title='報酬合計額',
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
                                            title='ユニーク稼働者数',
                                            yaxis_title='ユニーク稼働者数',
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
                                            ('total_calls_per_staff', '1人あたり架電数'),
                                            ('taaan_deals_per_staff', '1人あたりTAAAN商談数')
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
                                            ('call_hours_per_staff', '1人あたり架電時間数'),
                                            ('approved_deals_per_staff', '1人あたり承認数')
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
                                            ('charge_connected_per_staff', '1人あたり担当コネクト数'),
                                            ('appointments_per_staff', '1人あたりアポ獲得数'),
                                            ('revenue_per_staff', '1人あたり報酬合計額')
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
                                            ('total_calls_per_hour', '時間あたり架電数'),
                                            ('taaan_deals_per_hour', '時間あたりTAAAN商談数')
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
                                            ('charge_connected_per_hour', '時間あたり担当コネクト数'),
                                            ('approved_deals_per_hour', '時間あたり承認数')
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
                                            ('appointments_per_hour', '時間あたりアポ獲得数'),
                                            ('revenue_per_hour', '時間あたり報酬合計額')
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
                                        b, d, s = load_analysis_data_from_json(json_data, m)
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
                                
                                # 共通のスタッフ別集計処理
                                # 日報データから基本集計
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
                                staff_summary.columns = ['staff_name', 'total_calls', 'charge_connected', 'appointments', 'branch']
                                
                                # TAAANデータをスタッフ別に集計（基本分析データから直接取得）
                                taaan_staff_data = {}
                                if basic_data and 'monthly_analysis' in basic_data and selected_month in basic_data['monthly_analysis']:
                                    staff_dict = basic_data['monthly_analysis'][selected_month]['staff']
                                    for staff_name, staff_data in staff_dict.items():
                                        taaan_staff_data[staff_name] = {
                                            'taaan_deals': staff_data.get('total_deals', 0),
                                            'approved_deals': staff_data.get('total_approved', 0),
                                            'total_revenue': staff_data.get('total_revenue', 0),
                                            'total_potential_revenue': staff_data.get('total_potential_revenue', 0)
                                        }
                                
                                # staff_performanceもフォールバックとして使用（上位N名のデータのため）
                                if 'staff_performance' in summary_data:
                                    for staff_name, data in summary_data['staff_performance'].items():
                                        if staff_name not in taaan_staff_data:  # まだ存在しない場合のみ追加
                                            taaan_staff_data[staff_name] = {
                                                'taaan_deals': data.get('total_deals', 0),
                                                'approved_deals': data.get('total_approved', 0),
                                                'total_revenue': data.get('total_revenue', 0),
                                                'total_potential_revenue': data.get('total_potential_revenue', 0)
                                            }
                                
                                # TAAANデータを結合
                                staff_summary['taaan_deals'] = staff_summary['staff_name'].map(
                                    lambda x: taaan_staff_data.get(x, {}).get('taaan_deals', 0)
                                )
                                staff_summary['approved_deals'] = staff_summary['staff_name'].map(
                                    lambda x: taaan_staff_data.get(x, {}).get('approved_deals', 0)
                                )
                                staff_summary['total_revenue'] = staff_summary['staff_name'].map(
                                    lambda x: taaan_staff_data.get(x, {}).get('total_revenue', 0)
                                )
                                staff_summary['total_potential_revenue'] = staff_summary['staff_name'].map(
                                    lambda x: taaan_staff_data.get(x, {}).get('total_potential_revenue', 0)
                                )
                                
                                # 支部名を正規化
                                staff_summary['branch'] = staff_summary['branch'].fillna('未設定')
                                
                                # 変換率の計算
                                staff_summary['connect_rate'] = (
                                    (staff_summary['charge_connected'] / staff_summary['total_calls'] * 100)
                                    .fillna(0)
                                    .round(1)
                                )
                                staff_summary['appointment_rate'] = (
                                    (staff_summary['appointments'] / staff_summary['charge_connected'] * 100)
                                    .fillna(0)
                                    .round(1)
                                )
                                staff_summary['approval_rate'] = (
                                    (staff_summary['approved_deals'] / staff_summary['taaan_deals'] * 100)
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
                                
                                # 全体TAAANデータの状況を確認
                                total_staff_count = len(staff_summary)
                                total_taaan_deals_all = staff_summary['taaan_deals'].sum()
                                total_approved_deals_all = staff_summary['approved_deals'].sum()
                                total_revenue_all = staff_summary['total_revenue'].sum()
                                staff_with_taaan = len(staff_summary[staff_summary['taaan_deals'] > 0])
                                
                                # データソース情報を追加
                                basic_data_available = basic_data and 'monthly_analysis' in basic_data and selected_month in basic_data['monthly_analysis']
                                basic_staff_count = len(basic_data['monthly_analysis'][selected_month]['staff']) if basic_data_available else 0
                                summary_staff_count = len(summary_data.get('staff_performance', {})) if 'staff_performance' in summary_data else 0
                                
                                # スタッフ別分析のサブタブ
                                staff_subtab1, staff_subtab2, staff_subtab3, staff_subtab4 = st.tabs([
                                    "📊 全体実数ランキング", "🏢 支部内実数ランキング", "⚡ 効率性ランキング", "📈 月別推移(3ヶ月)"
                                ])
                                
                                with staff_subtab1:
                                    st.subheader("📊 全体実数ランキング")
                                    st.write("全スタッフの実数（絶対値）でのランキングです。")
                                    
                                    # 6つのランキングを2列×3行で表示
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        # 1. 架電数ランキング
                                        st.markdown("##### 🏆 架電数ランキング (日報)")
                                        display_ranking_with_ties(
                                            staff_summary, 
                                            'total_calls', 
                                            ['total_calls'], 
                                            max_rank=10, 
                                            branch_colors=branch_colors
                                        )
                                        
                                        st.markdown("---")
                                        
                                        # 2. 担当コネクト数ランキング
                                        st.markdown("##### 📞 担当コネクト数ランキング (日報)")
                                        display_ranking_with_ties(
                                            staff_summary, 
                                            'charge_connected', 
                                            ['charge_connected'], 
                                            max_rank=10, 
                                            branch_colors=branch_colors
                                        )
                                        
                                        st.markdown("---")
                                        
                                        # 3. アポ獲得数ランキング
                                        st.markdown("##### 🎯 アポ獲得数ランキング (日報)")
                                        display_ranking_with_ties(
                                            staff_summary, 
                                            'appointments', 
                                            ['appointments'], 
                                            max_rank=10, 
                                            branch_colors=branch_colors
                                        )
                                    
                                    with col2:
                                        # 4. TAAAN商談数ランキング
                                        st.markdown("##### 💼 TAAAN商談数ランキング (TAAAN)")
                                        display_ranking_with_ties(
                                            staff_summary, 
                                            'taaan_deals', 
                                            ['taaan_deals'], 
                                            max_rank=10, 
                                            branch_colors=branch_colors
                                        )
                                        
                                        st.markdown("---")
                                        
                                        # 5. TAAAN承認数ランキング
                                        st.markdown("##### ✅ TAAAN承認数ランキング (TAAAN)")
                                        display_ranking_with_ties(
                                            staff_summary, 
                                            'approved_deals', 
                                            ['approved_deals'], 
                                            max_rank=10, 
                                            branch_colors=branch_colors
                                        )
                                        
                                        st.markdown("---")
                                        
                                        # 6. TAAAN報酬額ランキング
                                        st.markdown("##### 💰 TAAAN報酬額ランキング (TAAAN)")
                                        display_ranking_with_ties(
                                            staff_summary, 
                                            'total_revenue', 
                                            ['total_revenue'], 
                                            max_rank=10, 
                                            branch_colors=branch_colors
                                        )
                                
                                with staff_subtab2:
                                    st.subheader("🏢 支部内実数ランキング")
                                    st.write("支部内でのスタッフランキングです。")
                                    
                                    # 支部選択（ボタン形式）
                                    available_branches = sorted(staff_summary['branch'].unique())
                                    st.write("**📍 分析対象支部を選択**")
                                    
                                    # 支部ボタンを動的に配置
                                    if len(available_branches) <= 6:
                                        # 6個以下の場合は横一列に配置
                                        cols = st.columns(len(available_branches))
                                        for i, branch in enumerate(available_branches):
                                            with cols[i]:
                                                if st.button(f"{branch}", use_container_width=True, key=f"branch_btn_{branch}"):
                                                    st.session_state.selected_branch_ranking = branch
                                    else:
                                        # 7個以上の場合は2行に分けて配置
                                        mid_point = (len(available_branches) + 1) // 2
                                        first_row = available_branches[:mid_point]
                                        second_row = available_branches[mid_point:]
                                        
                                        # 1行目
                                        cols1 = st.columns(len(first_row))
                                        for i, branch in enumerate(first_row):
                                            with cols1[i]:
                                                if st.button(f"{branch}", use_container_width=True, key=f"branch_btn_{branch}"):
                                                    st.session_state.selected_branch_ranking = branch
                                        
                                        # 2行目
                                        cols2 = st.columns(len(second_row))
                                        for i, branch in enumerate(second_row):
                                            with cols2[i]:
                                                if st.button(f"{branch}", use_container_width=True, key=f"branch_btn_{branch}"):
                                                    st.session_state.selected_branch_ranking = branch
                                    
                                    # デフォルトの選択支部を設定
                                    if 'selected_branch_ranking' not in st.session_state:
                                        st.session_state.selected_branch_ranking = available_branches[0]
                                    
                                    selected_branch = st.session_state.selected_branch_ranking
                                    
                                    # 選択された支部のスタッフをフィルタリング
                                    branch_staff = staff_summary[staff_summary['branch'] == selected_branch]
                                    
                                    if not branch_staff.empty:
                                        
                                        # デバッグ情報を表示
                                        total_taaan_deals = branch_staff['taaan_deals'].sum()
                                        if total_taaan_deals == 0:
                                            st.warning("⚠️ この支部のTAAAN商談数が0件です。基本分析データにTAAAN商談情報が含まれているか確認してください。")
                                        
                                        # 6つのランキングを2列×3行で表示
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            # 1. 架電数ランキング（支部内）
                                            st.markdown("##### 🏆 架電数ランキング (日報)")
                                            display_ranking_with_ties(
                                                branch_staff, 
                                                'total_calls', 
                                                ['total_calls'], 
                                                max_rank=5, 
                                                show_branch=False
                                            )
                                            
                                            st.markdown("---")
                                            
                                            # 2. 担当コネクト数ランキング（支部内）
                                            st.markdown("##### 📞 担当コネクト数ランキング (日報)")
                                            display_ranking_with_ties(
                                                branch_staff, 
                                                'charge_connected', 
                                                ['charge_connected'], 
                                                max_rank=5, 
                                                show_branch=False
                                            )
                                            
                                            st.markdown("---")
                                            
                                            # 3. アポ獲得数ランキング（支部内）
                                            st.markdown("##### 🎯 アポ獲得数ランキング (日報)")
                                            display_ranking_with_ties(
                                                branch_staff, 
                                                'appointments', 
                                                ['appointments'], 
                                                max_rank=5, 
                                                show_branch=False
                                            )
                                        
                                        with col2:
                                            # 4. TAAAN商談数ランキング（支部内）
                                            st.markdown("##### 💼 TAAAN商談数ランキング (TAAAN)")
                                            display_ranking_with_ties(
                                                branch_staff, 
                                                'taaan_deals', 
                                                ['taaan_deals'], 
                                                max_rank=5, 
                                                show_branch=False
                                            )
                                            
                                            st.markdown("---")
                                            
                                            # 5. TAAAN承認数ランキング（支部内）
                                            st.markdown("##### ✅ TAAAN承認数ランキング (TAAAN)")
                                            display_ranking_with_ties(
                                                branch_staff, 
                                                'approved_deals', 
                                                ['approved_deals'], 
                                                max_rank=5, 
                                                show_branch=False
                                            )
                                            
                                            st.markdown("---")
                                            
                                            # 6. TAAAN報酬額ランキング（支部内）
                                            st.markdown("##### 💰 TAAAN報酬額ランキング (TAAAN)")
                                            display_ranking_with_ties(
                                                branch_staff, 
                                                'total_revenue', 
                                                ['total_revenue'], 
                                                max_rank=5, 
                                                show_branch=False
                                            )
                                    else:
                                        st.warning(f"選択された支部 '{selected_branch}' にはスタッフが存在しません。")
                                
                                with staff_subtab3:
                                    st.subheader("⚡ 効率性ランキング")
                                    st.write("時間当たりや稼働日当たりの効率性指標でのランキングです。")
                                    
                                    # 稼働日数を計算する関数
                                    def calculate_working_days(staff_name, basic_data):
                                        """スタッフの稼働日数を計算"""
                                        try:
                                            staff_data = basic_data[basic_data['staff_name'] == staff_name]
                                            # 架電数>0の日をカウント
                                            working_days = len(staff_data[staff_data[call_col] > 0]['date'].unique())
                                            return working_days
                                        except:
                                            return 0
                                    
                                    # 稼働日数を各スタッフについて計算
                                    staff_summary['working_days'] = staff_summary['staff_name'].apply(
                                        lambda x: calculate_working_days(x, df_basic)
                                    )
                                    
                                    # 稼働日数データの可用性をチェック
                                    working_days_available = staff_summary['working_days'].sum() > 0
                                    
                                    # 架電時間データが利用可能かチェック
                                    hours_available = 'call_hours' in df_basic.columns and df_basic['call_hours'].sum() > 0
                                    
                                    if not working_days_available:
                                        st.warning("⚠️ 稼働日数の算出ができませんでした。")
                                        st.info("💡 日報データから稼働日数を計算するには、daily_activityデータまたは日別の架電データが必要です。")
                                    
                                    # 効率性ランキング用のタブ
                                    eff_tab1, eff_tab2 = st.tabs(["⏰ 時間当たり効率", "📅 稼働日当たり効率"])
                                    
                                    with eff_tab1:
                                        if hours_available:
                                            # 架電時間データから時間当たり効率を計算
                                            staff_hours_summary = df_basic.groupby('staff_name').agg({
                                                call_col: 'sum',
                                                'call_hours': 'sum',
                                                appointment_col: 'sum',
                                                'branch': 'first'
                                            }).reset_index()
                                            
                                            staff_hours_summary.columns = ['staff_name', 'total_calls', 'total_hours', 'appointments', 'branch']
                                            
                                            # 時間当たり効率の計算
                                            staff_hours_summary['calls_per_hour'] = (
                                                staff_hours_summary['total_calls'] / staff_hours_summary['total_hours']
                                            ).fillna(0).round(1)
                                            
                                            staff_hours_summary['appointments_per_hour'] = (
                                                staff_hours_summary['appointments'] / staff_hours_summary['total_hours']
                                            ).fillna(0).round(1)
                                            
                                            # TAAANデータを結合（既に作成済みのtaaan_staff_dataを使用）
                                            staff_hours_summary['taaan_deals'] = staff_hours_summary['staff_name'].map(
                                                lambda x: taaan_staff_data.get(x, {}).get('taaan_deals', 0)
                                            )
                                            staff_hours_summary['approved_deals'] = staff_hours_summary['staff_name'].map(
                                                lambda x: taaan_staff_data.get(x, {}).get('approved_deals', 0)
                                            )
                                            staff_hours_summary['total_revenue'] = staff_hours_summary['staff_name'].map(
                                                lambda x: taaan_staff_data.get(x, {}).get('total_revenue', 0)
                                            )
                                            
                                            staff_hours_summary['deals_per_hour'] = (
                                                staff_hours_summary['taaan_deals'] / staff_hours_summary['total_hours']
                                            ).fillna(0).round(1)
                                            
                                            staff_hours_summary['revenue_per_hour'] = (
                                                staff_hours_summary['total_revenue'] / staff_hours_summary['total_hours']
                                            ).fillna(0).round(0)
                                            
                                            # 効率性ランキング表示
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                # 1時間あたり架電数ランキング
                                                st.markdown("##### 📞 1時間あたり架電数ランキング")
                                                display_ranking_with_ties(
                                                    staff_hours_summary, 
                                                    'calls_per_hour', 
                                                    ['calls_per_hour', 'total_hours'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                                
                                                st.markdown("---")
                                                
                                                # 1時間あたりアポ獲得数ランキング
                                                st.markdown("##### 🎯 1時間あたりアポ獲得数ランキング")
                                                display_ranking_with_ties(
                                                    staff_hours_summary, 
                                                    'appointments_per_hour', 
                                                    ['appointments_per_hour', 'appointments'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                            
                                            with col2:
                                                # 1時間あたりTAAAN商談数ランキング
                                                st.markdown("##### 💼 1時間あたりTAAAN商談数ランキング")
                                                display_ranking_with_ties(
                                                    staff_hours_summary, 
                                                    'deals_per_hour', 
                                                    ['deals_per_hour', 'taaan_deals'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                                
                                                st.markdown("---")
                                                
                                                # 1時間あたり報酬額ランキング
                                                st.markdown("##### 💰 1時間あたり報酬額ランキング")
                                                display_ranking_with_ties(
                                                    staff_hours_summary, 
                                                    'revenue_per_hour', 
                                                    ['revenue_per_hour', 'total_revenue'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                        else:
                                            st.warning("⚠️ 架電時間データが利用できないため、時間当たり効率性ランキングを表示できません。")
                                            st.info("💡 GASのJSON生成時に架電時間データが含まれているか確認してください。")
                                    
                                    with eff_tab2:
                                        if working_days_available:
                                            
                                            # 稼働日当たり効率の計算
                                            staff_summary['calls_per_working_day'] = (
                                                staff_summary['total_calls'] / staff_summary['working_days']
                                            ).fillna(0).round(1)
                                            
                                            staff_summary['appointments_per_working_day'] = (
                                                staff_summary['appointments'] / staff_summary['working_days']
                                            ).fillna(0).round(1)
                                            
                                            staff_summary['deals_per_working_day'] = (
                                                staff_summary['taaan_deals'] / staff_summary['working_days']
                                            ).fillna(0).round(1)
                                            
                                            staff_summary['approved_per_working_day'] = (
                                                staff_summary['approved_deals'] / staff_summary['working_days']
                                            ).fillna(0).round(1)
                                            
                                            staff_summary['revenue_per_working_day'] = (
                                                staff_summary['total_revenue'] / staff_summary['working_days']
                                            ).fillna(0).round(0)
                                            
                                            # 稼働日当たり効率性ランキング表示
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                # 1稼働日あたり架電数ランキング
                                                st.markdown("##### 📞 1稼働日あたり架電数ランキング")
                                                display_ranking_with_ties(
                                                    staff_summary, 
                                                    'calls_per_working_day', 
                                                    ['calls_per_working_day', 'working_days'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                                
                                                st.markdown("---")
                                                
                                                # 1稼働日あたりアポ獲得数ランキング
                                                st.markdown("##### 🎯 1稼働日あたりアポ獲得数ランキング")
                                                display_ranking_with_ties(
                                                    staff_summary, 
                                                    'appointments_per_working_day', 
                                                    ['appointments_per_working_day', 'appointments'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                                
                                                st.markdown("---")
                                                
                                                # 1稼働日あたりTAAAN商談数ランキング
                                                st.markdown("##### 💼 1稼働日あたりTAAAN商談数ランキング")
                                                display_ranking_with_ties(
                                                    staff_summary, 
                                                    'deals_per_working_day', 
                                                    ['deals_per_working_day', 'taaan_deals'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                            
                                            with col2:
                                                # 1稼働日あたり承認数ランキング
                                                st.markdown("##### ✅ 1稼働日あたり承認数ランキング")
                                                display_ranking_with_ties(
                                                    staff_summary, 
                                                    'approved_per_working_day', 
                                                    ['approved_per_working_day', 'approved_deals'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                                
                                                st.markdown("---")
                                                
                                                # 1稼働日あたり報酬額ランキング
                                                st.markdown("##### 💰 1稼働日あたり報酬額ランキング")
                                                display_ranking_with_ties(
                                                    staff_summary, 
                                                    'revenue_per_working_day', 
                                                    ['revenue_per_working_day', 'total_revenue'], 
                                                    max_rank=10, 
                                                    branch_colors=branch_colors
                                                )
                                        else:
                                            st.warning("⚠️ 稼働日数データが利用できないため、稼働日当たり効率性ランキングを表示できません。")
                                            st.info("💡 **理由**: 日別の架電データまたは`daily_activity`データが不足している可能性があります。")
                                            st.info("🔧 **解決方法**: GASのJSON生成時に、スタッフの日別活動データ（`daily_activity`）が正しく含まれているか確認してください。")
                                
                                with staff_subtab4:
                                    st.subheader("📈 月別推移(3ヶ月)")
                                    
                                    # 過去3ヶ月のデータを取得
                                    target_months = get_prev_months(selected_month, 3)
                                    
                                    # 月別データを読み込み
                                    with st.spinner("📊 過去3ヶ月のデータを読み込み中..."):
                                        monthly_data = load_multi_month_data(json_data, target_months)
                                    
                                    if not monthly_data:
                                        st.warning("⚠️ 3ヶ月推移に必要なデータが不足しています。")
                                        st.info("💡 過去3ヶ月分のJSONファイルがアップロードされているか確認してください。")
                                    else:
                                        st.success(f"✅ 対象月: {', '.join(sorted(monthly_data.keys()))}")
                                        
                                        # 分析タイプ選択（ラジオボタンで改善）
                                        st.markdown("### 📊 比較タイプ")
                                        comparison_type = st.radio(
                                            "比較タイプ",
                                            ["🌐 全スタッフ比較", "🏢 支部内比較"],
                                            horizontal=True,
                                            key="trend_comparison_type",
                                            label_visibility="collapsed"
                                        )
                                        
                                        st.markdown("---")
                                        
                                        # 分析指標選択（カテゴリ別タブで改善）
                                        st.markdown("### 📈 分析指標選択")
                                        
                                        metric_tab1, metric_tab2, metric_tab3 = st.tabs(["�� 実数指標", "⚡ 時間効率", "📅 日別効率"])
                                        
                                        # 実数指標
                                        with metric_tab1:
                                            metric_cols1 = st.columns(3)
                                            with metric_cols1[0]:
                                                if st.button("📞 架電数", use_container_width=True, key="btn_calls"):
                                                    st.session_state.selected_metric_key = "total_calls"
                                                    st.session_state.selected_metric_name = "📞 架電数 (日報)"
                                                if st.button("💼 TAAAN商談数", use_container_width=True, key="btn_deals"):
                                                    st.session_state.selected_metric_key = "taaan_deals"
                                                    st.session_state.selected_metric_name = "💼 TAAAN商談数 (TAAAN)"
                                            with metric_cols1[1]:
                                                if st.button("🔗 担当コネクト数", use_container_width=True, key="btn_connects"):
                                                    st.session_state.selected_metric_key = "charge_connected"
                                                    st.session_state.selected_metric_name = "🔗 担当コネクト数 (日報)"
                                                if st.button("✅ TAAAN承認数", use_container_width=True, key="btn_approved_1"):
                                                    st.session_state.selected_metric_key = "approved_deals"
                                                    st.session_state.selected_metric_name = "✅ TAAAN承認数 (TAAAN)"
                                            with metric_cols1[2]:
                                                if st.button("🎯 アポ獲得数", use_container_width=True, key="btn_appointments"):
                                                    st.session_state.selected_metric_key = "appointments"
                                                    st.session_state.selected_metric_name = "🎯 アポ獲得数 (日報)"
                                                if st.button("💰 TAAAN報酬額", use_container_width=True, key="btn_revenue_1"):
                                                    st.session_state.selected_metric_key = "total_revenue"
                                                    st.session_state.selected_metric_name = "💰 TAAAN報酬額 (TAAAN)"
                                        
                                        # 時間効率指標
                                        with metric_tab2:
                                            metric_cols2 = st.columns(2)
                                            with metric_cols2[0]:
                                                if st.button("📞 1時間あたり架電数", use_container_width=True, key="btn_calls_hour"):
                                                    st.session_state.selected_metric_key = "calls_per_hour"
                                                    st.session_state.selected_metric_name = "📞 1時間あたり架電数"
                                                if st.button("💼 1時間あたりTAAAN商談数", use_container_width=True, key="btn_deals_hour"):
                                                    st.session_state.selected_metric_key = "deals_per_hour"
                                                    st.session_state.selected_metric_name = "💼 1時間あたりTAAAN商談数"
                                            with metric_cols2[1]:
                                                if st.button("🎯 1時間あたりアポ獲得数", use_container_width=True, key="btn_appt_hour"):
                                                    st.session_state.selected_metric_key = "appointments_per_hour"
                                                    st.session_state.selected_metric_name = "🎯 1時間あたりアポ獲得数"
                                                if st.button("💰 1時間あたり報酬額", use_container_width=True, key="btn_rev_hour"):
                                                    st.session_state.selected_metric_key = "revenue_per_hour"
                                                    st.session_state.selected_metric_name = "💰 1時間あたり報酬額"
                                        
                                        # 日別効率指標
                                        with metric_tab3:
                                            metric_cols3 = st.columns(3)
                                            with metric_cols3[0]:
                                                if st.button("📞 1稼働日あたり架電数", use_container_width=True, key="btn_calls_day"):
                                                    st.session_state.selected_metric_key = "calls_per_working_day"
                                                    st.session_state.selected_metric_name = "📞 1稼働日あたり架電数"
                                                if st.button("✅ 1稼働日あたり承認数", use_container_width=True, key="btn_appr_day"):
                                                    st.session_state.selected_metric_key = "approved_per_working_day"
                                                    st.session_state.selected_metric_name = "✅ 1稼働日あたり承認数"
                                            with metric_cols3[1]:
                                                if st.button("🎯 1稼働日あたりアポ獲得数", use_container_width=True, key="btn_appt_day"):
                                                    st.session_state.selected_metric_key = "appointments_per_working_day"
                                                    st.session_state.selected_metric_name = "🎯 1稼働日あたりアポ獲得数"
                                                if st.button("💰 1稼働日あたり報酬額", use_container_width=True, key="btn_rev_day"):
                                                    st.session_state.selected_metric_key = "revenue_per_working_day"
                                                    st.session_state.selected_metric_name = "💰 1稼働日あたり報酬額"
                                            with metric_cols3[2]:
                                                if st.button("💼 1稼働日あたりTAAAN商談数", use_container_width=True, key="btn_deals_day"):
                                                    st.session_state.selected_metric_key = "deals_per_working_day"
                                                    st.session_state.selected_metric_name = "💼 1稼働日あたりTAAAN商談数"
                                        
                                        # デフォルト選択
                                        if 'selected_metric_key' not in st.session_state:
                                            st.session_state.selected_metric_key = "appointments"
                                            st.session_state.selected_metric_name = "🎯 アポ獲得数 (日報)"
                                        
                                        selected_metric = st.session_state.selected_metric_key
                                        selected_metric_name = st.session_state.selected_metric_name
                                        
                                        # 現在選択中の指標を表示
                                        st.info(f"📊 **現在選択中**: {selected_metric_name}")
                                        
                                        st.markdown("---")
                                        
                                        # 支部内比較の場合は支部選択
                                        staff_filter = None
                                        if comparison_type == "🏢 支部内比較":
                                            # 利用可能な支部を取得
                                            all_branches = set()
                                            for month_df in monthly_data.values():
                                                all_branches.update(month_df['branch'].unique())
                                            available_branches = sorted([b for b in all_branches if pd.notna(b) and b != ''])
                                            
                                            if available_branches:
                                                selected_branch_trend = st.selectbox(
                                                    "🏢 分析対象支部",
                                                    available_branches,
                                                    key="trend_branch"
                                                )
                                                
                                                # 選択支部のスタッフを取得
                                                branch_staff = set()
                                                for month_df in monthly_data.values():
                                                    branch_df = month_df[month_df['branch'] == selected_branch_trend]
                                                    branch_staff.update(branch_df['staff_name'].tolist())
                                                staff_filter = list(branch_staff)
                                                
                                                st.info(f"📍 **{selected_branch_trend}支部** の {len(staff_filter)}名のスタッフを分析対象とします")
                                            else:
                                                st.warning("⚠️ 支部情報が見つかりません。")
                                        else:
                                            # 全スタッフ表示用の情報
                                            total_staff = set()
                                            for month_df in monthly_data.values():
                                                total_staff.update(month_df['staff_name'].tolist())
                                            st.info(f"🌐 **全スタッフ** {len(total_staff)}名を分析対象とします")
                                        
                                        # チャート表示
                                        st.subheader("📊 推移チャート")
                                        
                                        try:
                                            chart = create_trend_chart(
                                                monthly_data, 
                                                selected_metric, 
                                                selected_metric_name,
                                                staff_filter, 
                                                branch_colors
                                            )
                                            st.plotly_chart(chart, use_container_width=True)
                                            
                                            # ヒストグラム表示
                                            st.subheader("📊 月別分布")
                                            hist_chart = create_monthly_histogram(
                                                monthly_data,
                                                selected_metric,
                                                selected_metric_name,
                                                staff_filter
                                            )
                                            st.plotly_chart(hist_chart, use_container_width=True)
                                            
                                        except Exception as e:
                                            st.error(f"❌ チャート生成エラー: {str(e)}")
                                        
                                        # データテーブル表示
                                        st.subheader("📋 詳細データ")
                                        
                                        # 月別比較テーブル作成
                                        comparison_data = []
                                        months = sorted(monthly_data.keys())
                                        
                                        # 全スタッフのデータを取得
                                        all_staff = set()
                                        for month_df in monthly_data.values():
                                            if staff_filter:
                                                month_df = month_df[month_df['staff_name'].isin(staff_filter)]
                                            all_staff.update(month_df['staff_name'].tolist())
                                        
                                        for staff_name in sorted(all_staff):
                                            row_data = {'スタッフ名': staff_name}
                                            
                                            # 支部情報を取得
                                            staff_branch = '未設定'
                                            for month_df in monthly_data.values():
                                                staff_row = month_df[month_df['staff_name'] == staff_name]
                                                if not staff_row.empty:
                                                    staff_branch = staff_row.iloc[0]['branch']
                                                    break
                                            row_data['支部'] = staff_branch
                                            
                                            # 各月のデータを追加
                                            for month in months:
                                                if month in monthly_data:
                                                    month_df = monthly_data[month]
                                                    staff_row = month_df[month_df['staff_name'] == staff_name]
                                                    if not staff_row.empty:
                                                        value = staff_row.iloc[0][selected_metric]
                                                        # フォーマット
                                                        if selected_metric == 'total_revenue':
                                                            formatted_value = f"¥{value:,.0f}"
                                                        elif 'per_hour' in selected_metric:
                                                            formatted_value = f"{value:.1f}"
                                                        elif 'per_working_day' in selected_metric:
                                                            formatted_value = f"{value:.1f}"
                                                        else:
                                                            formatted_value = f"{value:.0f}"
                                                        row_data[month] = formatted_value
                                                    else:
                                                        row_data[month] = "-"
                                                else:
                                                    row_data[month] = "-"
                                            
                                            comparison_data.append(row_data)
                                        
                                        if comparison_data:
                                            comparison_df = pd.DataFrame(comparison_data)
                                            
                                            # 支部別色分け表示（改善版）
                                            def highlight_branch(row):
                                                branch = row['支部']
                                                if branch in branch_colors:
                                                    color = branch_colors[branch]
                                                    # より薄い透明度で背景色を設定
                                                    return [f'background-color: {color}20; border-left: 3px solid {color}'] * len(row)
                                                else:
                                                    return [f'background-color: #f8f9fa; border-left: 3px solid #dee2e6'] * len(row)
                                            
                                            try:
                                                styled_df = comparison_df.style.apply(highlight_branch, axis=1)
                                                st.dataframe(styled_df, use_container_width=True, height=400)
                                                
                                                # 支部色の凡例を表示
                                                st.markdown("**支部色の凡例:**")
                                                legend_cols = st.columns(len(branch_colors))
                                                for i, (branch, color) in enumerate(branch_colors.items()):
                                                    with legend_cols[i % len(legend_cols)]:
                                                        st.markdown(f'<span style="display: inline-block; width: 15px; height: 15px; background-color: {color}; border-radius: 3px; margin-right: 5px;"></span>{branch}', unsafe_allow_html=True)
                                                        
                                            except Exception as e:
                                                # スタイル適用が失敗した場合は通常のデータフレーム表示
                                                st.dataframe(comparison_df, use_container_width=True)
                                                st.warning(f"⚠️ 色分け表示に失敗しました: {str(e)}")
                                            
                                            # 統計情報
                                            st.subheader("📊 統計サマリー")
                                            
                                            stats_cols = st.columns(len(months))
                                            for i, month in enumerate(months):
                                                with stats_cols[i]:
                                                    month_values = []
                                                    for _, row in comparison_df.iterrows():
                                                        val_str = row[month]
                                                        if val_str != "-":
                                                            # 数値を抽出
                                                            try:
                                                                if selected_metric == 'total_revenue':
                                                                    val = float(val_str.replace('¥', '').replace(',', ''))
                                                                else:
                                                                    val = float(val_str)
                                                                month_values.append(val)
                                                            except:
                                                                continue
                                                    
                                                    if month_values:
                                                        avg_val = sum(month_values) / len(month_values)
                                                        max_val = max(month_values)
                                                        min_val = min(month_values)
                                                        
                                                        st.markdown(f"**{month}**")
                                                        if selected_metric == 'total_revenue':
                                                            st.metric("平均", f"¥{avg_val:,.0f}")
                                                            st.metric("最大", f"¥{max_val:,.0f}")
                                                            st.metric("最小", f"¥{min_val:,.0f}")
                                                        else:
                                                            st.metric("平均", f"{avg_val:.1f}")
                                                            st.metric("最大", f"{max_val:.1f}")
                                                            st.metric("最小", f"{min_val:.1f}")
                                        else:
                                            st.warning("⚠️ 表示するデータがありません。")
                            
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
                                        if st.button("✅ 承認数", use_container_width=True, key="btn_approved_2"):
                                            st.session_state.analysis_metric = "承認数"
                                    with col3:
                                        if st.button("💰 確定売上", use_container_width=True, key="btn_revenue_2"):
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
                                    
                                    # 過去3ヶ月の月リスト作成
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
                                            basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, month)
                                            
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
                                    
                                    # 商材別集計
                                    product_summary = df_basic.groupby('product').agg({
                                        'call_count': 'sum',
                                        'charge_connected': 'sum',
                                        'get_appointment': 'sum'
                                    }).reset_index()
                                    
                                    product_summary.columns = ['商材名', '架電数', '担当コネクト数', 'アポ獲得数']
                                    product_summary['架電効率'] = (product_summary['担当コネクト数'] / product_summary['架電数'] * 100).round(1)
                                    product_summary['成約率'] = (product_summary['アポ獲得数'] / product_summary['架電数'] * 100).round(1)
                                    
                                    # 商材別グラフ
                                    fig_product = go.Figure()
                                    
                                    fig_product.add_trace(go.Bar(
                                        x=product_summary['商材名'],
                                        y=product_summary['架電数'],
                                        name='架電数',
                                        marker_color='blue'
                                    ))
                                    
                                    fig_product.add_trace(go.Bar(
                                        x=product_summary['商材名'],
                                        y=product_summary['アポ獲得数'],
                                        name='アポ獲得数',
                                        marker_color='red'
                                    ))
                                    
                                    fig_product.update_layout(
                                        title="商材別実績",
                                        barmode='group',
                                        height=400
                                    )
                                    
                                    st.plotly_chart(fig_product, use_container_width=True)
                                    
                                    # 商材別詳細テーブル
                                    st.subheader("商材別詳細テーブル")
                                    st.dataframe(product_summary, use_container_width=True)
                            
                            with tab5:
                                st.subheader("詳細データ")
                                
                                # フィルター機能
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    selected_branch = st.selectbox(
                                        "支部でフィルター",
                                        ['全て'] + list(df_basic['branch'].unique())
                                    )
                                
                                with col2:
                                    selected_staff = st.selectbox(
                                        "スタッフでフィルター",
                                        ['全て'] + list(df_basic['staff_name'].unique())
                                    )
                                
                                # フィルター適用
                                filtered_df = df_basic.copy()
                                
                                if selected_branch != '全て':
                                    filtered_df = filtered_df[filtered_df['branch'] == selected_branch]
                                
                                if selected_staff != '全て':
                                    filtered_df = filtered_df[filtered_df['staff_name'] == selected_staff]
                                
                                # 詳細データ表示
                                st.dataframe(filtered_df, use_container_width=True)
                                
                                # CSVダウンロード機能
                                csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    label="📥 CSVダウンロード",
                                    data=csv,
                                    file_name=f"詳細データ_{selected_month}.csv",
                                    mime="text/csv"
                                )
                        else:
                            st.warning("⚠️ 架電データが見つかりませんでした")
                    else:
                        st.warning("⚠️ 分析データが見つかりませんでした")
    
    else:
        st.title("📊 インサイドセールス分析ダッシュボード")
        st.markdown("""
        ### 使用方法
        
        1. **データの準備**: 分析したいJSONファイルをZip形式で圧縮してください
        2. **アップロード**: 左サイドバーからZipファイルをアップロードしてください
        3. **分析実行**: アップロード後、分析タイプを選択して分析を開始してください
        
        ### 対応ファイル形式
        
        - `基本分析_YYYY-MM.json`
        - `詳細分析_YYYY-MM.json`
        - `月次サマリー_YYYY-MM.json`
        - `定着率分析_YYYY-MM.json`
        
        ### 注意事項
        
        - ファイル名は上記の形式に従ってください
        - 複数の月のデータを含めることができます
        - 最大ファイルサイズ: 200MB
        """)



# フッター
st.divider()
st.caption("© 2025 架電ダッシュボード - Streamlit版")