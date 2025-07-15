"""グラフ作成ロジック"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import streamlit as st

def create_trend_chart(monthly_data, metric_column, metric_name, staff_filter=None, branch_colors=None):
    """
    月別推移チャートを作成（人ごとの色分け、月次表示対応）
    
    Args:
        monthly_data: 月別データ辞書
        metric_column: 指標列名
        metric_name: 指標表示名
        staff_filter: スタッフフィルター（Noneの場合は全スタッフ）
        branch_colors: 支部色設定（人ごと色分けのため現在未使用）
        
    Returns:
        plotly figure
    """
    fig = go.Figure()
    
    # 全スタッフのデータを統合
    all_staff_data = {}
    months = sorted(monthly_data.keys())
    
    for month, df in monthly_data.items():
        if staff_filter:
            df = df[df['staff_name'].isin(staff_filter)]
        
        for _, row in df.iterrows():
            staff_name = row['staff_name']
            branch = row['branch']
            value = row[metric_column]
            
            if staff_name not in all_staff_data:
                all_staff_data[staff_name] = {
                    'months': [],
                    'values': [],
                    'branch': branch
                }
            
            all_staff_data[staff_name]['months'].append(month)
            all_staff_data[staff_name]['values'].append(value)
    
    # 人数に応じた色パレットを生成
    staff_names = list(all_staff_data.keys())
    num_staff = len(staff_names)
    
    if num_staff <= 10:
        # 10人以下の場合はplotlyの標準カラーを使用
        colors = px.colors.qualitative.Plotly
    else:
        # 10人以上の場合はより多くの色を生成
        colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel + px.colors.qualitative.Set1
    
    # 各スタッフの推移線を追加（人ごとに異なる色）
    for i, (staff_name, data) in enumerate(all_staff_data.items()):
        branch = data['branch']
        color = colors[i % len(colors)]  # 色をローテーション
        
        # データが3ヶ月分揃っていない場合の補完
        complete_months = []
        complete_values = []
        for month in months:
            if month in data['months']:
                idx = data['months'].index(month)
                complete_months.append(month)
                complete_values.append(data['values'][idx])
            else:
                complete_months.append(month)
                complete_values.append(None)  # 欠損値
        
        fig.add_trace(go.Scatter(
            x=complete_months,
            y=complete_values,
            mode='lines+markers',
            name=f"{staff_name} ({branch})",
            line=dict(color=color, width=2),
            marker=dict(size=8, color=color),
            connectgaps=False,  # 欠損値は接続しない
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         '月: %{x}<br>' +
                         f'{metric_name}: %{{y}}<br>' +
                         '<extra></extra>'
        ))
    
    # 月次表示のためのx軸フォーマット設定
    fig.update_layout(
        title=f"📈 {metric_name} - 3ヶ月推移",
        xaxis=dict(
            title="月",
            type='category',  # カテゴリ軸として扱う
            categoryorder='array',
            categoryarray=months,
            tickangle=45
        ),
        yaxis_title=metric_name,
        hovermode='x unified',
        showlegend=True,
        height=600,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        margin=dict(r=150)  # 凡例のためのマージン
    )
    
    return fig

def create_monthly_histogram(monthly_data, metric_column, metric_name, staff_filter=None):
    """
    月別ヒストグラムを作成（月ごとに色分けし、最適なbinサイズで統一）
    
    Args:
        monthly_data: 月別データ辞書
        metric_column: 指標列名
        metric_name: 指標表示名
        staff_filter: スタッフフィルター
        
    Returns:
        plotly figure
    """
    import numpy as np
    
    fig = go.Figure()
    
    months = sorted(monthly_data.keys())
    # 月ごとに区別しやすい色（Plotlyのカテゴリカルカラーパレット）
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # 全データを収集してbinサイズを計算
    all_values = []
    monthly_values = {}
    
    for month in months:
        if month in monthly_data:
            df = monthly_data[month]
            if staff_filter:
                df = df[df['staff_name'].isin(staff_filter)]
            
            values = df[metric_column].dropna().tolist()
            if values:
                monthly_values[month] = values
                all_values.extend(values)
    
    if not all_values:
        return go.Figure()
    
    # 最適なbinサイズを計算（Sturgesの法則とFreedman-Diaconisの法則の中間値）
    n_data = len(all_values)
    sturges_bins = int(np.log2(n_data) + 1)
    
    # データの範囲とIQRを計算
    q75, q25 = np.percentile(all_values, [75, 25])
    iqr = q75 - q25
    
    if iqr > 0:
        # Freedman-Diaconisの法則
        h = 2 * iqr / (n_data ** (1/3))
        fd_bins = int((max(all_values) - min(all_values)) / h) if h > 0 else sturges_bins
        # 適切な範囲内に制限
        optimal_bins = max(5, min(30, int((sturges_bins + fd_bins) / 2)))
    else:
        optimal_bins = sturges_bins
    
    # 共通のbinエッジを計算
    data_min, data_max = min(all_values), max(all_values)
    bin_edges = np.linspace(data_min, data_max, optimal_bins + 1)
    
    # 各月のヒストグラムを作成
    for i, month in enumerate(months):
        if month in monthly_values:
            values = monthly_values[month]
            
            fig.add_trace(go.Histogram(
                x=values,
                name=f"{month} (n={len(values)})",
                opacity=0.7,
                marker_color=colors[i % len(colors)],
                xbins=dict(
                    start=data_min,
                    end=data_max,
                    size=(data_max - data_min) / optimal_bins
                ),
                histnorm='probability density',  # 確率密度で正規化
                legendgroup=month
            ))
    
    fig.update_layout(
        title=dict(
            text=f"📊 {metric_name} - 月別分布比較",
            x=0.5,
            font=dict(size=16)
        ),
        xaxis_title=metric_name,
        yaxis_title="確率密度",
        barmode='overlay',
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified'
    )
    
    return fig

def create_funnel_chart(values, labels, title="営業フロー ファネルチャート"):
    """
    ファネルチャートを作成
    
    Args:
        values: 値のリスト
        labels: ラベルのリスト
        title: チャートタイトル
        
    Returns:
        plotly figure
    """
    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="value+percent previous"
    ))
    fig.update_layout(title=title, height=350)
    return fig

def create_pie_chart(labels, values, title="円グラフ", colors=None):
    """
    円グラフを作成
    
    Args:
        labels: ラベルのリスト
        values: 値のリスト
        title: チャートタイトル
        colors: 色のリスト（オプション）
        
    Returns:
        plotly figure
    """
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        marker_colors=colors
    )])
    fig.update_layout(title=title, height=350)
    return fig

def create_bar_chart(df, x, y, title, color=None, color_discrete_sequence=None):
    """
    棒グラフを作成
    
    Args:
        df: DataFrame
        x: x軸の列名
        y: y軸の列名
        title: チャートタイトル
        color: 色分けの列名（オプション）
        color_discrete_sequence: 色のリスト（オプション）
        
    Returns:
        plotly figure
    """
    if color:
        fig = px.bar(df, x=x, y=y, title=title, color=color,
                    color_discrete_sequence=color_discrete_sequence)
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                    color_discrete_sequence=color_discrete_sequence)
    
    fig.update_layout(
        height=350,
        yaxis=dict(tickformat=',', separatethousands=True)
    )
    return fig

def create_line_chart(df, x, y, color=None, title="線グラフ", markers=True):
    """
    線グラフを作成
    
    Args:
        df: DataFrame
        x: x軸の列名
        y: y軸の列名
        color: 色分けの列名（オプション）
        title: チャートタイトル
        markers: マーカーを表示するか
        
    Returns:
        plotly figure
    """
    fig = px.line(df, x=x, y=y, color=color, title=title, markers=markers)
    fig.update_layout(
        height=400,
        yaxis=dict(tickformat=',', separatethousands=True)
    )
    return fig

def create_heatmap(data, x_labels, y_labels, title="ヒートマップ", colorscale="Blues"):
    """
    ヒートマップを作成
    
    Args:
        data: 2次元配列データ
        x_labels: x軸ラベル
        y_labels: y軸ラベル
        title: チャートタイトル
        colorscale: カラースケール
        
    Returns:
        plotly figure
    """
    # 数値をカンマ区切りで表示するためのテキスト配列を作成
    text = [[f"{val:,}" if isinstance(val, (int, float)) else str(val) for val in row] for row in data]
    
    fig = go.Figure(
        data=go.Heatmap(
            z=data,
            x=x_labels,
            y=y_labels,
            text=text,
            texttemplate="%{text}",
            colorscale=colorscale
        )
    )
    
    fig.update_layout(
        title=title,
        height=500,
        xaxis_title="商材",
        yaxis_title="支部"
    )
    
    return fig 