"""
共通モジュールパッケージ
カラーパレット、フォーマット機能、ヘルパー関数を提供
"""

from .colors import (
    BRANCH_COLORS,
    PRODUCT_COLORS,
    STATUS_COLORS,
    PERFORMANCE_COLORS,
    GRADIENT_COLORS,
    get_branch_color,
    get_product_color,
    get_status_color,
    get_performance_color
)

from .formatting import (
    format_number,
    format_percentage,
    format_currency,
    format_time,
    format_date,
    format_month,
    format_cross_table_value,
    format_efficiency,
    format_conversion_rate
)

from .helpers import (
    get_prev_months,
    validate_month_format,
    extract_month_from_filename,
    calculate_working_days,
    convert_utc_to_jst,
    safe_divide,
    validate_json_data,
    get_latest_month,
    format_duration_hours,
    calculate_percentage_change
)

__all__ = [
    # Colors
    'BRANCH_COLORS',
    'PRODUCT_COLORS', 
    'STATUS_COLORS',
    'PERFORMANCE_COLORS',
    'GRADIENT_COLORS',
    'get_branch_color',
    'get_product_color',
    'get_status_color',
    'get_performance_color',
    
    # Formatting
    'format_number',
    'format_percentage',
    'format_currency',
    'format_time',
    'format_date',
    'format_month',
    'format_cross_table_value',
    'format_efficiency',
    'format_conversion_rate',
    
    # Helpers
    'get_prev_months',
    'validate_month_format',
    'extract_month_from_filename',
    'calculate_working_days',
    'convert_utc_to_jst',
    'safe_divide',
    'validate_json_data',
    'get_latest_month',
    'format_duration_hours',
    'calculate_percentage_change'
]
