"""データ処理・抽出ロジック"""
import pandas as pd
import json
import tempfile
import zipfile
import os
from datetime import datetime, timedelta
import streamlit as st

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