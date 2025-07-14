"""
共通ヘルパー関数モジュール
日付処理、データ検証、ユーティリティ関数
"""

import pandas as pd
from datetime import datetime, timedelta
import re

def get_prev_months(month_str, n=3):
    """指定月から過去nヶ月の月リストを取得"""
    try:
        if isinstance(month_str, str) and len(month_str) == 7:
            year, month = month_str.split('-')
            current_date = datetime(int(year), int(month), 1)
            
            months = []
            for i in range(n):
                prev_date = current_date - timedelta(days=32)  # 前月に移動
                prev_date = prev_date.replace(day=1)  # 月初に調整
                months.append(prev_date.strftime('%Y-%m'))
                current_date = prev_date
            
            return months[::-1]  # 古い順に並べ替え
        else:
            return []
    except (ValueError, TypeError):
        return []

def validate_month_format(month_str):
    """月次フォーマット（YYYY-MM）の検証"""
    if not isinstance(month_str, str):
        return False
    pattern = r'^\d{4}-\d{2}$'
    return bool(re.match(pattern, month_str))

def extract_month_from_filename(filename):
    """ファイル名から月次情報を抽出"""
    if not isinstance(filename, str):
        return None
    
    # パターン: 基本分析_2024-09.json
    pattern = r'_(\d{4}-\d{2})\.json$'
    match = re.search(pattern, filename)
    if match:
        return match.group(1)
    return None

def calculate_working_days(staff_name, basic_data):
    """スタッフの稼働日数を計算"""
    try:
        if staff_name not in basic_data:
            return 0
        
        staff_data = basic_data[staff_name]
        daily_activity = staff_data.get('daily_activity', [])
        
        # 架電数が0より大きい日を稼働日としてカウント
        working_days = 0
        for activity in daily_activity:
            main_product = activity.get('main_product', {})
            sub_products = activity.get('sub_products', [])
            
            # メイン商材の架電数チェック
            if main_product.get('call_count', 0) > 0:
                working_days += 1
                continue
            
            # サブ商材の架電数チェック
            for sub_product in sub_products:
                if sub_product.get('call_count', 0) > 0:
                    working_days += 1
                    break
        
        return working_days
    except Exception:
        return 0

def convert_utc_to_jst(date_str):
    """UTC日付をJSTに変換"""
    try:
        if not date_str:
            return None
        
        # UTC→JST変換
        date_jst = pd.to_datetime(date_str, utc=True).tz_convert('Asia/Tokyo')
        return str(date_jst.date())
    except Exception:
        return date_str

def safe_divide(numerator, denominator, default=0):
    """安全な除算（ゼロ除算エラーを回避）"""
    try:
        if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
            return default
        return numerator / denominator
    except (ValueError, TypeError, ZeroDivisionError):
        return default

def validate_json_data(data):
    """JSONデータの基本検証"""
    if not isinstance(data, dict):
        return False
    
    # 必須キーのチェック
    required_keys = ['staff_data', 'month']
    for key in required_keys:
        if key not in data:
            return False
    
    return True

def get_latest_month(available_months):
    """利用可能な月から最新月を取得"""
    if not available_months:
        return None
    
    try:
        # YYYY-MM形式でソートして最新月を取得
        sorted_months = sorted(available_months, reverse=True)
        return sorted_months[0]
    except Exception:
        return None

def format_duration_hours(hours):
    """時間を時間:分形式でフォーマット"""
    try:
        if pd.isna(hours) or hours is None:
            return "0:00"
        
        hours_int = int(hours)
        minutes = int((hours - hours_int) * 60)
        return f"{hours_int}:{minutes:02d}"
    except (ValueError, TypeError):
        return "0:00"

def calculate_percentage_change(current, previous):
    """前月比の変化率を計算"""
    try:
        if pd.isna(current) or pd.isna(previous) or previous == 0:
            return 0
        
        change = ((current - previous) / previous) * 100
        return round(change, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0 