# 設定・定数ファイル
import streamlit as st

# ページ設定
PAGE_CONFIG = {
    "page_title": "インサイドセールス_ダッシュボード",
    "page_icon": "📞",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# 認証設定
CREDENTIALS = {
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

# 支部別色設定
BRANCH_COLORS = {
    '東京': '#ff6b6b',      # 赤
    '横浜': '#4ecdc4',      # ティール
    '名古屋': '#45b7d1',    # 青
    '福岡': '#96ceb4',      # 緑
    '新潟': '#feca57',      # オレンジ
    '大分': '#ff9ff3',      # ピンク
    '未設定': '#95a5a6',    # グレー
    '社員': '#6c5ce7'       # 紫（未設定と区別）
}

# ファイル名パターン
FILE_PATTERNS = {
    'basic': '基本分析_{}.json',
    'detail': '詳細分析_{}.json', 
    'summary': '月次サマリー_{}.json',
    'retention': '定着率分析_{}.json'
}

# カードスタイルCSS
CARD_STYLE = """
<div style="
    background-color: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    padding: 20px 10px 10px 10px;
    margin: 5px;
    text-align: center;
    border-left: 6px solid {color};
    min-width: 170px;
    min-height: 170px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
">
    <div>
        <div style=\"font-size: 1.1em; color: #555;\">{label}</div>
        <div style=\"font-size: 2em; font-weight: bold; color: {color};\">{value}</div>
    </div>
    <div style=\"font-size: 0.9em; color: #888; margin-top: 10px;\">{desc}</div>
</div>
""" 