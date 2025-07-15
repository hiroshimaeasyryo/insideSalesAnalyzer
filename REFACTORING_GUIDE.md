# リファクタリングガイド

## 概要

`streamlit_app.py`（3400行超）を機能別・レイヤー別に分離し、保守性とテスト容易性を向上させました。

## 新しいディレクトリ構造

```
InsideSalesGenerateJson/
├── streamlit_app_refactored.py  # 新しいメインファイル（200行未満）
├── auth/
│   └── authentication.py       # 認証処理
├── components/
│   ├── charts.py               # グラフ作成
│   ├── rankings.py             # ランキング表示
│   └── file_upload.py          # ファイルアップロード
├── pages/
│   └── monthly_detail.py       # 月次詳細ページ
├── utils/
│   ├── config.py               # 設定・定数
│   ├── data_processor.py       # データ処理
│   └── formatters.py           # フォーマット処理
└── streamlit_app.py            # 元のファイル（バックアップ）
```

## 分離の利点

### 1. 可読性の向上
- **元**: 3400行の巨大ファイル
- **新**: 機能別に分離された100-300行のファイル

### 2. 保守性の向上
- 関連する機能がまとまっている
- 変更の影響範囲が限定される
- 単体テストが書きやすい

### 3. 再利用性の向上
- 共通機能（グラフ作成、ランキング表示など）を他のページで再利用可能
- 設定の一元管理

### 4. チーム開発の改善
- 異なる機能を並行して開発可能
- コンフリクトの発生確率が低下

## 主要な分離単位

### 🔐 認証レイヤー（`auth/`）
```python
# 使用例
from auth.authentication import handle_authentication, display_auth_sidebar

authenticator, auth_status, name, username = handle_authentication()
display_auth_sidebar(authenticator, name)
```

### 📊 データ処理レイヤー（`utils/data_processor.py`）
```python
# 使用例
from utils.data_processor import extract_zip_data, load_analysis_data_from_json

json_data = extract_zip_data(uploaded_file)
basic_data, detail_data, summary_data = load_analysis_data_from_json(json_data, month)
```

### 📈 グラフ作成コンポーネント（`components/charts.py`）
```python
# 使用例
from components.charts import create_funnel_chart, create_pie_chart

fig = create_funnel_chart(values, labels, "営業フロー")
st.plotly_chart(fig, use_container_width=True)
```

### 🏆 ランキング表示コンポーネント（`components/rankings.py`）
```python
# 使用例
from components.rankings import display_ranking_with_ties

display_ranking_with_ties(
    df, 'total_calls', ['total_calls'], 
    max_rank=10, branch_colors=BRANCH_COLORS
)
```

### 📝 フォーマット処理（`utils/formatters.py`）
```python
# 使用例
from utils.formatters import format_currency, format_percentage

formatted_revenue = format_currency(123456)  # "¥123,456"
formatted_rate = format_percentage(75.5)     # "75.5%"
```

## 移行手順

### 1. バックアップ作成
```bash
cp streamlit_app.py streamlit_app_backup.py
```

### 2. 新しいファイル構造の確認
全ての新しいファイルが正しく作成されていることを確認してください。

### 3. 依存関係の確認
```bash
pip install streamlit streamlit-authenticator pandas plotly
```

### 4. 動作テスト
```bash
streamlit run streamlit_app_refactored.py
```

### 5. 段階的移行
元のファイルを残したまま、新しいファイルで動作確認を行い、問題なければ入れ替え。

## 設定の一元管理

すべての設定は`utils/config.py`に集約されています：

```python
# 色設定
BRANCH_COLORS = {
    '東京': '#ff6b6b',
    '横浜': '#4ecdc4',
    # ...
}

# ページ設定
PAGE_CONFIG = {
    "page_title": "インサイドセールス_ダッシュボード",
    "page_icon": "📞",
    # ...
}
```

## 今後の拡張性

### 新しいページの追加
```python
# pages/new_analysis.py
def render_new_analysis_page(json_data, selected_month):
    st.header("新しい分析")
    # 分析ロジック

# streamlit_app_refactored.py に追加
elif selected_analysis == "new_analysis":
    render_new_analysis_page(json_data, selected_month)
```

### 新しいグラフタイプの追加
```python
# components/charts.py に追加
def create_new_chart_type(data, title):
    # チャート作成ロジック
    return fig
```

## 注意事項

1. **インポートエラー**: 新しい構造でのインポートパスに注意
2. **セッション状態**: 既存のセッション状態変数は維持
3. **設定値**: `config.py`の設定値を環境に応じて調整

## トラブルシューティング

### よくあるエラー

1. **ModuleNotFoundError**
   - ディレクトリ構造とインポートパスを確認
   - `__init__.py`ファイルが存在するか確認

2. **設定値エラー**
   - `utils/config.py`の設定値を確認
   - 元のファイルから設定値を移行

3. **機能の欠落**
   - 一部の機能が省略されている場合は元のファイルから移植

## まとめ

このリファクタリングにより：
- **保守性**: 3400行→200行未満のメインファイル
- **テスト容易性**: 機能別の単体テスト可能
- **開発効率**: 複数人での並行開発可能
- **拡張性**: 新機能の追加が容易

より効率的で持続可能なコードベースになりました。 