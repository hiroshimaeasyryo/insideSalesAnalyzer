"""商材別分析モジュール"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_processor import (
    extract_taaan_product_data,
    generate_branch_product_cross_data,
    format_number_value,
    load_product_3month_comparison_data,
    get_prev_months,
    aggregate_product_data_from_basic
)
from components.charts import create_bar_chart, create_line_chart


def render_product_analysis_tab(df_basic, summary_data, json_data, selected_month):
    """商材別分析タブをレンダリング"""
    st.subheader("商材別分析")
    
    # 商材別分析のサブタブ
    subtab1, subtab2, subtab3, subtab4 = st.tabs([
        "📊 商材別パフォーマンス", 
        "🔗 支部×商材クロス分析", 
        "📈 商材別3ヶ月比較", 
        "📋 商材別詳細"
    ])
    
    with subtab1:
        render_product_performance_subtab(df_basic, summary_data)
    
    with subtab2:
        render_branch_product_cross_subtab(summary_data)
    
    with subtab3:
        render_product_3month_comparison_subtab(json_data, selected_month)
    
    with subtab4:
        render_product_detail_subtab(df_basic)


def render_product_performance_subtab(df_basic, summary_data):
    """商材別パフォーマンスサブタブをレンダリング"""
    st.subheader("商材別パフォーマンス")
    
    # TAAANデータから商材別集計
    taaan_product_summary = extract_taaan_product_data(summary_data)
    
    if not taaan_product_summary.empty:
        # 商材別グラフ（TAAANデータ）
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig_product_taaan = create_bar_chart(
                taaan_product_summary,
                x='product',
                y='taaan_deals',
                title="商材別TAAAN商談数（TAAANデータ）",
                color_discrete_sequence=['#7b1fa2']  # 紫
            )
            st.plotly_chart(fig_product_taaan, use_container_width=True)
        
        with col2:
            fig_product_approved = create_bar_chart(
                taaan_product_summary,
                x='product',
                y='approved_deals',
                title="商材別承認数（TAAANデータ）",
                color_discrete_sequence=['#c62828']  # 赤
            )
            st.plotly_chart(fig_product_approved, use_container_width=True)
        
        with col3:
            fig_product_revenue = create_bar_chart(
                taaan_product_summary,
                x='product',
                y='total_revenue',
                title="商材別確定売上（TAAANデータ）",
                color_discrete_sequence=['#00695c']  # ダークグリーン
            )
            st.plotly_chart(fig_product_revenue, use_container_width=True)
        
        # 商材別サマリーテーブル
        st.markdown("#### 商材別サマリーテーブル")
        
        display_table = taaan_product_summary.copy()
        
        # 数値フォーマット
        display_table['taaan_deals'] = display_table['taaan_deals'].apply(lambda x: format_number_value(x))
        display_table['approved_deals'] = display_table['approved_deals'].apply(lambda x: format_number_value(x))
        display_table['total_revenue'] = display_table['total_revenue'].apply(lambda x: format_number_value(x, "revenue"))
        display_table['total_potential_revenue'] = display_table['total_potential_revenue'].apply(lambda x: format_number_value(x, "revenue"))
        display_table['approval_rate'] = display_table['approval_rate'].apply(lambda x: format_number_value(x, "percentage"))
        
        # 列名を日本語に変更
        display_table = display_table.rename(columns={
            'product': '商材',
            'taaan_deals': 'TAAAN商談数',
            'approved_deals': '承認数',
            'total_revenue': '確定売上',
            'total_potential_revenue': '潜在売上',
            'approval_rate': '承認率'
        })
        
        st.dataframe(display_table, use_container_width=True)
    else:
        st.warning("⚠️ **TAAANデータが見つかりません**: 商材別分析ではTAAAN関連の指標を表示できません")


def render_branch_product_cross_subtab(summary_data):
    """支部×商材クロス分析サブタブをレンダリング"""
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
            # 指標に応じたデータを選択
            metric_mapping = {
                "TAAAN商談数": "taaan_deals",
                "承認数": "approved_deals",
                "確定売上": "total_revenue"
            }
            
            metric_key = metric_mapping[analysis_metric]
            cross_analysis = generate_branch_product_cross_data(summary_data, metric_key)
            
            if not cross_analysis.empty:
                # ヒートマップ
                z = cross_analysis.iloc[:-1, :-1].values  # 数値（合計行・列除く）
                x_labels = cross_analysis.columns[:-1].tolist()  # 商材名（合計列除く）
                y_labels = cross_analysis.index[:-1].tolist()   # 支部名（合計行除く）
                
                # ホバー用テキスト作成
                z_text = cross_analysis.iloc[:-1, :-1].copy()
                for col in z_text.columns:
                    z_text[col] = z_text[col].apply(
                        lambda v: format_number_value(v, "revenue" if analysis_metric == "確定売上" else "normal")
                    )
                text = z_text.values
                
                # ヒートマップを直接作成
                fig_cross = go.Figure(
                    data=go.Heatmap(
                        z=z,
                        x=x_labels,
                        y=y_labels,
                        text=text,
                        texttemplate="%{text}",
                        colorscale="Blues",
                        colorbar=dict(title=analysis_metric),
                        hovertemplate="<b>支部</b>: %{y}<br><b>商材</b>: %{x}<br><b>" + analysis_metric + "</b>: %{z:,.0f}<extra></extra>"
                    )
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
                formatted_cross_analysis = cross_analysis.copy()
                for col in formatted_cross_analysis.columns:
                    formatted_cross_analysis[col] = formatted_cross_analysis[col].apply(
                        lambda x: format_number_value(x, "revenue" if analysis_metric == "確定売上" else "normal")
                    )
                
                st.dataframe(formatted_cross_analysis, use_container_width=True)
                
                # 統計情報（カードスタイル）
                st.subheader("📊 統計情報")
                
                # カードスタイルのCSS
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
                    total_display = format_number_value(total_value, "revenue" if analysis_metric == "確定売上" else "normal")
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">総{analysis_metric}</div>
                        <div class="metric-value">{total_display}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    max_branch = cross_analysis.iloc[:-1, :-1].sum(axis=1).idxmax()
                    max_branch_value = cross_analysis.loc[max_branch, '合計']
                    branch_display = format_number_value(max_branch_value, "revenue" if analysis_metric == "確定売上" else "normal")
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">最高{analysis_metric}支部</div>
                        <div class="metric-value">{max_branch}<br><small>{branch_display}</small></div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    max_product = cross_analysis.iloc[:-1, :-1].sum().idxmax()
                    max_product_value = cross_analysis.loc['合計', max_product]
                    product_display = format_number_value(max_product_value, "revenue" if analysis_metric == "確定売上" else "normal")
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-title">最高{analysis_metric}商材</div>
                        <div class="metric-value">{max_product}<br><small>{product_display}</small></div>
                    </div>
                    """, unsafe_allow_html=True)
                
            else:
                st.warning(f"{analysis_metric}の支部×商材クロス分析データが見つかりません。")
                
        except Exception as e:
            st.error(f"支部×商材クロス分析の実行中にエラーが発生しました: {str(e)}")
            st.info("💡 データ構造の確認が必要です。")


