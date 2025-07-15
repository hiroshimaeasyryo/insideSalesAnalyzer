"""月次詳細データページ"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_processor import (
    load_analysis_data_from_json, 
    extract_daily_activity_from_staff,
    get_prev_months,
    load_multi_month_data
)
from components.charts import create_funnel_chart, create_pie_chart, create_trend_chart, create_monthly_histogram
from components.rankings import display_ranking_with_ties
from utils.config import BRANCH_COLORS, CARD_STYLE

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
            render_branch_analysis_tab(df_basic, summary_data)
        
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

def render_branch_analysis_tab(df_basic, summary_data):
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
        st.info("単位あたり分析（実装予定）")
    
    with subtab3:
        st.info("実数3ヶ月比較（実装予定）")
    
    with subtab4:
        st.info("単位あたり3ヶ月比較（実装予定）")

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
            st.markdown("##### 💼 TAAAN商談数ランキング")
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
            
            # 5. 承認数ランキング
            st.markdown("##### ✅ 承認数ランキング")
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
            
            # 6. 売上ランキング
            st.markdown("##### 💰 売上ランキング")
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
        st.write("各支部内でのランキングです。")
        
        # 支部選択
        branches = staff_summary['branch'].unique()
        selected_branch = st.selectbox("支部を選択", branches)
        
        if selected_branch:
            branch_staff = staff_summary[staff_summary['branch'] == selected_branch]
            
            if not branch_staff.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"##### 🏆 {selected_branch} - 架電数ランキング")
                    display_ranking_with_ties(
                        branch_staff, 
                        'total_calls', 
                        ['total_calls'], 
                        max_rank=10, 
                        branch_colors=BRANCH_COLORS
                    )
                    
                    st.markdown(f"##### 🎯 {selected_branch} - アポ獲得数ランキング")
                    display_ranking_with_ties(
                        branch_staff, 
                        'appointments', 
                        ['appointments'], 
                        max_rank=10, 
                        branch_colors=BRANCH_COLORS
                    )
                
                with col2:
                    st.markdown(f"##### 💼 {selected_branch} - TAAAN商談数ランキング")
                    branch_taaan = branch_staff[branch_staff['taaan_deals'] > 0]
                    if not branch_taaan.empty:
                        display_ranking_with_ties(
                            branch_taaan, 
                            'taaan_deals', 
                            ['taaan_deals'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS
                        )
                    else:
                        st.info(f"{selected_branch}にTAAANデータがありません")
                    
                    st.markdown(f"##### 💰 {selected_branch} - 売上ランキング")
                    branch_revenue = branch_staff[branch_staff['total_revenue'] > 0]
                    if not branch_revenue.empty:
                        display_ranking_with_ties(
                            branch_revenue, 
                            'total_revenue', 
                            ['total_revenue'], 
                            max_rank=10, 
                            branch_colors=BRANCH_COLORS,
                            format_as_currency=True
                        )
                    else:
                        st.info(f"{selected_branch}に売上データがありません")
            else:
                st.warning(f"{selected_branch}にスタッフデータがありません")
    
    with staff_subtab3:
        st.subheader("⚡ 効率性ランキング")
        st.write("変換率や効率性の指標でのランキングです。")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # コネクト率ランキング
            st.markdown("##### 📞 コネクト率ランキング")
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
            st.markdown("##### ✅ 承認率ランキング")
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
            st.markdown("##### 🎯 アポ率ランキング")
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
    
    with staff_subtab4:
        st.info("月別推移(3ヶ月)（実装予定）")

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