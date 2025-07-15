"""
単月詳細データ分析パッケージ
機能別に分割された分析モジュールを統合
"""

# 各モジュールからの関数をエクスポート
from .main import render_monthly_detail_page
# from .daily_trend import render_daily_trend_tab
# from .branch_analysis import render_branch_analysis_tab
# from .staff_analysis import render_staff_analysis_tab
from .product_analysis import render_product_analysis_tab
# from .detail_data import render_detail_data_tab

__version__ = "1.0.0"
__author__ = "InsideSales Team" 