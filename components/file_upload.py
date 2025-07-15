"""ファイルアップロード処理"""
import streamlit as st
from utils.data_processor import extract_zip_data, get_available_months_from_data

def render_upload_section():
    """ファイルアップロードセクションを表示"""
    st.subheader("📁 データアップロード")
    uploaded_file = st.file_uploader(
        "JSONファイルを含むZipファイルをアップロード",
        type=['zip'],
        help="複数のJSONファイルをZip形式でアップロードしてください"
    )
    
    # アップロードされたデータをセッションに保存
    if uploaded_file is not None:
        if 'json_data' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
            with st.spinner("Zipファイルを処理中..."):
                json_data = extract_zip_data(uploaded_file)
                st.session_state['json_data'] = json_data
                st.session_state['uploaded_file_name'] = uploaded_file.name
                st.session_state['available_months'] = get_available_months_from_data(json_data)
            
            if json_data:
                st.success(f"✅ {len(json_data)}個のJSONファイルを読み込みました")
                st.write(f"利用可能な月: {', '.join(st.session_state['available_months'])}")
            else:
                st.error("❌ JSONファイルが見つかりませんでした")

def render_analysis_selection():
    """分析タイプ選択セクションを表示"""
    # データがアップロードされている場合のみ分析オプションを表示
    if 'json_data' in st.session_state and st.session_state['json_data']:
        st.divider()
        
        # 分析タイプ選択
        st.subheader("📊 分析タイプ")
        analysis_options = {
            "📊 月次サマリー分析": "basic_analysis",
            "📈 定着率分析": "retention_analysis",
            "📋 単月詳細データ": "monthly_detail"
        }
        
        analysis_type = st.selectbox(
            "分析タイプを選択",
            list(analysis_options.keys())
        )
        
        selected_analysis = analysis_options[analysis_type]
        
        # 月選択
        if st.session_state.get('available_months'):
            selected_month = st.selectbox(
                "分析月を選択",
                st.session_state['available_months'],
                index=0
            )
            st.session_state['selected_month'] = selected_month
            
            return selected_analysis, selected_month
        else:
            return selected_analysis, None
    else:
        st.info("📁 データをアップロードして分析を開始してください")
        return None, None

def render_usage_guide():
    """使用方法ガイドを表示"""
    st.title("📊 インサイドセールス分析ダッシュボード")
    st.markdown("""
    ### 使用方法
    
    1. **データの準備**: 分析したいJSONファイルをZip形式で圧縮してください
    2. **アップロード**: 左サイドバーからZipファイルをアップロードしてください
    3. **分析実行**: アップロード後、分析タイプを選択して分析を開始してください
    
    ### 対応ファイル形式
    
    - `基本分析_YYYY-MM.json`
    - `詳細分析_YYYY-MM.json`
    - `月次サマリー_YYYY-MM.json`
    - `定着率分析_YYYY-MM.json`
    
    ### 注意事項
    
    - ファイル名は上記の形式に従ってください
    - 複数の月のデータを含めることができます
    - 最大ファイルサイズ: 200MB
    """) 