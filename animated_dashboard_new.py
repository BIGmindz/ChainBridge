"""
Professional Trading Dashboard combining TradingView and Robinhood styles
"""

import dash
from dash import html, dcc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import math
from typing import Dict
from datetime import datetime

# TradingView Color Scheme
TV_COLORS = {
    'blue': 'rgba(0, 195, 255, 0.95)',
    'red': 'rgba(255, 45, 85, 0.95)',
    'green': 'rgba(50, 255, 150, 0.95)',
    'orange': 'rgba(255, 140, 0, 0.95)',
    'purple': 'rgba(191, 0, 255, 0.95)',
    'cloud_fill': 'rgba(50, 255, 150, 0.15)'
}

# Robinhood Color Scheme
RH_COLORS = {
    'green': '#00FF94',
    'red': '#FF2D55',
    'black': '#1E2124',
    'dark_gray': '#18191A',
    'light_gray': '#8C8C8E',
    'glow': 'rgba(0, 255, 148, 0.15)'
}

class AnimatedTradingDashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()

    def create_gauge_figure(self, value=0):
        angle = (value + 2) / 4 * 270 - 135
        fig = go.Figure()
        fig.add_trace(go.Pie(values=[1], rotation=135, hole=0.7,
            marker_colors=['rgba(255,255,255,0.1)'], showlegend=False,
            hoverinfo='skip', textinfo='none'))
        fig.add_trace(go.Pie(values=[abs(angle), 360 - abs(angle)],
            rotation=135 if angle >= 0 else -45, hole=0.7,
            marker_colors=[RH_COLORS['green'] if angle >= 0 else RH_COLORS['red'],
            'rgba(0,0,0,0)'], showlegend=False, hoverinfo='skip', textinfo='none'))
        fig.add_annotation(text='NEUTRAL', x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color='white'), xanchor='center', yanchor='middle')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0, l=0, r=0),
            width=300, height=300, showlegend=False)
        return fig

    def calculate_signal_strength(self, signals):
        signal_values = {
            'Strong Sell': -2, 'Sell': -1, 'Neutral': 0, 'Buy': 1, 'Strong Buy': 2
        }
        weights = {'RSI': 0.3, 'MACD': 0.4, 'BB': 0.3}
        total_strength = 0
        for signal in signals:
            total_strength += signal_values.get(signal['status'], 0) * weights[signal['name']]
        return total_strength

    def get_signal_color(self, strength):
        if strength <= -1.5:
            return RH_COLORS['red'], 'Strong Sell'
        elif strength <= -0.5:
            return RH_COLORS['red'], 'Sell'
        elif strength <= 0.5:
            return RH_COLORS['light_gray'], 'Neutral'
        elif strength <= 1.5:
            return RH_COLORS['green'], 'Buy'
        else:
            return RH_COLORS['green'], 'Strong Buy'

    def setup_layout(self):
        self.app.layout = html.Div(style={
            'backgroundColor': RH_COLORS['dark_gray'], 'minHeight': '100vh',
            'color': '#ffffff', 'fontFamily': '"Roboto", "Helvetica Neue", sans-serif'
        }, children=[
            html.Div(style={'backgroundColor': RH_COLORS['black'], 'padding': '20px',
                'marginBottom': '20px', 'borderBottom': '1px solid rgba(255,255,255,0.1)'
            }, children=[html.H1("Signal Dashboard",
                style={'margin': '0', 'color': '#ffffff'})]),
            html.Div(style={'padding': '20px'}, children=[
                html.Div(style={'backgroundColor': RH_COLORS['black'],
                    'padding': '20px', 'borderRadius': '8px', 'marginBottom': '20px',
                    'boxShadow': '0 4px 6px rgba(0,0,0,0.1)'
                }, children=[
                    html.H2("Signal Strength",
                        style={'textAlign': 'center', 'marginBottom': '20px'}),
                    dcc.Graph(id='signal-gauge', figure=self.create_gauge_figure(),
                        config={'displayModeBar': False},
                        style={'width': '300px', 'height': '300px', 'margin': '0 auto'}),
                    html.Div(id='signal-value', style={'textAlign': 'center',
                        'fontSize': '24px', 'fontWeight': 'bold', 'marginTop': '20px'})
                ]),
                dcc.Interval(id='interval-component', interval=1000, n_intervals=0)
            ])
        ])

    def setup_callbacks(self):
        @self.app.callback(
            [dash.Output('signal-gauge', 'figure'),
             dash.Output('signal-value', 'children'),
             dash.Output('signal-value', 'style')],
            [dash.Input('interval-component', 'n_intervals')])
        def update_signal_gauge(n):
            signals = [
                {'name': 'RSI', 'value': '65.4', 'status': 'Buy'},
                {'name': 'MACD', 'value': 'Bullish', 'status': 'Strong Buy'},
                {'name': 'BB', 'value': 'Upper Band', 'status': 'Buy'}
            ]
            strength = self.calculate_signal_strength(signals)
            color, status = self.get_signal_color(strength)
            gauge_figure = self.create_gauge_figure(strength)
            gauge_figure.update_layout(
                paper_bgcolor=RH_COLORS['black'],
                plot_bgcolor=RH_COLORS['black'])
            gauge_figure.update_annotations(dict(
                text=status.upper(),
                font=dict(color=color, size=24)))
            signal_style = {
                'color': color, 'fontSize': '24px', 'fontWeight': 'bold',
                'textAlign': 'center', 'textShadow': f'0 0 10px {color}50',
                'transition': 'all 0.3s ease'
            }
            return gauge_figure, status, signal_style

    def run(self, debug=True, port=8052):
        print(f"Starting dashboard on http://localhost:{port}")
        self.app.run(debug=debug, port=port)

if __name__ == '__main__':
    dashboard = AnimatedTradingDashboard()
    dashboard.run()
