"""
設定管理モジュール
アプリケーション全体の設定を管理
"""

import os
from pathlib import Path

# ページ設定
PAGE_CONFIG = {
    "page_title": "インサイドセールス_ダッシュボード",
    "page_icon": "📞",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# 認証設定
AUTH_CREDENTIALS = {
    "usernames": {
        "admin": {
            "name": "管理者",
            "password": "admin123"
        },
        "user": {
            "name": "一般ユーザー",
            "password": "user123"
        }
    }
}

# 認証オブジェクト設定
AUTH_CONFIG = {
    "cookie_name": "dashboard",
    "key": "auth_key",
    "cookie_expiry_days": 30
}

# データ処理設定
DATA_CONFIG = {
    "cache_ttl": 1800,  # 30分間キャッシュ
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "supported_formats": ['.json', '.zip']
}

# 分析設定
ANALYSIS_CONFIG = {
    "default_months_back": 6,  # デフォルトで過去6ヶ月
    "max_months_display": 12,  # 最大表示月数
    "min_data_points": 3  # 最小データポイント数
}

# UI設定
UI_CONFIG = {
    "chart_height": 400,
    "table_height": 300,
    "metric_columns": 4,
    "sidebar_width": 300
}

# ファイルパス設定
def get_data_directory():
    """データディレクトリのパスを取得"""
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_output_directory():
    """出力ディレクトリのパスを取得"""
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir

def get_temp_directory():
    """一時ディレクトリのパスを取得"""
    base_dir = Path(__file__).parent.parent
    temp_dir = base_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir

# 環境変数設定
def get_environment_config():
    """環境変数から設定を取得"""
    return {
        "production_mode": os.getenv("PRODUCTION_MODE", "false").lower() == "true",
        "google_drive_enabled": os.getenv("GOOGLE_DRIVE_ENABLED", "false").lower() == "true",
        "use_local_fallback": os.getenv("USE_LOCAL_FALLBACK", "true").lower() == "true",
        "google_drive_folder_id": os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
        "google_service_account_file": os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    }

# デバッグ設定
DEBUG_CONFIG = {
    "enable_debug_logs": os.getenv("DEBUG", "false").lower() == "true",
    "show_data_info": os.getenv("SHOW_DATA_INFO", "false").lower() == "true",
    "enable_performance_monitoring": os.getenv("PERFORMANCE_MONITORING", "false").lower() == "true"
} 