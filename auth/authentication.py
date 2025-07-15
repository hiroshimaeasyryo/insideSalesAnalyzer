"""認証処理ロジック"""
import streamlit as st
import streamlit_authenticator as stauth
from utils.config import CREDENTIALS

def initialize_authenticator():
    """認証オブジェクトを初期化"""
    authenticator = stauth.Authenticate(
        CREDENTIALS,
        "dashboard",
        "auth_key",
        cookie_expiry_days=30
    )
    return authenticator

def handle_authentication():
    """認証処理を実行し、認証状態を返す"""
    # 認証オブジェクトを作成
    authenticator = initialize_authenticator()
    
    # ログインフォームをmainエリアに表示
    authenticator.login(location='main', key='ログイン')
    
    # 認証状態をセッションから取得
    authentication_status = st.session_state.get("authentication_status")
    name = st.session_state.get("name")
    username = st.session_state.get("username")
    
    return authenticator, authentication_status, name, username

def display_auth_sidebar(authenticator, name):
    """サイドバーに認証情報を表示"""
    with st.sidebar:
        st.title("🔐 認証")
        authenticator.logout('ログアウト', 'sidebar')
        st.write(f'ようこそ **{name}** さん')

def show_auth_error(authentication_status):
    """認証エラーを表示"""
    if authentication_status == False:
        st.error('❌ ユーザー名/パスワードが間違っています')
    elif authentication_status == None:
        st.warning('⚠️ ユーザー名とパスワードを入力してください') 