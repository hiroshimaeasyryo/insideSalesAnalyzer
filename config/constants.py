"""
定数定義モジュール
アプリケーション全体で使用する定数を管理
"""

# 分析タイプ
ANALYSIS_TYPES = {
    "basic_analysis": "📊 月次サマリー分析",
    "retention_analysis": "📈 定着率分析", 
    "monthly_detail": "📋 単月詳細データ"
}

# ファイルタイプ
FILE_TYPES = {
    "json": "application/json",
    "zip": "application/zip"
}

# データカラム名
COLUMN_NAMES = {
    "date": "date",
    "month": "month",
    "staff_name": "staff_name",
    "branch": "branch",
    "product": "product",
    "call_count": "call_count",
    "call_hours": "call_hours",
    "appointments": "appointments",
    "join_date": "join_date",
    "product_type": "product_type"
}

# メトリクス名
METRIC_NAMES = {
    "total_calls": "総架電数",
    "total_hours": "総架電時間",
    "total_appointments": "総アポ獲得数",
    "efficiency": "効率（架電数/時間）",
    "conversion_rate": "コンバージョン率",
    "retention_rate": "定着率"
}

# ステータス名
STATUS_NAMES = {
    "self_reported_appointments": "日報上のアポ獲得",
    "taaan_entries": "TAAAN入力",
    "approved_deals": "メーカーからの承認",
    "rejected_deals": "却下"
}

# 支部名
BRANCH_NAMES = [
    "東京", "大阪", "名古屋", "福岡", "札幌"
]

# 商材名
PRODUCT_NAMES = [
    "Sansan", "TAAAN", "学生日報"
]

# 在籍期間グループ
TENURE_GROUPS = {
    "<3mo": "3ヶ月未満",
    "3–6mo": "3-6ヶ月",
    "6–12mo": "6-12ヶ月", 
    ">=12mo": "12ヶ月以上",
    "Unknown": "不明"
}

# 月次フォーマット
MONTH_FORMAT = "%Y-%m"

# 日付フォーマット
DATE_FORMAT = "%Y-%m-%d"

# 時間フォーマット
TIME_FORMAT = "%H:%M"

# デフォルト値
DEFAULT_VALUES = {
    "string": "",
    "number": 0,
    "percentage": 0.0,
    "date": "1900-01-01"
}

# エラーメッセージ
ERROR_MESSAGES = {
    "file_not_found": "ファイルが見つかりません",
    "invalid_format": "ファイル形式が正しくありません",
    "data_loading_error": "データの読み込みに失敗しました",
    "processing_error": "データ処理中にエラーが発生しました",
    "authentication_error": "認証に失敗しました"
}

# 成功メッセージ
SUCCESS_MESSAGES = {
    "file_uploaded": "ファイルが正常にアップロードされました",
    "data_loaded": "データが正常に読み込まれました",
    "analysis_completed": "分析が完了しました"
}

# 警告メッセージ
WARNING_MESSAGES = {
    "no_data": "データが見つかりません",
    "insufficient_data": "十分なデータがありません",
    "partial_data": "一部のデータのみ利用可能です"
}

# 情報メッセージ
INFO_MESSAGES = {
    "upload_instruction": "JSONファイルを含むZipファイルをアップロードしてください",
    "analysis_instruction": "分析タイプと月を選択してください",
    "data_processing": "データを処理中です..."
}

# チャート設定
CHART_CONFIG = {
    "height": 400,
    "width": None,
    "use_container_width": True,
    "theme": "plotly_white"
}

# テーブル設定
TABLE_CONFIG = {
    "height": 300,
    "use_container_width": True
}

# メトリクス設定
METRIC_CONFIG = {
    "columns": 4,
    "delta_color": "normal"
} 