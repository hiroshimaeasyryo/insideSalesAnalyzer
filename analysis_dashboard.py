#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析ダッシュボード生成モジュール

架電データの詳細分析とHTMLダッシュボードの生成を行います
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from pathlib import Path
from data_loader import get_data_loader

def load_and_prepare_data(target_month: str) -> dict:
    """
    指定月のデータを読み込み、分析用に準備する
    
    Args:
        target_month (str): 対象月（YYYY-MM形式）
        
    Returns:
        dict: 処理済みデータ
    """
    loader = get_data_loader()
    
    try:
        # 基本データの読み込み
        basic_data, detail_data, summary_data = loader.load_analysis_data(target_month)
        
        result = {
            'basic_data': None,
            'detail_data': None,
            'summary_data': None,
            'retention_data': None,
            'has_data': False
        }
        
        if not basic_data:
            pass
        else:
            result['basic_data'] = pd.DataFrame(basic_data)
            result['has_data'] = True
        
        if not detail_data:
            pass
        else:
            result['detail_data'] = detail_data
            result['has_data'] = True
        
        if not summary_data:
            pass
        else:
            result['summary_data'] = summary_data
            result['has_data'] = True
        
        # 定着率データの読み込み
        retention_data = loader.load_retention_data(target_month)
        if not retention_data:
            pass
        else:
            result['retention_data'] = retention_data
            result['has_data'] = True
        
        if not result['has_data']:
            return result
        
        # 基本データの前処理
        if result['basic_data'] is not None:
            df_basic = result['basic_data']
            
            # 日付カラムの処理
            if 'date' in df_basic.columns:
                df_basic['date'] = pd.to_datetime(df_basic['date'], errors='coerce')
            
            # 数値カラムの前処理
            numeric_columns = ['call_count', 'reception_bk', 'no_one_in_charge', 'disconnect', 
                             'charge_connected', 'charge_bk', 'get_appointment', 'call_hours']
            
            for col in numeric_columns:
                if col in df_basic.columns:
                    df_basic[col] = pd.to_numeric(df_basic[col], errors='coerce').fillna(0)
            
            # アポ率の計算
            df_basic['appointment_rate'] = (
                df_basic['get_appointment'] / df_basic['call_count'] * 100
            ).fillna(0)
            
            result['basic_data'] = df_basic
        
        return result
        
    except Exception as e:
        return {
            'basic_data': None,
            'detail_data': None,
            'summary_data': None,
            'retention_data': None,
            'has_data': False,
            'error': str(e)
        }

def extract_monthly_conversion_data(detail_data):
    """詳細データから月次コンバージョンデータを抽出"""
    try:
        if 'monthly_conversion' in detail_data:
            return detail_data['monthly_conversion']
        
        # フォールバック：他の形式のデータ構造も試行
        for key in detail_data.keys():
            if 'conversion' in key.lower() or 'monthly' in key.lower():
                return detail_data[key]
        
        return None
        
    except Exception as e:
        return None

