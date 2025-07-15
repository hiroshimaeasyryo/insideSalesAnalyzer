"""
リファクタリング後のメインアプリケーションファイル
分離された機能をインポートして使用
"""
import streamlit as st

# 設定とページ設定
from utils.config import PAGE_CONFIG
from auth.authentication import handle_authentication, display_auth_sidebar, show_auth_error
from components.file_upload import render_upload_section, render_analysis_selection, render_usage_guide
from pages.monthly_detail import render_monthly_detail_page
from utils.data_processor import load_analysis_data_from_json, load_retention_data_from_json
import pandas as pd
import plotly.graph_objects as go

# ページ設定
st.set_page_config(**PAGE_CONFIG)

def render_basic_analysis_page(json_data, selected_month):
    """月次サマリー分析ページをレンダリング"""
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
            else:
                st.warning("⚠️ コンバージョンデータが見つかりませんでした")
        else:
            st.error("❌ 月次分析データの読み込みに失敗しました")

def render_retention_analysis_page(json_data, selected_month):
    """定着率分析ページをレンダリング"""
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
        else:
            st.warning("⚠️ 定着率データが見つかりませんでした")

def main():
    """メインアプリケーション"""
    # 認証処理
    authenticator, authentication_status, name, username = handle_authentication()
    
    # 認証状態に応じた表示
    if authentication_status == False:
        show_auth_error(authentication_status)
    elif authentication_status == None:
        show_auth_error(authentication_status)
    elif authentication_status:
        # 認証後のメインアプリ
        st.success(f"ようこそ {name} さん")
        
        # サイドバーに認証情報表示
        with st.sidebar:
            display_auth_sidebar(authenticator, name)
            st.divider()
            
            # ファイルアップロードセクション
            render_upload_section()
            
            # 分析選択セクション
            selected_analysis, selected_month = render_analysis_selection()
        
        # メインコンテンツエリア
        if 'json_data' in st.session_state and st.session_state['json_data']:
            json_data = st.session_state['json_data']
            
            if selected_analysis == "basic_analysis":
                render_basic_analysis_page(json_data, selected_month)
            elif selected_analysis == "retention_analysis":
                render_retention_analysis_page(json_data, selected_month)
            elif selected_analysis == "monthly_detail":
                render_monthly_detail_page(json_data, selected_month)
        else:
            render_usage_guide()

# フッター
    st.divider()
    st.caption("© 2025 架電ダッシュボード - Streamlit版（リファクタリング済み）")

if __name__ == "__main__":
    main() 