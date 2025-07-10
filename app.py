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
from data_loader import get_data_loader
import streamlit as st

app = Flask(__name__)

# グローバル変数としてデータを保持
global_data = None
base_data = None

def load_data():
    """データを読み込んでグローバル変数に保存"""
    global global_data, base_data
    
    try:
        loader = get_data_loader()
        available_months = loader.get_available_months()
        
        if not available_months:
            print("警告: 利用可能なデータが見つかりません")
            return False
        
        # 最新月のデータを使用
        target_month = available_months[0]
        basic_data, detail_data, summary_data = loader.load_analysis_data(target_month)
        
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

def get_debug_info():
    # This function is not provided in the original file or the new code block
    # It's assumed to exist as it's called in the new code block
    pass

if __name__ == '__main__':
    # データを事前に読み込み
    if load_data():
        print("データの読み込みが完了しました")
        app.run(debug=True, host='0.0.0.0', port=5001)
    else:
        print("データの読み込みに失敗しました")

    if st.button("🔍 詳細デバッグ情報を取得", type="primary"):
        with st.spinner("詳細情報を取得中..."):
            debug_info = get_debug_info()
            
            # 基本設定情報
            st.subheader("🔧 設定状態")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**PRODUCTION_MODE**: {debug_info['config']['PRODUCTION_MODE']}")
                st.write(f"**GOOGLE_DRIVE_ENABLED**: {debug_info['config']['GOOGLE_DRIVE_ENABLED']}")
                st.write(f"**USE_LOCAL_FALLBACK**: {debug_info['config']['USE_LOCAL_FALLBACK']}")
                st.write(f"**FOLDER_ID**: {debug_info['config']['GOOGLE_DRIVE_FOLDER_ID']}")
            
            # Streamlit Secrets状態
            st.subheader("🔐 Streamlit Secrets状態")
            if debug_info['secrets']['available']:
                st.success(f"✅ Secrets利用可能")
                st.write(f"**設定済みキー**: {debug_info['secrets']['keys']}")
                st.write(f"**google_driveキー**: {debug_info['secrets']['google_drive_keys']}")
                st.write(f"**service_account長さ**: {debug_info['secrets']['service_account_length']}")
                
                # Service Account JSON詳細検証
                st.subheader("🔍 Service Account JSON詳細")
                service_account_data = st.secrets.get("google_drive", {}).get("service_account", "")
                
                if service_account_data:
                    try:
                        import json
                        parsed_json = json.loads(service_account_data)
                        st.success("✅ JSON形式: 正常")
                        
                        # 重要なフィールドの確認
                        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri"]
                        missing_fields = [field for field in required_fields if field not in parsed_json]
                        
                        if missing_fields:
                            st.error(f"❌ 不足フィールド: {missing_fields}")
                        else:
                            st.success("✅ 必要フィールド: 全て存在")
                        
                        # private_keyの詳細確認
                        private_key = parsed_json.get("private_key", "")
                        if private_key:
                            st.write(f"**private_key長さ**: {len(private_key)}")
                            st.write(f"**private_key開始**: {private_key[:50]}...")
                            st.write(f"**改行文字数**: {private_key.count('\\n')}")
                            
                            # PEM形式の確認
                            if "-----BEGIN PRIVATE KEY-----" in private_key and "-----END PRIVATE KEY-----" in private_key:
                                st.success("✅ PEM形式ヘッダー: 正常")
                            else:
                                st.error("❌ PEM形式ヘッダー: 不正")
                            
                            # 改行文字の問題確認
                            if "\\n" in private_key:
                                st.warning("⚠️ エスケープされた改行文字を検出")
                                st.info("💡 解決方法: private_keyの\\nを実際の改行文字に置換する必要があります")
                        else:
                            st.error("❌ private_keyが見つかりません")
                        
                    except json.JSONDecodeError as e:
                        st.error(f"❌ JSON解析エラー: {str(e)}")
                        st.text("JSONの先頭50文字:")
                        st.code(service_account_data[:50])
                else:
                    st.error("❌ service_accountデータが見つかりません")
            
            # 環境変数状態
            st.subheader("🌍 環境変数状態")
            if debug_info['environment']['GOOGLE_SERVICE_ACCOUNT']:
                st.success("✅ GOOGLE_SERVICE_ACCOUNT: 設定済み")
                st.write(f"**プロジェクトID**: {debug_info['environment']['project_id']}")
                st.write(f"**クライアントメール**: {debug_info['environment']['client_email']}")
            else:
                st.error("❌ GOOGLE_SERVICE_ACCOUNT: 未設定")
            
            # 接続テスト
            st.subheader("🔗 接続テスト")
            
            col1, col2 = st.columns(2)
            with col1:
                if debug_info['connection']['force_refresh_success']:
                    st.success("✅ 強制リフレッシュテスト: 成功")
                else:
                    st.error("❌ 強制リフレッシュテスト: 失敗")
                    st.error(f"エラー詳細: {debug_info['connection']['force_refresh_error']}")
            
            with col2:
                if debug_info['connection']['normal_success']:
                    st.success("✅ 通常テスト: 成功")
                else:
                    st.error("❌ 通常テスト: 失敗")
                    st.error(f"エラー: {debug_info['connection']['normal_error']}")
            
            # 解決方法の提案
            if not debug_info['connection']['normal_success']:
                st.subheader("💡 解決方法")
                if "Unable to load PEM file" in str(debug_info['connection']['normal_error']):
                    st.info("""
                    **private_keyの改行文字問題の解決方法:**
                    
                    1. Google Cloud ConsoleからService Accountキーを再ダウンロード
                    2. JSONファイルを開いて、private_keyフィールドの内容をコピー
                    3. Streamlit Cloudの設定で、private_keyの値の\\nを実際の改行に置換
                    4. または、下記のボタンで自動修正を試行
                    """)
                    
                    if st.button("🔧 private_key自動修正を試行"):
                        try:
                            import json
                            service_account_data = st.secrets.get("google_drive", {}).get("service_account", "")
                            parsed_json = json.loads(service_account_data)
                            
                            # private_keyの修正
                            if "private_key" in parsed_json:
                                original_key = parsed_json["private_key"]
                                fixed_key = original_key.replace("\\n", "\n")
                                
                                st.text("修正前の改行文字数:")
                                st.code(f"\\n文字数: {original_key.count('\\n')}")
                                st.text("修正後の改行文字数:")
                                st.code(f"実際の改行数: {fixed_key.count(chr(10))}")
                                
                                # 修正したJSONを表示（実際の適用は手動で行う必要がある）
                                parsed_json["private_key"] = fixed_key
                                st.text("修正後のJSON（手動でStreamlit Secretsに設定してください）:")
                                st.code(json.dumps(parsed_json, indent=2))
                            
                        except Exception as e:
                            st.error(f"自動修正エラー: {str(e)}") 