#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flaskアプリケーション for インタラクティブダッシュボード
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json
import pandas as pd
import datetime as dt
from analysis_dashboard import extract_monthly_data, FILES

app = Flask(__name__)

# グローバル変数としてデータを保持
global_data = None
base_data = None

def load_data():
    """データを読み込んでグローバル変数に保存"""
    global global_data, base_data
    
    dfs = {}
    for k, p in FILES.items():
        try:
            with p.open(encoding="utf-8") as f:
                raw_data = json.load(f)
            dfs[k] = extract_monthly_data(raw_data)
        except Exception as e:
            print(f"警告: {k} ファイルの読み込みに失敗: {e}")
            dfs[k] = pd.DataFrame()

    # 空のDataFrameを除外
    dfs = {k: v for k, v in dfs.items() if not v.empty}
    
    if not dfs:
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
    if global_data is None:
        if not load_data():
            return "データの読み込みに失敗しました", 500
    
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
        if not load_data():
            return jsonify({'error': 'データの読み込みに失敗しました'}), 500
    
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
    # データを事前に読み込み
    if load_data():
        print("データの読み込みが完了しました")
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("データの読み込みに失敗しました") 