def render_product_3month_comparison_subtab(json_data, selected_month):
    """商材別3ヶ月比較サブタブをレンダリング"""
    st.subheader("商材別3ヶ月比較")
    
    # 過去3ヶ月の月リスト作成
    target_months = get_prev_months(selected_month, 3)
    
    # 過去3ヶ月のTAAANデータを読み込み
    all_taaan_data = load_product_3month_comparison_data(json_data, selected_month)
    
    # デバッグ情報
    st.info(f"🔍 **対象月**: {', '.join(target_months)}")
    
    if all_taaan_data.empty:
        st.warning("過去3ヶ月のTAAANデータが見つかりません。")
        return
    
    st.markdown("### 💼 TAAANデータ（TAAAN商談数、承認数、確定売上）の3ヶ月推移")
    st.info("📊 **データソース**: この分析ではTAAANシステムからの商談データ（total_deals、total_approved、total_revenue）のみを使用しています。日報データ（total_calls、total_hours、total_appointments）は含まれていません。")
    
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
        fig_taaan_trend = create_line_chart(
            filtered_taaan_data,
            x='month',
            y=taaan_metric_col_mapping[taaan_comparison_metric],
            color='product',
            title=f"TAAANデータ: 商材別{taaan_comparison_metric}の3ヶ月推移",
            markers=True
        )
        
        # ホバー時の情報を日本語に設定
        fig_taaan_trend.update_traces(
            hovertemplate="<b>月</b>: %{x}<br><b>商材</b>: %{fullData.name}<br><b>" + taaan_comparison_metric + "</b>: %{y:,.0f}<extra></extra>"
        )
        
        # X軸を月次ベースに設定
        fig_taaan_trend.update_layout(
            xaxis=dict(
                type='category',
                categoryorder='category ascending'
            )
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
        
        # フォーマットされたテーブルを表示
        formatted_pivot = pivot_taaan_comparison.copy()
        for col in formatted_pivot.columns:
            if col != '増減率(%)':
                formatted_pivot[col] = formatted_pivot[col].apply(
                    lambda x: format_number_value(x, "revenue" if taaan_comparison_metric == "確定売上" else "normal")
                )
            else:
                formatted_pivot[col] = formatted_pivot[col].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else ""
                )
        
        st.dataframe(formatted_pivot, use_container_width=True)
    else:
        st.info("比較したい商材を選択してください。")


