"""ランキング表示ロジック"""
import streamlit as st
import pandas as pd

def display_ranking_with_ties(df, ranking_column, display_columns, max_rank=10, 
                             branch_colors=None, show_branch=True, format_func=None,
                             format_as_currency=False, format_as_percent=False):
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
        format_as_currency: 通貨フォーマットで表示するか
        format_as_percent: パーセントフォーマットで表示するか
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
            elif format_as_currency:
                formatted_value = f"¥{value:,}"
            elif format_as_percent:
                formatted_value = f"{value:.1f}%"
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

def create_ranking_dataframe(df, ranking_column, display_columns, max_rank=10):
    """
    ランキングデータフレームを作成
    
    Args:
        df: DataFrame
        ranking_column: ランキング基準の列名
        display_columns: 表示する列のリスト
        max_rank: 表示する最大順位
        
    Returns:
        DataFrame: ランキングデータフレーム
    """
    # 同順位を反映した順位を計算
    df_sorted = df.copy()
    df_sorted['順位'] = df_sorted[ranking_column].rank(method='min', ascending=False).astype(int)
    df_sorted = df_sorted.sort_values([ranking_column, 'staff_name'], ascending=[False, True])
    
    # 指定順位以内のデータのみ取得
    df_display = df_sorted[df_sorted['順位'] <= max_rank]
    
    # 表示列のみを選択
    result_columns = ['順位', 'staff_name'] + display_columns
    if 'branch' in df_display.columns:
        result_columns.insert(2, 'branch')
    
    return df_display[result_columns]

def format_ranking_table(df, currency_columns=None, percentage_columns=None, rate_columns=None):
    """
    ランキングテーブルのフォーマットを適用
    
    Args:
        df: DataFrame
        currency_columns: 通貨列のリスト
        percentage_columns: パーセンテージ列のリスト
        rate_columns: 比率列のリスト
        
    Returns:
        DataFrame: フォーマット済みのDataFrame
    """
    formatted_df = df.copy()
    
    if currency_columns:
        for col in currency_columns:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"¥{x:,}" if pd.notna(x) else "")
    
    if percentage_columns:
        for col in percentage_columns:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
    
    if rate_columns:
        for col in rate_columns:
            if col in formatted_df.columns:
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "")
    
    return formatted_df 