def create_daily_trend_chart(df_basic):
    """日別トレンドチャートを作成"""
    if df_basic is None or df_basic.empty:
        return None
    
    try:
        # 日別集計
        daily_stats = df_basic.groupby('date').agg({
            'call_count': 'sum',
            'get_appointment': 'sum',
            'appointment_rate': 'mean'
        }).reset_index()
        
        # チャート作成
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('日別架電数・アポ数', '日別アポ率'),
            vertical_spacing=0.1
        )
        
        # 架電数
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['call_count'],
                name='架電数',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # アポ数
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['get_appointment'],
                name='アポ数',
                line=dict(color='green')
            ),
            row=1, col=1
        )
        
        # アポ率
        fig.add_trace(
            go.Scatter(
                x=daily_stats['date'],
                y=daily_stats['appointment_rate'],
                name='アポ率(%)',
                line=dict(color='red')
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=600,
            title_text="日別パフォーマンス推移",
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        if 'date' not in df_basic.columns:
            pass
        return None

def create_staff_performance_chart(df_basic):
    """スタッフ別パフォーマンスチャートを作成"""
    if df_basic is None or df_basic.empty:
        return None
    
    try:
        # スタッフ別集計
        staff_stats = df_basic.groupby('staff_name').agg({
            'call_count': 'sum',
            'get_appointment': 'sum',
            'call_hours': 'sum'
        }).reset_index()
        
        # アポ率計算
        staff_stats['appointment_rate'] = (
            staff_stats['get_appointment'] / staff_stats['call_count'] * 100
        ).fillna(0)
        
        # 上位20位まで表示
        staff_stats = staff_stats.sort_values('call_count', ascending=False).head(20)
        
        # チャート作成
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('架電数 vs アポ数', 'アポ率ランキング'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 架電数 vs アポ数（散布図）
        fig.add_trace(
            go.Scatter(
                x=staff_stats['call_count'],
                y=staff_stats['get_appointment'],
                mode='markers+text',
                text=staff_stats['staff_name'],
                textposition='top center',
                marker=dict(
                    size=staff_stats['call_hours'] * 2,  # 架電時間でサイズ調整
                    color=staff_stats['appointment_rate'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="アポ率(%)")
                ),
                name='スタッフ'
            ),
            row=1, col=1
        )
        
        # アポ率ランキング（棒グラフ）
        top_performers = staff_stats.nlargest(10, 'appointment_rate')
        fig.add_trace(
            go.Bar(
                x=top_performers['staff_name'],
                y=top_performers['appointment_rate'],
                name='アポ率',
                marker_color='lightblue'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            height=500,
            title_text="スタッフ別パフォーマンス分析",
            showlegend=False
        )
        
        fig.update_xaxes(title_text="架電数", row=1, col=1)
        fig.update_yaxes(title_text="アポ数", row=1, col=1)
        fig.update_xaxes(title_text="スタッフ", tickangle=45, row=1, col=2)
        fig.update_yaxes(title_text="アポ率(%)", row=1, col=2)
        
        return fig
        
    except Exception as e:
        return None

def create_product_analysis_chart(df_basic):
    """商材別分析チャートを作成"""
    if df_basic is None or df_basic.empty:
        return None
    
    try:
        # 商材別集計
        product_stats = df_basic.groupby('product').agg({
            'call_count': 'sum',
            'get_appointment': 'sum',
            'call_hours': 'sum'
        }).reset_index()
        
        # アポ率計算
        product_stats['appointment_rate'] = (
            product_stats['get_appointment'] / product_stats['call_count'] * 100
        ).fillna(0)
        
        # チャート作成
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('商材別架電数', '商材別アポ数', '商材別架電時間', '商材別アポ率'),
            specs=[[{"type": "xy"}, {"type": "xy"}],
                   [{"type": "xy"}, {"type": "xy"}]]
        )
        
        # 商材別架電数
        fig.add_trace(
            go.Bar(x=product_stats['product'], y=product_stats['call_count'], name='架電数'),
            row=1, col=1
        )
        
        # 商材別アポ数
        fig.add_trace(
            go.Bar(x=product_stats['product'], y=product_stats['get_appointment'], name='アポ数'),
            row=1, col=2
        )
        
        # 商材別架電時間
        fig.add_trace(
            go.Bar(x=product_stats['product'], y=product_stats['call_hours'], name='架電時間'),
            row=2, col=1
        )
        
        # 商材別アポ率
        fig.add_trace(
            go.Bar(x=product_stats['product'], y=product_stats['appointment_rate'], name='アポ率'),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            title_text="商材別パフォーマンス分析",
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        return None

def generate_dashboard_html(target_month: str, output_path: str = None) -> str:
    """
    HTMLダッシュボードを生成
    
    Args:
        target_month (str): 対象月（YYYY-MM形式）
        output_path (str): 出力パス（Noneの場合はデフォルト）
        
    Returns:
        str: 生成されたHTMLファイルのパス
    """
    # データ読み込み
    data = load_and_prepare_data(target_month)
    
    if not data['has_data']:
        raise ValueError(f"月 {target_month} のデータが見つかりません")
    
    # チャート作成
    charts = {}
    
    if data['basic_data'] is not None:
        charts['daily_trend'] = create_daily_trend_chart(data['basic_data'])
        charts['staff_performance'] = create_staff_performance_chart(data['basic_data'])
        charts['product_analysis'] = create_product_analysis_chart(data['basic_data'])
    
    # HTML生成
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>架電分析ダッシュボード - {target_month}</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .chart-container {{
                background-color: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .chart {{
                width: 100%;
                height: 500px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📞 架電分析ダッシュボード</h1>
            <h2>{target_month}</h2>
            <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    """
    
    # チャートをHTMLに追加
    chart_id = 0
    for chart_name, chart in charts.items():
        if chart is not None:
            chart_id += 1
            html_content += f"""
            <div class="chart-container">
                <div id="chart{chart_id}" class="chart"></div>
                <script>
                    {chart.to_html(include_plotlyjs=False, div_id=f"chart{chart_id}")}
                </script>
            </div>
            """
    
    html_content += """
    </body>
    </html>
    """
    
    # ファイル保存
    if output_path is None:
        output_dir = Path('output')
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / 'dashboard.html'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return str(output_path)

if __name__ == '__main__':
    # 最新月のダッシュボードを生成
    try:
        loader = get_data_loader()
        months = loader.get_available_months()
        
        if months:
            latest_month = months[0]
            output_file = generate_dashboard_html(latest_month)
        else:
            raise ValueError("利用可能なデータが見つかりません")
            
    except Exception as e:
        pass