def render_product_detail_subtab(df_basic):
    """商材別詳細サブタブをレンダリング"""
    st.subheader("商材別詳細")
    
    if df_basic.empty:
        st.warning("⚠️ 日報データが見つかりません")
        return
    
    # 商材別集計
    product_summary = aggregate_product_data_from_basic(df_basic)
    
    if product_summary.empty:
        st.warning("⚠️ 商材別データが見つかりません")
        return
    
    # 商材別グラフ
    fig_product = go.Figure()
    
    fig_product.add_trace(go.Bar(
        x=product_summary['product'],
        y=product_summary['total_calls'],
        name='架電数',
        marker_color='blue'
    ))
    
    fig_product.add_trace(go.Bar(
        x=product_summary['product'],
        y=product_summary['appointments'],
        name='アポ獲得数',
        marker_color='red'
    ))
    
    fig_product.update_layout(
        title="商材別実績",
        barmode='group',
        height=400,
        yaxis=dict(tickformat=',', separatethousands=True)
    )
    
    st.plotly_chart(fig_product, use_container_width=True)
    
    # 商材別詳細テーブル
    st.subheader("商材別詳細テーブル")
    
    display_table = product_summary.copy()
    
    # 数値フォーマット
    display_table['total_calls'] = display_table['total_calls'].apply(lambda x: format_number_value(x))
    display_table['charge_connected'] = display_table['charge_connected'].apply(lambda x: format_number_value(x))
    display_table['appointments'] = display_table['appointments'].apply(lambda x: format_number_value(x))
    display_table['connection_rate'] = display_table['connection_rate'].apply(lambda x: format_number_value(x, "percentage"))
    display_table['appointment_rate'] = display_table['appointment_rate'].apply(lambda x: format_number_value(x, "percentage"))
    
    # 列名を日本語に変更
    display_table = display_table.rename(columns={
        'product': '商材名',
        'total_calls': '架電数',
        'charge_connected': '担当コネクト数',
        'appointments': 'アポ獲得数',
        'connection_rate': '架電効率',
        'appointment_rate': '成約率'
    })
    
    st.dataframe(display_table, use_container_width=True) 