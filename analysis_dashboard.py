#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analysis_dashboard.py

概要:
  - /data 配下の 3 つの JSON を読み込み、必要な集計値を算出
  - /templates/dashboard_template.html をレンダリングして
    /output/dashboard.html に書き出す

json 構造が多少変わっても最低限動くよう、列名マッピングは
先頭 few rows を自動推定しつつ手動 override も可能。
"""

from pathlib import Path
import json
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import datetime as dt

# ---------- 設定 ----------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "dataset"
TPL_DIR  = ROOT / "templates"
OUT_DIR  = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

# ファイルパス
FILES = {
    "basic": DATA_DIR / "基本分析_2025-06.json",
    "monthly": DATA_DIR / "月次サマリー_2025-06.json",
    "detail": DATA_DIR / "詳細分析_2025-06.json",
}

# ---------- ユーティリティ ----------
def load_json(path: Path) -> pd.DataFrame:
    """JSON → pandas.DataFrame（階層構造も自動 flatten）"""
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    return pd.json_normalize(raw)

def extract_monthly_data(json_data):
    """階層構造のJSONから月次データを抽出"""
    monthly_records = []
    
    if 'monthly_analysis' in json_data:
        for month_key, month_data in json_data['monthly_analysis'].items():
            # 月の基本情報
            month = month_data.get('month', month_key)
            
            # 支店データの抽出
            if 'branches' in month_data:
                for branch_name, branch_data in month_data['branches'].items():
                    record = {
                        'date': month,
                        'month': month,
                        'branch': branch_data.get('branch_name', branch_name),
                        'calls': branch_data.get('total_calls', 0),
                        'call_hours': branch_data.get('total_hours', 0),
                        'appointments': branch_data.get('total_appointments', 0),
                        'deals': branch_data.get('total_deals', 0),
                        'approved': branch_data.get('total_approved', 0),
                        'rejected': branch_data.get('total_rejected', 0),
                        'approval_rate': branch_data.get('approval_rate', 0)
                    }
                    monthly_records.append(record)
            
            # スタッフデータの抽出
            if 'staff' in month_data:
                for staff_name, staff_data in month_data['staff'].items():
                    record = {
                        'date': month,
                        'month': month,
                        'staff': staff_data.get('staff_name', staff_name),
                        'branch': staff_data.get('branch', ''),
                        'join_date': staff_data.get('join_date', ''),
                        'calls': staff_data.get('total_calls', 0),
                        'call_hours': staff_data.get('total_hours', 0),
                        'appointments': staff_data.get('total_appointments', 0),
                        'deals': staff_data.get('total_deals', 0),
                        'approved': staff_data.get('total_approved', 0),
                        'rejected': staff_data.get('total_rejected', 0),
                        'approval_rate': staff_data.get('approval_rate', 0)
                    }
                    monthly_records.append(record)
    
    return pd.DataFrame(monthly_records)

def safe_mean(s):
    return (s.sum() / s.count()) if s.count() else 0

# ---------- データロード ----------
dfs = {}
for k, p in FILES.items():
    try:
        with p.open(encoding="utf-8") as f:
            raw_data = json.load(f)
        dfs[k] = extract_monthly_data(raw_data)
    except Exception as e:
        print(f"警告: {k} ファイルの読み込みに失敗: {e}")
        dfs[k] = pd.DataFrame()

# 定着率分析データのロード
RETENTION_PATH = DATA_DIR / "定着率分析_2025-06.json"
try:
    with RETENTION_PATH.open(encoding="utf-8") as f:
        retention_json = json.load(f)
except Exception as e:
    print(f"警告: 定着率分析ファイルの読み込みに失敗: {e}")
    retention_json = {}

# 空のDataFrameを除外
dfs = {k: v for k, v in dfs.items() if not v.empty}

if not dfs:
    print("エラー: 読み込めるデータがありません")
    exit(1)

# ---------- monthly_conversionの抽出 ----------
conversion = []
try:
    with FILES["basic"].open(encoding="utf-8") as f:
        basic_json = json.load(f)
    monthly_conv = basic_json.get("monthly_conversion", {})
    for month, month_data in monthly_conv.items():
        # 全体
        total = month_data.get("total", {})
        conversion.append({
            "month": month,
            "type": "total",
            **total
        })
        # スタッフ別
        for staff, sdata in month_data.get("by_staff", {}).items():
            conversion.append({
                "month": month,
                "type": "staff",
                "name": staff,
                **sdata
            })
        # 支部別
        for branch, bdata in month_data.get("by_branch", {}).items():
            conversion.append({
                "month": month,
                "type": "branch",
                "name": branch,
                **bdata
            })
        # 商材別
        for prod, pdata in month_data.get("by_product", {}).items():
            conversion.append({
                "month": month,
                "type": "product",
                "name": prod,
                **pdata
            })
    conversion_df = pd.DataFrame(conversion)
except Exception as e:
    print(f"警告: monthly_conversion抽出失敗: {e}")
    conversion_df = pd.DataFrame()

# ---------- 定着率分析の抽出 ----------
# 月次定着率推移
retention_trend = []
if "monthly_retention_rates" in retention_json:
    for month, r in retention_json["monthly_retention_rates"].items():
        retention_trend.append({
            "month": month,
            "active_staff": r.get("active_staff", 0),
            "total_staff": r.get("total_staff", 0),
            "retention_rate": float(r.get("retention_rate", 0))
        })
    retention_trend_df = pd.DataFrame(retention_trend)
else:
    retention_trend_df = pd.DataFrame()

# スタッフ別定着率
staff_retention = []
if "staff_retention_analysis" in retention_json:
    for staff, s in retention_json["staff_retention_analysis"].items():
        staff_retention.append({
            "staff_name": staff,
            "branch": s.get("branch", ""),
            "risk_level": s.get("risk_level", ""),
            "risk_score": s.get("risk_score", 0),
            "monthly_activity_rate": float(s.get("monthly_activity_rate", 0)),
            "appointment_rate": float(s.get("appointment_rate", 0)),
            "total_calls": s.get("total_calls", 0),
            "total_appointments": s.get("total_appointments", 0)
        })
    staff_retention_df = pd.DataFrame(staff_retention)
else:
    staff_retention_df = pd.DataFrame()

# 支部別定着率
branch_retention = []
if "branch_retention_analysis" in retention_json:
    for branch, b in retention_json["branch_retention_analysis"].items():
        branch_retention.append({
            "branch": branch,
            "total_staff": b.get("total_staff", 0),
            "active_staff": b.get("active_staff", 0),
            "avg_activity_rate": float(b.get("avg_activity_rate", 0)),
            "avg_risk_score": float(b.get("avg_risk_score", 0)),
            "high_risk_staff": b.get("high_risk_staff", 0),
            "medium_risk_staff": b.get("medium_risk_staff", 0),
            "low_risk_staff": b.get("low_risk_staff", 0)
        })
    branch_retention_df = pd.DataFrame(branch_retention)
else:
    branch_retention_df = pd.DataFrame()

# リスクリスト
risk_lists = {
    "high": retention_json.get("risk_analysis", {}).get("high_risk_staff", []),
    "medium": retention_json.get("risk_analysis", {}).get("medium_risk_staff", []),
    "low": retention_json.get("risk_analysis", {}).get("low_risk_staff", [])
}

# ---------- マスタ結合（必要であれば） ----------
base = pd.concat(dfs.values(), ignore_index=True)

# ---------- 前処理 ----------
# date列が存在するかチェック
if 'date' not in base.columns:
    print("エラー: date列が見つかりません")
    print("利用可能な列:", list(base.columns))
    exit(1)

base['date'] = pd.to_datetime(base['date'], errors='coerce')
base['month'] = base['date'].dt.to_period('M').astype(str)
base['join_date'] = pd.to_datetime(base['join_date'], errors='coerce')

# タイムゾーン情報を統一（タイムゾーン情報を削除）
base['date'] = base['date'].dt.tz_localize(None)
base['join_date'] = base['join_date'].dt.tz_localize(None)

base['tenure_months'] = ((base['date'] - base['join_date']) / pd.Timedelta(days=30)).round()

# tenure bucket
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
base['tenure_grp'] = base['tenure_months'].apply(bucket)

# ---------- 集計 ----------
# 1) 月次
monthly = (
    base.groupby('month')
        .agg(calls=('calls','sum'),
             appointments=('appointments','sum'),
             hours=('call_hours','sum'))
        .assign(eff=lambda x: x.calls / x.hours,
                conv=lambda x: x.appointments / x.calls * 100)
        .reset_index()
)

# 利用可能な月のリストを生成（直近6ヶ月）
available_months = sorted(monthly['month'].unique(), reverse=True)[:6]
latest_month = available_months[0] if available_months else None

# 2) 支店 × 月
branch_month = (
    base.groupby(['month','branch'])
        .agg(calls=('calls','sum'),
             hours=('call_hours','sum'))
        .assign(eff=lambda x: x.calls / x.hours)
        .reset_index()
)

# 3) 選択された月のデータ（デフォルトは最新月）
selected_month = latest_month
latest_df = base[base['month'] == selected_month]

branch_latest = (
    latest_df.groupby('branch')
        .agg(calls=('calls','sum'),
             hours=('call_hours','sum'),
             appointments=('appointments','sum'))
        .assign(eff=lambda x: x.calls / x.hours,
                conv=lambda x: x.appointments / x.calls * 100)
        .sort_values('eff', ascending=False)
        .reset_index()
)

staff_eff = (
    latest_df.groupby('staff')
        .agg(calls=('calls','sum'),
             hours=('call_hours','sum'))
        .assign(eff=lambda x: x.calls / x.hours)
        .sort_values('eff', ascending=False)
        .head(5)
        .reset_index()
)

staff_conv = (
    latest_df.groupby('staff')
        .agg(calls=('calls','sum'),
             appointments=('appointments','sum'))
        .assign(conv=lambda x: x.appointments / x.calls * 100)
        .sort_values('conv', ascending=False)
        .head(5)
        .reset_index()
)

tenure_perf = (
    base.groupby('tenure_grp')
        .agg(calls=('calls','sum'),
             hours=('call_hours','sum'),
             appointments=('appointments','sum'))
        .assign(eff=lambda x: x.calls / x.hours,
                conv=lambda x: x.appointments / x.calls * 100)
        .reset_index()
)

# サマリー統計の計算
summary = {
    'total_calls': int(base['calls'].sum()),
    'total_hours': int(base['call_hours'].sum()),
    'total_appointments': int(base['appointments'].sum()),
    'avg_efficiency': float(base['calls'].sum() / base['call_hours'].sum()) if base['call_hours'].sum() > 0 else 0
}

# ---------- テンプレートレンダリング ----------
env = Environment(loader=FileSystemLoader(TPL_DIR), autoescape=True)
tpl = env.get_template("dashboard_template.html")

rendered = tpl.render(
    generated_at=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    monthly=monthly.to_dict(orient="records"),
    branch_trend=branch_month.to_dict(orient="records"),
    branch_latest=branch_latest.to_dict(orient="records"),
    staff_eff=staff_eff.to_dict(orient="records"),
    staff_conv=staff_conv.to_dict(orient="records"),
    tenure_perf=tenure_perf.to_dict(orient="records"),
    summary=summary,
    available_months=available_months,
    selected_month=selected_month,
    conversion=conversion_df.to_dict(orient="records"),
    retention_trend=retention_trend_df.to_dict(orient="records"),
    staff_retention=staff_retention_df.to_dict(orient="records"),
    branch_retention=branch_retention_df.to_dict(orient="records"),
    risk_lists=risk_lists
)

(OUT_DIR / "dashboard.html").write_text(rendered, encoding="utf-8")
print("✔ ダッシュボードを output/dashboard.html に生成しました")