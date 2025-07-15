"""月次詳細データページ"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils.data_processor import (
    load_analysis_data_from_json, 
    extract_daily_activity_from_staff,
    get_prev_months,
    load_multi_month_data
)
from components.charts import create_funnel_chart, create_pie_chart, create_trend_chart, create_monthly_histogram
from components.rankings import display_ranking_with_ties
from utils.config import BRANCH_COLORS, CARD_STYLE

def get_prev_months(month_str, n=3):
    """指定月から過去n月分の月リストを取得"""
    base = datetime.strptime(month_str, '%Y-%m')
    return [(base - timedelta(days=30*i)).strftime('%Y-%m') for i in reversed(range(n))]

def render_monthly_detail_page(json_data, selected_month):
    """月次詳細データページをレンダリング"""
    st.header("📋 単月詳細データ")
    st.caption(f"選択月: {selected_month}")
    
    basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, selected_month)
    
    if basic_data and detail_data and summary_data:
        # データフレーム作成
        try:
            staff_dict = basic_data["monthly_analysis"][selected_month]["staff"]
            df_basic = extract_daily_activity_from_staff(staff_dict)
        except Exception as e:
            st.error(f"データ抽出エラー: {e}")
            df_basic = pd.DataFrame()
        
        # 営業フロー指標セクション
        render_sales_flow_metrics(df_basic, summary_data)
        
        # メインタブセクション
        render_main_tabs(df_basic, basic_data, detail_data, summary_data, selected_month, json_data)
    else:
        st.warning("⚠️ 分析データが見つかりませんでした")

def render_sales_flow_metrics(df_basic, summary_data):
    """営業フロー指標セクションをレンダリング"""
    st.subheader("営業フロー指標")
    st.info("フロー: 架電数 → 担当コネクト → アポ獲得 → TAAAN入力")

    if not df_basic.empty:
        # 基本指標の計算
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

        # カードスタイルで指標を表示
        render_metric_cards(total_calls, charge_connected, appointments, total_deals, 
                           total_revenue, total_potential_revenue)
        
        # 変換率の計算と表示
        render_conversion_rates(total_calls, charge_connected, appointments, total_deals, total_approved)
        
        # ファネルチャート
        render_funnel_chart(total_calls, charge_connected, appointments, total_deals)
        
        # 商談ステータス詳細
        render_deal_status_detail(summary_data)

def render_metric_cards(total_calls, charge_connected, appointments, total_deals, 
                       total_revenue, total_potential_revenue):
    """指標カードをレンダリング"""
    # (a) 架電数セット（青系グラデーション）
    card_data = [
        {"label": "架電数", "value": f"{total_calls:,}件", "desc": "日報上で報告された架電数", "color": "#01478c"},
        {"label": "担当コネクト数", "value": f"{charge_connected:,}件", "desc": "日報上で報告された担当コネクト数", "color": "#1976d2"},
        {"label": "アポ獲得数", "value": f"{appointments:,}件", "desc": "日報上で報告されたアポ獲得数", "color": "#42a5f5"},
        {"label": "TAAAN商談数", "value": f"{total_deals:,}件", "desc": "TAAANに入力された件数", "color": "#90caf9"},
    ]
    cols = st.columns(len(card_data))
    for i, card in enumerate(card_data):
        cols[i].markdown(CARD_STYLE.format(**card), unsafe_allow_html=True)

    # (b) 売上セット（緑系グラデーション）
    revenue_card_data = [
        {"label": "確定売上", "value": f"¥{total_revenue:,}", "desc": "TAAAN入力で商談ステータスが「承認」の報酬合計", "color": "#055709"},
        {"label": "潜在売上", "value": f"¥{total_potential_revenue:,}", "desc": "TAAAN入力で商談ステータスが「承認待ち」または「要対応」の報酬合計", "color": "#388e3c"},
        {"label": "総売上", "value": f"¥{total_revenue + total_potential_revenue:,}", "desc": "確定売上と潜在売上の合計", "color": "#81c784"},
    ]
    revenue_cols = st.columns(len(revenue_card_data))
    for i, card in enumerate(revenue_card_data):
        revenue_cols[i].markdown(CARD_STYLE.format(**card), unsafe_allow_html=True)

def render_conversion_rates(total_calls, charge_connected, appointments, total_deals, total_approved):
    """変換率カードをレンダリング"""
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
        rate_cols[i].markdown(CARD_STYLE.format(**card), unsafe_allow_html=True)

def render_funnel_chart(total_calls, charge_connected, appointments, total_deals):
    """ファネルチャートをレンダリング"""
    funnel_labels = ["架電数", "担当コネクト数", "アポ獲得数", "TAAAN商談数"]
    funnel_values = [total_calls, charge_connected, appointments, total_deals]
    fig = create_funnel_chart(funnel_values, funnel_labels)
    st.plotly_chart(fig, use_container_width=True)

def render_deal_status_detail(summary_data):
    """商談ステータス詳細をレンダリング"""
    if 'deal_status_breakdown' in summary_data:
        st.subheader("商談ステータス詳細")
        deal_status = summary_data['deal_status_breakdown']
        approved = deal_status.get('approved', 0)
        rejected = deal_status.get('rejected', 0)
        pending = deal_status.get('pending', 0)
        
        fig = create_pie_chart(
            ['承認', '却下', '承認待ち・要対応'],
            [approved, rejected, pending],
            "商談ステータス分布",
            ['#00ff00', '#ff0000', '#ffaa00']
        )
        st.plotly_chart(fig, use_container_width=True)

def render_main_tabs(df_basic, basic_data, detail_data, summary_data, selected_month, json_data):
    """メインタブセクションをレンダリング"""
    # データ存在チェック
    has_call_data = (not df_basic.empty and 
                    ('call_count' in df_basic.columns or 'total_calls' in df_basic.columns))
    
    if has_call_data:
        # タブを作成
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 日次トレンド", "🏢 支部別分析", "👥 スタッフ別分析", "📦 商材別分析", "📋 詳細データ"])
        
        with tab1:
            render_daily_trend_tab(df_basic)
        
        with tab2:
            render_branch_analysis_tab(df_basic, summary_data, selected_month, json_data)
        
        with tab3:
            render_staff_analysis_tab(df_basic, basic_data, summary_data, selected_month, json_data)
        
        with tab4:
            render_product_analysis_tab(df_basic, summary_data, json_data, selected_month)
        
        with tab5:
            render_detail_data_tab(df_basic, selected_month)
    else:
        st.warning("⚠️ 架電データが見つかりませんでした")

def render_daily_trend_tab(df_basic):
    """日次トレンドタブをレンダリング"""
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

def render_branch_analysis_tab(df_basic, summary_data, selected_month, json_data):
    """支部別分析タブをレンダリング"""
    st.subheader("支部別分析")
    
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
    
    # TAAAN データの追加
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
        (branch_summary['approved_deals'] / branch_summary['taaan_deals'] * 100)
        .fillna(0)
        .round(1)
    )
    
    # サブタブを追加
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "実数", "単位あたり分析", "実数3ヶ月比較", "単位あたり3ヶ月比較"
    ])
    
    with subtab1:
        st.markdown("#### 実数")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 架電数グラフ
            fig_branch_calls = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_calls.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['total_calls'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
                # 架電時間数グラフ
                fig_branch_hours = go.Figure()
                for branch in branch_summary['branch']:
                    branch_data = branch_summary[branch_summary['branch'] == branch]
                    fig_branch_hours.add_trace(go.Bar(
                        x=[branch],
                        y=branch_data['call_hours'],
                        name=branch,
                        marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
            # 担当コネクト数グラフ
            fig_branch_connect = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_connect.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['charge_connected'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
            # アポ獲得数グラフ
            fig_branch_appointments = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_appointments.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['appointments'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
            # TAAAN商談数グラフ
            fig_branch_taaan = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_taaan.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['taaan_deals'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
            # 承認済み商談数グラフ
            fig_branch_approved = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_approved.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['approved_deals'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
                    showlegend=False,
                    hovertemplate='<b>%{x}</b><br>承認済み商談数: %{y:,}件<extra></extra>'
                ))
            fig_branch_approved.update_layout(
                title='承認済み商談数',
                yaxis_title='承認済み商談数',
                showlegend=False,
                yaxis=dict(tickformat=',', separatethousands=True)
            )
            st.plotly_chart(fig_branch_approved, use_container_width=True)
        
        col7, col8 = st.columns(2)
        
        with col7:
            # 報酬合計額グラフ
            fig_branch_reward = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_reward.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['total_revenue'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
            # ユニーク稼働者数グラフ
            fig_branch_staff = go.Figure()
            for branch in branch_summary['branch']:
                branch_data = branch_summary[branch_summary['branch'] == branch]
                fig_branch_staff.add_trace(go.Bar(
                    x=[branch],
                    y=branch_data['unique_staff_count'],
                    name=branch,
                    marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
        
        # 支部別サマリーテーブル
        st.markdown("#### 支部別サマリーテーブル")
        display_table = branch_summary.copy()
        # 数値フォーマット
        display_table['total_calls'] = display_table['total_calls'].apply(lambda x: f"{x:,}")
        display_table['charge_connected'] = display_table['charge_connected'].apply(lambda x: f"{x:,}")
        display_table['appointments'] = display_table['appointments'].apply(lambda x: f"{x:,}")
        display_table['taaan_deals'] = display_table['taaan_deals'].apply(lambda x: f"{x:,}")
        display_table['approved_deals'] = display_table['approved_deals'].apply(lambda x: f"{x:,}")
        display_table['connect_rate'] = display_table['connect_rate'].apply(lambda x: f"{x:.1f}%")
        display_table['appointment_rate'] = display_table['appointment_rate'].apply(lambda x: f"{x:.1f}%")
        display_table['approval_rate'] = display_table['approval_rate'].apply(lambda x: f"{x:.1f}%")
        
        # 列名を日本語に変更
        display_table = display_table.rename(columns={
            'branch': '支部',
            'total_calls': '架電数',
            'charge_connected': '担当コネクト',
            'appointments': 'アポ獲得',
            'taaan_deals': 'TAAAN商談',
            'approved_deals': '承認済み',
            'connect_rate': 'コネクト率',
            'appointment_rate': 'アポ率',
            'approval_rate': '承認率',
            'unique_staff_count': 'スタッフ数'
        })
        
        # 表示する列を選択
        display_columns = ['支部', 'スタッフ数', '架電数', '担当コネクト', 'アポ獲得', 'TAAAN商談', '承認済み', 'コネクト率', 'アポ率', '承認率']
        st.dataframe(display_table[display_columns], use_container_width=True)
    
    with subtab2:
        st.markdown("#### 単位あたり分析")
        
        # 1人あたり指標の計算
        unit_df = branch_summary.copy()
        unit_df['total_calls_per_staff'] = unit_df['total_calls'] / unit_df['unique_staff_count'].replace(0, float('nan'))
        unit_df['call_hours_per_staff'] = unit_df['call_hours'] / unit_df['unique_staff_count'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        unit_df['charge_connected_per_staff'] = unit_df['charge_connected'] / unit_df['unique_staff_count'].replace(0, float('nan'))
        unit_df['appointments_per_staff'] = unit_df['appointments'] / unit_df['unique_staff_count'].replace(0, float('nan'))
        unit_df['taaan_deals_per_staff'] = unit_df['taaan_deals'] / unit_df['unique_staff_count'].replace(0, float('nan'))
        unit_df['approved_deals_per_staff'] = unit_df['approved_deals'] / unit_df['unique_staff_count'].replace(0, float('nan'))
        unit_df['revenue_per_staff'] = unit_df['total_revenue'] / unit_df['unique_staff_count'].replace(0, float('nan'))
        
        # 時間あたり指標の計算
        unit_df['total_calls_per_hour'] = unit_df['total_calls'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        unit_df['charge_connected_per_hour'] = unit_df['charge_connected'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        unit_df['appointments_per_hour'] = unit_df['appointments'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        unit_df['taaan_deals_per_hour'] = unit_df['taaan_deals'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        unit_df['approved_deals_per_hour'] = unit_df['approved_deals'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        unit_df['revenue_per_hour'] = unit_df['total_revenue'] / unit_df['call_hours'].replace(0, float('nan')) if 'call_hours' in unit_df.columns else float('nan')
        
        # 1人あたり指標表示
        st.markdown("##### 1人あたり指標")
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
                        marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
                        marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
                        marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
        
        # 時間あたり指標表示
        st.markdown("##### 時間あたり指標")
        if 'call_hours' in unit_df.columns:
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
                            marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
                            marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
                            marker_color=BRANCH_COLORS.get(branch, '#95a5a6'),
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
        else:
            st.info("時間あたり指標の表示には架電時間データが必要です")
    
    with subtab3:
        st.markdown("#### 実数3ヶ月比較")
        
        # 比較月リスト作成
        compare_months = get_prev_months(selected_month, 3)
        st.info(f"比較対象月: {', '.join(compare_months)}")
        
        # 各月の支部別集計を取得
        branch_summaries = {}
        for m in compare_months:
            b, d, s = load_analysis_data_from_json(json_data, m)
            if b and s:
                try:
                    staff_dict = b["monthly_analysis"][m]["staff"]
                    df_b = extract_daily_activity_from_staff(staff_dict)
                    df_b["branch"] = df_b["branch"].fillna("未設定")
                    
                    # 基本集計
                    unique_staff = df_b.groupby('branch')['staff_name'].nunique().reset_index()
                    unique_staff.columns = ['branch', 'unique_staff_count']
                    
                    call_col = 'call_count' if 'call_count' in df_b.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_b.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_b.columns else 'successful_calls'
                    hours_col = 'call_hours' if 'call_hours' in df_b.columns else None
                    
                    agg_dict = {call_col: 'sum', success_col: 'sum', appointment_col: 'sum'}
                    if hours_col:
                        agg_dict[hours_col] = 'sum'
                    
                    branch_df = df_b.groupby('branch').agg(agg_dict).reset_index()
                    
                    # カラム名を統一
                    columns = ['branch', 'call_count', 'charge_connected', 'get_appointment']
                    if hours_col:
                        columns.append('call_hours')
                    branch_df.columns = columns
                    
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
                    st.warning(f"{m}月のデータ読み込みエラー: {e}")
                    branch_summaries[m] = None
            else:
                branch_summaries[m] = None
        
        # 指標リスト
        indicators = [
            ('call_count', '架電数'),
            ('call_hours', '架電時間数'),
            ('charge_connected', '担当コネクト数'),
            ('get_appointment', 'アポ獲得数'),
            ('total_deals', 'TAAAN商談数'),
            ('total_approved', '承認数'),
            ('total_revenue', '報酬合計額'),
            ('unique_staff_count', 'ユニーク稼働者数')
        ]
        
        # 3列レイアウトで指標を表示
        for i in range(0, len(indicators), 3):
            cols = st.columns(3)
            for j, (col, label) in enumerate(indicators[i:i+3]):
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
                        color_sequence = [BRANCH_COLORS.get(branch, '#95a5a6') for branch in plot_df['branch'].unique()]
                        
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
                            ),
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("データがありません")
    
    with subtab4:
        st.markdown("#### 単位あたり3ヶ月比較")
        
        # 比較月リスト作成（実数3ヶ月比較と同じデータを使用）
        compare_months = get_prev_months(selected_month, 3)
        st.info(f"比較対象月: {', '.join(compare_months)}")
        
        # 各月の支部別集計を取得（実数3ヶ月比較と同じロジック）
        branch_summaries = {}
        for m in compare_months:
            b, d, s = load_analysis_data_from_json(json_data, m)
            if b and s:
                try:
                    staff_dict = b["monthly_analysis"][m]["staff"]
                    df_b = extract_daily_activity_from_staff(staff_dict)
                    df_b["branch"] = df_b["branch"].fillna("未設定")
                    
                    # 基本集計
                    unique_staff = df_b.groupby('branch')['staff_name'].nunique().reset_index()
                    unique_staff.columns = ['branch', 'unique_staff_count']
                    
                    call_col = 'call_count' if 'call_count' in df_b.columns else 'total_calls'
                    appointment_col = 'get_appointment' if 'get_appointment' in df_b.columns else 'appointments'
                    success_col = 'charge_connected' if 'charge_connected' in df_b.columns else 'successful_calls'
                    hours_col = 'call_hours' if 'call_hours' in df_b.columns else None
                    
                    agg_dict = {call_col: 'sum', success_col: 'sum', appointment_col: 'sum'}
                    if hours_col:
                        agg_dict[hours_col] = 'sum'
                    
                    branch_df = df_b.groupby('branch').agg(agg_dict).reset_index()
                    
                    # カラム名を統一
                    columns = ['branch', 'call_count', 'charge_connected', 'get_appointment']
                    if hours_col:
                        columns.append('call_hours')
                    branch_df.columns = columns
                    
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
                    st.warning(f"{m}月のデータ読み込みエラー: {e}")
                    branch_summaries[m] = None
            else:
                branch_summaries[m] = None
        
        # 単位あたり指標リスト
        unit_indicators = [
            ('total_calls_per_staff', '1人あたり架電数'),
            ('call_hours_per_staff', '1人あたり架電時間数'),
            ('charge_connected_per_staff', '1人あたり担当コネクト数'),
            ('appointments_per_staff', '1人あたりアポ獲得数'),
            ('taaan_deals_per_staff', '1人あたりTAAAN商談数'),
            ('approved_deals_per_staff', '1人あたり承認数'),
            ('revenue_per_staff', '1人あたり報酬合計額'),
            ('total_calls_per_hour', '時間あたり架電数'),
            ('charge_connected_per_hour', '時間あたり担当コネクト数'),
            ('appointments_per_hour', '時間あたりアポ獲得数'),
            ('taaan_deals_per_hour', '時間あたりTAAAN商談数'),
            ('approved_deals_per_hour', '時間あたり承認数'),
            ('revenue_per_hour', '時間あたり報酬合計額')
        ]
        
        # 各月の単位あたり指標を計算
        unit_monthly = {}
        for m in compare_months:
            df = branch_summaries.get(m)
            if df is not None:
                u = df.copy()
                # 1人あたり指標
                u['total_calls_per_staff'] = u['call_count'] / u['unique_staff_count'].replace(0, float('nan'))
                u['call_hours_per_staff'] = u['call_hours'] / u['unique_staff_count'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                u['charge_connected_per_staff'] = u['charge_connected'] / u['unique_staff_count'].replace(0, float('nan'))
                u['appointments_per_staff'] = u['get_appointment'] / u['unique_staff_count'].replace(0, float('nan'))
                u['taaan_deals_per_staff'] = u['total_deals'] / u['unique_staff_count'].replace(0, float('nan'))
                u['approved_deals_per_staff'] = u['total_approved'] / u['unique_staff_count'].replace(0, float('nan'))
                u['revenue_per_staff'] = u['total_revenue'] / u['unique_staff_count'].replace(0, float('nan'))
                
                # 時間あたり指標
                u['total_calls_per_hour'] = u['call_count'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                u['charge_connected_per_hour'] = u['charge_connected'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                u['appointments_per_hour'] = u['get_appointment'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                u['taaan_deals_per_hour'] = u['total_deals'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                u['approved_deals_per_hour'] = u['total_approved'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                u['revenue_per_hour'] = u['total_revenue'] / u['call_hours'].replace(0, float('nan')) if 'call_hours' in u.columns else float('nan')
                
                unit_monthly[m] = u
            else:
                unit_monthly[m] = None
        
        # 3列レイアウトで指標を表示
        for i in range(0, len(unit_indicators), 3):
            cols = st.columns(3)
            for j, (col, label) in enumerate(unit_indicators[i:i+3]):
                with cols[j]:
                    st.markdown(f"##### {label}（支部別3ヶ月比較）")
                    plot_df = []
                    for m in compare_months:
                        df = unit_monthly.get(m)
                        if df is not None and col in df.columns:
                            for _, row in df.iterrows():
                                # NaNや無限大値をスキップ
                                value = row[col]
                                if pd.notna(value) and value != float('inf') and value != float('-inf'):
                                    plot_df.append({"month": m, "branch": row['branch'], "value": value})
                    
                    if plot_df:
                        plot_df = pd.DataFrame(plot_df)
                        # 統一した色パレットを使用
                        color_sequence = [BRANCH_COLORS.get(branch, '#95a5a6') for branch in plot_df['branch'].unique()]
                        
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
                            ),
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("データがありません")

def render_staff_analysis_tab(df_basic, basic_data, summary_data, selected_month, json_data):
    """スタッフ別分析タブをレンダリング"""
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
        
        # データ概要
        st.info(f"📋 データ概要: 総スタッフ数 {total_staff_count}名、TAAANデータあり {staff_with_taaan}名")
        
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
                branch_colors=BRANCH_COLORS
            )
            
            st.markdown("---")
            
            # 2. 担当コネクト数ランキング
            st.markdown("##### 📞 担当コネクト数ランキング (日報)")
            display_ranking_with_ties(
                staff_summary, 
                'charge_connected', 
                ['charge_connected'], 
                max_rank=10, 
                branch_colors=BRANCH_COLORS
            )
            
            st.markdown("---")
            
            # 3. アポ獲得数ランキング
            st.markdown("##### 🎯 アポ獲得数ランキング (日報)")
            display_ranking_with_ties(
                staff_summary, 
                'appointments', 
                ['appointments'], 
                max_rank=10, 
                branch_colors=BRANCH_COLORS
            )
        
        with col2:
            # 4. TAAAN商談数ランキング
            st.markdown("##### 💼 TAAAN商談数ランキング (TAAAN)")
            if staff_with_taaan > 0:
                display_ranking_with_ties(
                    staff_summary[staff_summary['taaan_deals'] > 0], 
                    'taaan_deals', 
                    ['taaan_deals'], 
                    max_rank=10, 
                    branch_colors=BRANCH_COLORS
                )
            else:
                st.info("TAAANデータがありません")
            
            st.markdown("---")
            
            # 5. TAAAN承認数ランキング
            st.markdown("##### ✅ TAAAN承認数ランキング (TAAAN)")
            if staff_with_taaan > 0:
                display_ranking_with_ties(
                    staff_summary[staff_summary['approved_deals'] > 0], 
                    'approved_deals', 
                    ['approved_deals'], 
                    max_rank=10, 
                    branch_colors=BRANCH_COLORS
                )
            else:
                st.info("承認データがありません")
            
            st.markdown("---")
            
            # 6. TAAAN報酬額ランキング
            st.markdown("##### 💰 TAAAN報酬額ランキング (TAAAN)")
            if staff_with_taaan > 0:
                display_ranking_with_ties(
                    staff_summary[staff_summary['total_revenue'] > 0], 
                    'total_revenue', 
                    ['total_revenue'], 
                    max_rank=10, 
                    branch_colors=BRANCH_COLORS,
                    format_as_currency=True
                )
            else:
                st.info("売上データがありません")
    
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
                call_col = 'call_count' if 'call_count' in basic_data.columns else 'total_calls'
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
        eff_tab1, eff_tab2, eff_tab3 = st.tabs(["📊 成約率分析", "⏰ 時間当たり効率", "📅 稼働日当たり効率"])
        
        with eff_tab1:
            st.markdown("#### 成約率分析")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # コネクト率ランキング
                st.markdown("##### 📞 コネクト率ランキング", help="**コネクト率の定義**: 担当コネクト数 ÷ 架電数 × 100（%）\n\n架電のうち、どの程度の割合で担当者とつながることができたかを示す指標です。")
                # 最低架電数のフィルター
                min_calls_for_rate = st.slider("最低架電数", 1, 100, 20, key="connect_rate_filter")
                connect_rate_filtered = staff_summary[staff_summary['total_calls'] >= min_calls_for_rate]
                if not connect_rate_filtered.empty:
                    display_ranking_with_ties(
                        connect_rate_filtered, 
                        'connect_rate', 
                        ['connect_rate'], 
                        max_rank=10, 
                        branch_colors=BRANCH_COLORS,
                        format_as_percent=True
                    )
                else:
                    st.info("条件に該当するデータがありません")
                
                st.markdown("---")
                
                # 承認率ランキング
                st.markdown("##### ✅ 承認率ランキング", help="**承認率の定義**: 承認数 ÷ TAAAN商談数 × 100（%）\n\nTAAANに入力した商談のうち、どの程度の割合で承認されたかを示す指標です。")
                min_deals_for_approval = st.slider("最低商談数", 1, 20, 3, key="approval_rate_filter")
                approval_rate_filtered = staff_summary[
                    (staff_summary['taaan_deals'] >= min_deals_for_approval) & 
                    (staff_summary['taaan_deals'] > 0)
                ]
                if not approval_rate_filtered.empty:
                    display_ranking_with_ties(
                        approval_rate_filtered, 
                        'approval_rate', 
                        ['approval_rate'], 
                        max_rank=10, 
                        branch_colors=BRANCH_COLORS,
                        format_as_percent=True
                    )
                else:
                    st.info("条件に該当するデータがありません")
            
            with col2:
                # アポ率ランキング
                st.markdown("##### 🎯 アポ率ランキング", help="**アポ率の定義**: アポ獲得数 ÷ 担当コネクト数 × 100（%）\n\n担当者とつながった通話のうち、どの程度の割合でアポを獲得できたかを示す指標です。")
                min_connects_for_appt = st.slider("最低コネクト数", 1, 50, 10, key="appt_rate_filter")
                appt_rate_filtered = staff_summary[staff_summary['charge_connected'] >= min_connects_for_appt]
                if not appt_rate_filtered.empty:
                    display_ranking_with_ties(
                        appt_rate_filtered, 
                        'appointment_rate', 
                        ['appointment_rate'], 
                        max_rank=10, 
                        branch_colors=BRANCH_COLORS,
                        format_as_percent=True
                    )
                else:
                    st.info("条件に該当するデータがありません")
        
        with eff_tab2:
            if hours_available:
                # 架電時間データから時間当たり効率を計算
                call_col = 'call_count' if 'call_count' in df_basic.columns else 'total_calls'
                appointment_col = 'get_appointment' if 'get_appointment' in df_basic.columns else 'appointments'
                
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
                
                # TAAANデータを結合
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
                    min_hours_calls = st.slider("最低架電時間（時間）", 1, 50, 10, key="calls_hour_filter")
                    calls_hour_filtered = staff_hours_summary[staff_hours_summary['total_hours'] >= min_hours_calls]
                    if not calls_hour_filtered.empty:
                        display_ranking_with_ties(
                            calls_hour_filtered, 
                            'calls_per_hour', 
                            ['calls_per_hour', 'total_hours'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                    
                    st.markdown("---")
                    
                    # 1時間あたりアポ獲得数ランキング
                    st.markdown("##### 🎯 1時間あたりアポ獲得数ランキング")
                    min_hours_appt = st.slider("最低架電時間（時間）", 1, 50, 10, key="appt_hour_filter")
                    appt_hour_filtered = staff_hours_summary[staff_hours_summary['total_hours'] >= min_hours_appt]
                    if not appt_hour_filtered.empty:
                        display_ranking_with_ties(
                            appt_hour_filtered, 
                            'appointments_per_hour', 
                            ['appointments_per_hour', 'appointments'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                
                with col2:
                    # 1時間あたりTAAAN商談数ランキング
                    st.markdown("##### 💼 1時間あたりTAAAN商談数ランキング")
                    min_hours_deals = st.slider("最低架電時間（時間）", 1, 50, 10, key="deals_hour_filter")
                    deals_hour_filtered = staff_hours_summary[staff_hours_summary['total_hours'] >= min_hours_deals]
                    if not deals_hour_filtered.empty:
                        display_ranking_with_ties(
                            deals_hour_filtered, 
                            'deals_per_hour', 
                            ['deals_per_hour', 'taaan_deals'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                    
                    st.markdown("---")
                    
                    # 1時間あたり報酬額ランキング
                    st.markdown("##### 💰 1時間あたり報酬額ランキング")
                    min_hours_revenue = st.slider("最低架電時間（時間）", 1, 50, 10, key="revenue_hour_filter")
                    revenue_hour_filtered = staff_hours_summary[staff_hours_summary['total_hours'] >= min_hours_revenue]
                    if not revenue_hour_filtered.empty:
                        display_ranking_with_ties(
                            revenue_hour_filtered, 
                            'revenue_per_hour', 
                            ['revenue_per_hour', 'total_revenue'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
            else:
                st.warning("⚠️ 架電時間データが利用できないため、時間当たり効率性ランキングを表示できません。")
                st.info("💡 GASのJSON生成時に架電時間データが含まれているか確認してください。")
        
        with eff_tab3:
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
                    min_working_days_calls = st.slider("最低稼働日数", 1, 30, 5, key="calls_day_filter")
                    calls_day_filtered = staff_summary[staff_summary['working_days'] >= min_working_days_calls]
                    if not calls_day_filtered.empty:
                        display_ranking_with_ties(
                            calls_day_filtered, 
                            'calls_per_working_day', 
                            ['calls_per_working_day', 'working_days'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                    
                    st.markdown("---")
                    
                    # 1稼働日あたりアポ獲得数ランキング
                    st.markdown("##### 🎯 1稼働日あたりアポ獲得数ランキング")
                    min_working_days_appt = st.slider("最低稼働日数", 1, 30, 5, key="appt_day_filter")
                    appt_day_filtered = staff_summary[staff_summary['working_days'] >= min_working_days_appt]
                    if not appt_day_filtered.empty:
                        display_ranking_with_ties(
                            appt_day_filtered, 
                            'appointments_per_working_day', 
                            ['appointments_per_working_day', 'appointments'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                    
                    st.markdown("---")
                    
                    # 1稼働日あたりTAAAN商談数ランキング
                    st.markdown("##### 💼 1稼働日あたりTAAAN商談数ランキング")
                    min_working_days_deals = st.slider("最低稼働日数", 1, 30, 5, key="deals_day_filter")
                    deals_day_filtered = staff_summary[staff_summary['working_days'] >= min_working_days_deals]
                    if not deals_day_filtered.empty:
                        display_ranking_with_ties(
                            deals_day_filtered, 
                            'deals_per_working_day', 
                            ['deals_per_working_day', 'taaan_deals'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                
                with col2:
                    # 1稼働日あたり承認数ランキング
                    st.markdown("##### ✅ 1稼働日あたり承認数ランキング")
                    min_working_days_approved = st.slider("最低稼働日数", 1, 30, 5, key="approved_day_filter")
                    approved_day_filtered = staff_summary[staff_summary['working_days'] >= min_working_days_approved]
                    if not approved_day_filtered.empty:
                        display_ranking_with_ties(
                            approved_day_filtered, 
                            'approved_per_working_day', 
                            ['approved_per_working_day', 'approved_deals'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
                    
                    st.markdown("---")
                    
                    # 1稼働日あたり報酬額ランキング
                    st.markdown("##### 💰 1稼働日あたり報酬額ランキング")
                    min_working_days_revenue = st.slider("最低稼働日数", 1, 30, 5, key="revenue_day_filter")
                    revenue_day_filtered = staff_summary[staff_summary['working_days'] >= min_working_days_revenue]
                    if not revenue_day_filtered.empty:
                        display_ranking_with_ties(
                            revenue_day_filtered, 
                            'revenue_per_working_day', 
                            ['revenue_per_working_day', 'total_revenue'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info("条件に該当するデータがありません")
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
            
            metric_tab1, metric_tab2, metric_tab3 = st.tabs(["📊 実数指標", "⚡ 時間効率", "📅 日別効率"])
            
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
            st.subheader("📊 推移チャート", help="**推移チャートの見方**:\n\n• **折れ線**: 各スタッフの3ヶ月間の指標の変化\n• **色分け**: スタッフごとに異なる色で表示\n• **凡例**: スタッフ名（支部名）を表示\n• **ホバー**: 線上にマウスを置くと、そのスタッフの詳細データを表示")
            
            try:
                chart = create_trend_chart(
                    monthly_data, 
                    selected_metric, 
                    selected_metric_name,
                    staff_filter, 
                    BRANCH_COLORS
                )
                st.plotly_chart(chart, use_container_width=True)
                
                # ヒストグラム表示
                st.subheader("📊 月別分布", help="**ヒストグラムの見方**:\n\n• **横軸**: 指標の値の範囲\n• **縦軸**: 頻度（その値を持つスタッフの人数）\n• **n**: 各月のデータがあるスタッフの総数\n• **分布の比較**: 月ごとの色で、同じ指標の分布の変化を確認できます")
                hist_chart = create_monthly_histogram(
                    monthly_data,
                    selected_metric,
                    selected_metric_name,
                    staff_filter
                )
                st.plotly_chart(hist_chart, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ チャート生成エラー: {str(e)}")
            
            # 基本的なデータテーブル表示
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
                        if not staff_row.empty and selected_metric in staff_row.columns:
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
                st.dataframe(comparison_df, use_container_width=True, height=400)
                
                # 統計情報
                st.subheader("📊 統計サマリー")
                
                stats_cols = st.columns(len(months))
                for i, month in enumerate(months):
                    with stats_cols[i]:
                        month_values = []
                        for _, row in comparison_df.iterrows():
                            val_str = row[month]
                            if val_str != "-":
                                # 数値を抽出（¥記号などを除去）
                                val_clean = val_str.replace('¥', '').replace(',', '')
                                try:
                                    month_values.append(float(val_clean))
                                except:
                                    pass
                        
                        if month_values:
                            avg_val = sum(month_values) / len(month_values)
                            max_val = max(month_values)
                            min_val = min(month_values)
                            
                            st.markdown(f"**{month}月**")
                            if selected_metric == 'total_revenue':
                                st.metric("平均", f"¥{avg_val:,.0f}")
                                st.metric("最大", f"¥{max_val:,.0f}")
                                st.metric("最小", f"¥{min_val:,.0f}")
                            else:
                                st.metric("平均", f"{avg_val:.1f}")
                                st.metric("最大", f"{max_val:.1f}")
                                st.metric("最小", f"{min_val:.1f}")
                        else:
                            st.markdown(f"**{month}月**")
                            st.info("データなし")

def render_product_analysis_tab(df_basic, summary_data, json_data, selected_month):
    """商材別分析タブをレンダリング"""
    st.subheader("商材別分析")
    
    # 商材別データの集計
    if 'product_performance' in summary_data:
        product_data = summary_data['product_performance']
        
        # データフレーム作成
        product_df = []
        for product, data in product_data.items():
            product_df.append({
                'product': product,
                'total_deals': data.get('total_deals', 0),
                'approved_deals': data.get('total_approved', 0),
                'total_revenue': data.get('total_revenue', 0),
                'total_potential_revenue': data.get('total_potential_revenue', 0)
            })
        
        if product_df:
            product_df = pd.DataFrame(product_df)
            
            # 承認率を計算
            product_df['approval_rate'] = (
                (product_df['approved_deals'] / product_df['total_deals'] * 100)
                .fillna(0)
                .round(1)
            )
            
            # 商材別グラフ表示
            col1, col2 = st.columns(2)
            
            with col1:
                # 商談数グラフ
                fig_deals = create_pie_chart(
                    product_df['product'].tolist(),
                    product_df['total_deals'].tolist(),
                    "商材別商談数分布"
                )
                st.plotly_chart(fig_deals, use_container_width=True)
                
                # 承認数グラフ
                fig_approved = create_pie_chart(
                    product_df['product'].tolist(),
                    product_df['approved_deals'].tolist(),
                    "商材別承認数分布"
                )
                st.plotly_chart(fig_approved, use_container_width=True)
            
            with col2:
                # 売上グラフ
                fig_revenue = create_pie_chart(
                    product_df['product'].tolist(),
                    product_df['total_revenue'].tolist(),
                    "商材別売上分布"
                )
                st.plotly_chart(fig_revenue, use_container_width=True)
                
                # 承認率グラフ
                fig_approval_rate = go.Figure()
                fig_approval_rate.add_trace(go.Bar(
                    x=product_df['product'],
                    y=product_df['approval_rate'],
                    marker_color='lightblue',
                    hovertemplate='<b>%{x}</b><br>承認率: %{y:.1f}%<extra></extra>'
                ))
                fig_approval_rate.update_layout(
                    title="商材別承認率",
                    xaxis_title="商材",
                    yaxis_title="承認率(%)",
                    yaxis=dict(range=[0, 100])
                )
                st.plotly_chart(fig_approval_rate, use_container_width=True)
            
            # 商材別サマリーテーブル
            st.markdown("#### 商材別サマリーテーブル")
            display_table = product_df.copy()
            
            # 数値フォーマット
            display_table['total_deals'] = display_table['total_deals'].apply(lambda x: f"{x:,}")
            display_table['approved_deals'] = display_table['approved_deals'].apply(lambda x: f"{x:,}")
            display_table['total_revenue'] = display_table['total_revenue'].apply(lambda x: f"¥{x:,}")
            display_table['total_potential_revenue'] = display_table['total_potential_revenue'].apply(lambda x: f"¥{x:,}")
            display_table['approval_rate'] = display_table['approval_rate'].apply(lambda x: f"{x:.1f}%")
            
            # 列名を日本語に変更
            display_table = display_table.rename(columns={
                'product': '商材',
                'total_deals': '総商談数',
                'approved_deals': '承認数',
                'total_revenue': '売上',
                'total_potential_revenue': '潜在売上',
                'approval_rate': '承認率'
            })
            
            st.dataframe(display_table, use_container_width=True)
        else:
            st.info("商材別データがありません")
    else:
        st.info("商材別データがありません")

def render_detail_data_tab(df_basic, selected_month):
    """詳細データタブをレンダリング"""
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