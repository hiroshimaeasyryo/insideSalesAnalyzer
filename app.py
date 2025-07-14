#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flaskアプリケーション for インタラクティブダッシュボード
"""

from flask import Flask, render_template, jsonify, request, session
from pathlib import Path
import json
import pandas as pd
import datetime as dt
from analysis_dashboard import extract_monthly_data, FILES
import zipfile
import tempfile
import os
import io

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # セッション管理用

# グローバル変数としてデータを保持
global_data = None
base_data = None

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
                                print(f"JSONファイル読み込みエラー {file}: {e}")
                
                return json_files
    except Exception as e:
        print(f"Zipファイル処理エラー: {e}")
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

def load_data_from_json(json_data, target_month):
    """JSONデータからデータを読み込んでグローバル変数に保存"""
    global global_data, base_data
    
    try:
        basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, target_month)
        
        dfs = {}
        if basic_data:
            dfs['basic'] = extract_monthly_data(basic_data)
        if detail_data:
            dfs['detail'] = extract_monthly_data(detail_data)
        if summary_data:
            dfs['monthly'] = extract_monthly_data(summary_data)
        
        # 空のDataFrameを除外
        dfs = {k: v for k, v in dfs.items() if not v.empty}
        
        if not dfs:
            print("警告: 有効なデータが見つかりません")
            return False
            
    except Exception as e:
        print(f"データ読み込みエラー: {e}")
        return False
    
    base_data = pd.concat(dfs.values(), ignore_index=True)
    
    # 前処理
    base_data['date'] = pd.to_datetime(base_data['date'], errors='coerce')
    base_data['month'] = base_data['date'].dt.to_period('M').astype(str)
    base_data['join_date'] = pd.to_datetime(base_data['join_date'], errors='coerce')
    
    # タイムゾーン情報を統一
    base_data['date'] = base_data['date'].dt.tz_localize(None)
    base_data['join_date'] = base_data['join_date'].dt.tz_localize(None)
    
    base_data['tenure_months'] = ((base_data['date'] - base_data['join_date']) / pd.Timedelta(days=30)).round()
    
    def bucket(m):
        if pd.isna(m):
            return "Unknown"
        if m < 3:
            return "<3mo"
        if m < 6:
            return "3–6mo"
        if m < 12:
            return "6–12mo"
        return ">=12mo"
    
    base_data['tenure_grp'] = base_data['tenure_months'].apply(bucket)
    
    # 月次データ
    monthly = (
        base_data.groupby('month')
            .agg(calls=('calls','sum'),
                 appointments=('appointments','sum'),
                 hours=('call_hours','sum'))
            .assign(eff=lambda x: x.calls / x.hours,
                    conv=lambda x: x.appointments / x.calls * 100)
            .reset_index()
    )
    
    # 支店 × 月
    branch_month = (
        base_data.groupby(['month','branch'])
            .agg(calls=('calls','sum'),
                 hours=('call_hours','sum'))
            .assign(eff=lambda x: x.calls / x.hours)
            .reset_index()
    )
    
    # 在籍期間別パフォーマンス
    tenure_perf = (
        base_data.groupby('tenure_grp')
            .agg(calls=('calls','sum'),
                 hours=('call_hours','sum'),
                 appointments=('appointments','sum'))
            .assign(eff=lambda x: x.calls / x.hours,
                    conv=lambda x: x.appointments / x.calls * 100)
            .reset_index()
    )
    
    # サマリー統計
    summary = {
        'total_calls': int(base_data['calls'].sum()),
        'total_hours': int(base_data['call_hours'].sum()),
        'total_appointments': int(base_data['appointments'].sum()),
        'avg_efficiency': float(base_data['calls'].sum() / base_data['call_hours'].sum()) if base_data['call_hours'].sum() > 0 else 0
    }
    
    global_data = {
        'monthly': monthly.to_dict(orient="records"),
        'branch_trend': branch_month.to_dict(orient="records"),
        'tenure_perf': tenure_perf.to_dict(orient="records"),
        'summary': summary,
        'available_months': sorted(monthly['month'].unique(), reverse=True)[:6]
    }
    
    return True

@app.route('/')
def dashboard():
    """メインダッシュボードページ"""
    return render_template('upload_template.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Zipファイルアップロード処理"""
    if 'file' not in request.files:
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'ファイルが選択されていません'}), 400
    
    if not file.filename.endswith('.zip'):
        return jsonify({'error': 'Zipファイルをアップロードしてください'}), 400
    
    try:
        # Zipファイルを処理
        json_data = extract_zip_data(file)
        
        if not json_data:
            return jsonify({'error': 'JSONファイルが見つかりませんでした'}), 400
        
        # 利用可能な月を取得
        available_months = get_available_months_from_data(json_data)
        
        if not available_months:
            return jsonify({'error': '有効な月データが見つかりませんでした'}), 400
        
        # セッションにデータを保存
        session['json_data'] = json_data
        session['available_months'] = available_months
        session['uploaded_file_name'] = file.filename
        
        # 最新月のデータを読み込み
        target_month = available_months[0]
        if load_data_from_json(json_data, target_month):
            return jsonify({
                'success': True,
                'message': f'{len(json_data)}個のJSONファイルを読み込みました',
                'available_months': available_months,
                'selected_month': target_month
            })
        else:
            return jsonify({'error': 'データの読み込みに失敗しました'}), 500
            
    except Exception as e:
        return jsonify({'error': f'ファイル処理エラー: {str(e)}'}), 500

