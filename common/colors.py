"""
カラーパレット定義モジュール
支部、商材、商談ステータスのテーマカラーを統一管理
"""

# 支部のテーマカラー
BRANCH_COLORS = {
    "東京": "#FF6B6B",
    "大阪": "#4ECDC4", 
    "名古屋": "#45B7D1",
    "福岡": "#96CEB4",
    "札幌": "#FFEAA7",
    "その他": "#DDA0DD"  # デフォルト色
}

# 商材のテーマカラー
PRODUCT_COLORS = {
    "Sansan": "#FF6B6B",
    "TAAAN": "#4ECDC4",
    "学生日報": "#45B7D1",
    "その他": "#DDA0DD"  # デフォルト色
}

# 商談ステータスのテーマカラー
STATUS_COLORS = {
    "アポ獲得": "#2ECC71",
    "TAAAN入力": "#F39C12", 
    "承認": "#E74C3C",
    "却下": "#95A5A6",
    "その他": "#DDA0DD"  # デフォルト色
}

# パフォーマンス指標のカラー
PERFORMANCE_COLORS = {
    "効率": "#3498DB",
    "コンバージョン": "#E74C3C",
    "定着率": "#2ECC71",
    "時間": "#F39C12"
}

# グラデーションカラー
GRADIENT_COLORS = {
    "青系": ["#3498DB", "#2980B9", "#1F618D"],
    "緑系": ["#2ECC71", "#27AE60", "#1E8449"],
    "赤系": ["#E74C3C", "#C0392B", "#A93226"],
    "オレンジ系": ["#F39C12", "#E67E22", "#D68910"]
}

def get_branch_color(branch_name):
    """支部名からカラーを取得"""
    return BRANCH_COLORS.get(branch_name, BRANCH_COLORS["その他"])

def get_product_color(product_name):
    """商材名からカラーを取得"""
    return PRODUCT_COLORS.get(product_name, PRODUCT_COLORS["その他"])

def get_status_color(status_name):
    """ステータス名からカラーを取得"""
    return STATUS_COLORS.get(status_name, STATUS_COLORS["その他"])

def get_performance_color(metric_name):
    """パフォーマンス指標名からカラーを取得"""
    return PERFORMANCE_COLORS.get(metric_name, PERFORMANCE_COLORS["効率"]) 