"""フォーマット処理ユーティリティ"""
import pandas as pd

def format_currency(value):
    """通貨フォーマット"""
    if pd.isna(value):
        return ""
    return f"¥{value:,}"

def format_percentage(value):
    """パーセンテージフォーマット"""
    if pd.isna(value):
        return ""
    return f"{value:.1f}%"

def format_number(value, decimal_places=0):
    """数値フォーマット"""
    if pd.isna(value):
        return ""
    if decimal_places == 0:
        return f"{value:,.0f}"
    else:
        return f"{value:,.{decimal_places}f}"

def format_hours(value):
    """時間フォーマット"""
    if pd.isna(value):
        return ""
    return f"{value:.1f}時間"

def format_rate(value):
    """比率フォーマット（小数点1桁）"""
    if pd.isna(value):
        return ""
    return f"{value:.1f}"

def format_metric_value(column_name, value):
    """指標に応じた値のフォーマット"""
    if pd.isna(value):
        return ""
    
    # 通貨関連
    if 'revenue' in column_name.lower():
        return format_currency(value)
    
    # パーセンテージ関連
    if 'rate' in column_name.lower() or 'percent' in column_name.lower():
        return format_percentage(value)
    
    # 時間関連
    if 'hour' in column_name.lower() and 'per_hour' not in column_name.lower():
        return format_hours(value)
    
    # 効率性指標（時間あたり、日あたり）
    if 'per_hour' in column_name.lower():
        return f"{value:.1f}/時間"
    
    if 'per_day' in column_name.lower() or 'per_working_day' in column_name.lower():
        return f"{value:.1f}/日"
    
    # 日数
    if 'days' in column_name.lower():
        return f"{value:.0f}日"
    
    # その他の数値（件数など）
    return f"{value:,.0f}件" if value >= 1000 or value == int(value) else f"{value:.1f}"

def create_comparison_table(data_dict, value_column, staff_filter=None):
    """
    月別比較テーブルを作成
    
    Args:
        data_dict: 月別データ辞書
        value_column: 比較する値の列名
        staff_filter: スタッフフィルター
        
    Returns:
        DataFrame: 比較テーブル
    """
    comparison_data = []
    months = sorted(data_dict.keys())
    
    # 全スタッフのリストを取得
    all_staff = set()
    for month_df in data_dict.values():
        if staff_filter:
            month_df = month_df[month_df['staff_name'].isin(staff_filter)]
        all_staff.update(month_df['staff_name'].tolist())
    
    for staff_name in sorted(all_staff):
        row_data = {'スタッフ名': staff_name}
        
        # 支部情報を取得
        staff_branch = '未設定'
        for month_df in data_dict.values():
            staff_row = month_df[month_df['staff_name'] == staff_name]
            if not staff_row.empty:
                staff_branch = staff_row.iloc[0]['branch']
                break
        row_data['支部'] = staff_branch
        
        # 各月のデータを追加
        for month in months:
            if month in data_dict:
                month_df = data_dict[month]
                staff_row = month_df[month_df['staff_name'] == staff_name]
                if not staff_row.empty:
                    value = staff_row.iloc[0][value_column]
                    formatted_value = format_metric_value(value_column, value)
                    row_data[month] = formatted_value
                else:
                    row_data[month] = "-"
            else:
                row_data[month] = "-"
        
        comparison_data.append(row_data)
    
    return pd.DataFrame(comparison_data)

def apply_branch_styling(dataframe, branch_colors):
    """
    支部別色分けスタイリングを適用
    
    Args:
        dataframe: DataFrame
        branch_colors: 支部色設定辞書
        
    Returns:
        Styled DataFrame
    """
    def highlight_branch(row):
        branch = row['支部']
        if branch in branch_colors:
            color = branch_colors[branch]
            return [f'background-color: {color}20; border-left: 3px solid {color}'] * len(row)
        else:
            return [f'background-color: #f8f9fa; border-left: 3px solid #dee2e6'] * len(row)
    
    return dataframe.style.apply(highlight_branch, axis=1) 