@app.route('/dashboard')
def main_dashboard():
    """メインダッシュボードページ（データ読み込み後）"""
    if global_data is None:
        return render_template('upload_template.html')
    
    selected_month = global_data['available_months'][0] if global_data['available_months'] else None
    
    # 選択された月のデータを取得
    month_data = get_month_data(selected_month)
    
    return render_template('dashboard_template.html',
                         generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                         monthly=global_data['monthly'],
                         branch_trend=global_data['branch_trend'],
                         branch_latest=month_data['branch_latest'],
                         staff_eff=month_data['staff_eff'],
                         staff_conv=month_data['staff_conv'],
                         tenure_perf=global_data['tenure_perf'],
                         summary=global_data['summary'],
                         available_months=global_data['available_months'],
                         selected_month=selected_month)

@app.route('/api/month_data/<month>')
def api_month_data(month):
    """指定された月のデータを返すAPIエンドポイント"""
    if global_data is None:
        return jsonify({'error': 'データが読み込まれていません'}), 500
    
    month_data = get_month_data(month)
    return jsonify(month_data)

def get_month_data(month):
    """指定された月のデータを取得"""
    if month is None or base_data is None:
        return {
            'branch_latest': [],
            'staff_eff': [],
            'staff_conv': []
        }
    
    month_df = base_data[base_data['month'] == month]
    
    # 支店別データ
    branch_latest = (
        month_df.groupby('branch')
            .agg(calls=('calls','sum'),
                 hours=('call_hours','sum'),
                 appointments=('appointments','sum'))
            .assign(eff=lambda x: x.calls / x.hours,
                    conv=lambda x: x.appointments / x.calls * 100)
            .sort_values('eff', ascending=False)
            .reset_index()
    )
    
    # スタッフ効率ランキング
    staff_eff = (
        month_df.groupby('staff')
            .agg(calls=('calls','sum'),
                 hours=('call_hours','sum'))
            .assign(eff=lambda x: x.calls / x.hours)
            .sort_values('eff', ascending=False)
            .head(5)
            .reset_index()
    )
    
    # スタッフ成約率ランキング
    staff_conv = (
        month_df.groupby('staff')
            .agg(calls=('calls','sum'),
                 appointments=('appointments','sum'))
            .assign(conv=lambda x: x.appointments / x.calls * 100)
            .sort_values('conv', ascending=False)
            .head(5)
            .reset_index()
    )
    
    return {
        'branch_latest': branch_latest.to_dict(orient="records"),
        'staff_eff': staff_eff.to_dict(orient="records"),
        'staff_conv': staff_conv.to_dict(orient="records")
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 