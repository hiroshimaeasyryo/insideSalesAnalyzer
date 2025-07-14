"""
フォーマット機能モジュール
数値、日付、パーセンテージなどの統一フォーマット機能
"""

import pandas as pd
from datetime import datetime

def format_number(value, decimal_places=0):
    """数値をフォーマット（カンマ区切り）"""
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        if decimal_places == 0:
            return f"{int(value):,}"
        else:
            return f"{float(value):,.{decimal_places}f}"
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(value, decimal_places=1):
    """パーセンテージをフォーマット"""
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.{decimal_places}f}%"
    except (ValueError, TypeError):
        return "N/A"

def format_currency(value, currency="¥"):
    """通貨をフォーマット"""
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        return f"{currency}{int(value):,}"
    except (ValueError, TypeError):
        return "N/A"

def format_time(hours):
    """時間をフォーマット（時間:分）"""
    if pd.isna(hours) or hours is None:
        return "N/A"
    try:
        hours_int = int(hours)
        minutes = int((hours - hours_int) * 60)
        return f"{hours_int}:{minutes:02d}"
    except (ValueError, TypeError):
        return "N/A"

def format_date(date_str, input_format="%Y-%m-%d", output_format="%Y年%m月%d日"):
    """日付をフォーマット"""
    if pd.isna(date_str) or date_str is None:
        return "N/A"
    try:
        if isinstance(date_str, str):
            date_obj = datetime.strptime(date_str, input_format)
        else:
            date_obj = pd.to_datetime(date_str)
        return date_obj.strftime(output_format)
    except (ValueError, TypeError):
        return "N/A"

def format_month(month_str):
    """月次データをフォーマット（YYYY年MM月）"""
    if pd.isna(month_str) or month_str is None:
        return "N/A"
    try:
        if isinstance(month_str, str) and len(month_str) == 7:
            year, month = month_str.split('-')
            return f"{year}年{int(month):02d}月"
        else:
            return str(month_str)
    except (ValueError, TypeError):
        return "N/A"

def format_cross_table_value(value):
    """クロス集計表の値をフォーマット"""
    if pd.isna(value) or value is None:
        return "-"
    try:
        if isinstance(value, (int, float)):
            if value == 0:
                return "-"
            elif value < 1:
                return f"{value:.3f}"
            else:
                return f"{value:.1f}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return "-"

def format_efficiency(calls, hours):
    """効率（架電数/時間）をフォーマット"""
    if pd.isna(calls) or pd.isna(hours) or hours == 0:
        return "N/A"
    try:
        efficiency = calls / hours
        return f"{efficiency:.1f}/h"
    except (ValueError, TypeError, ZeroDivisionError):
        return "N/A"

def format_conversion_rate(appointments, calls):
    """コンバージョン率をフォーマット"""
    if pd.isna(appointments) or pd.isna(calls) or calls == 0:
        return "N/A"
    try:
        rate = (appointments / calls) * 100
        return f"{rate:.1f}%"
    except (ValueError, TypeError, ZeroDivisionError):
        return "N/A" 