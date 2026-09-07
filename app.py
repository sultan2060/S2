import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

st.set_page_config(
    page_title="S2 Quantitative Terminal",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    header {visibility: hidden !important; display: none !important;}
    [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
    .stAppDeployButton {display: none !important; visibility: hidden !important;}
    div[class*="viewerBadge"] {display: none !important; visibility: hidden !important;}
    
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; }
    .block-container { padding: 0.6rem !important; }

    .disclaimer-bar {
        background-color: #161b22;
        border-right: 3px solid #d29922;
        color: #8b949e;
        font-size: 11px;
        padding: 5px 8px;
        border-radius: 4px;
        margin-bottom: 8px;
        direction: rtl;
        text-align: center;
    }

    .signal-header {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        margin-bottom: 8px;
    }
    .signal-call { border-right: 4px solid #2ea043; }
    .signal-put { border-right: 4px solid #da3633; }

    .targets-container {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 6px;
        margin-bottom: 8px;
    }
    .target-card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 6px;
        text-align: center;
    }
    .t-label { font-size: 10px; color: #8b949e; font-weight: bold; }
    .t-val { font-size: 13px; color: #58a6ff; font-weight: bold; margin: 2px 0; }
    .t-time { font-size: 9px; color: #3fb950; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="disclaimer-bar">تحليل تجريبي للمحفظة التجريبية لغرض التعلم وليست توصية استثمارية او مالية</div>', unsafe_allow_html=True)

# واجهة اختيار الأسهم والفريمات مباشرة في الشاشة الرئيسية (بدون قائمة جانبية)
col1, col2 = st.columns(2)

with col1:
    stocks_list = {
        "MU": "MU",
        "TSLA": "TSLA",
        "CROWD": "CRWD",
        "SPX (S&P 500)": "^GSPC",
        "NVDA": "NVDA",
        "AAPL": "AAPL",
        "MSFT": "MSFT",
        "AMZN": "AMZN",
        "META": "META",
        "GOOGL": "GOOGL",
        "AMD": "AMD",
        "NDX (Nasdaq)": "^IXIC",
        "BTC": "BTC-USD"
    }
    selected_stock = st.selectbox("اختر السهم", list(stocks_list.keys()))
    stock_symbol = stocks_list[selected_stock]

with col2:
    timeframe_config = {
        "3 دقائق": {"interval": "3m", "days": 5, "mins": 3},
        "5 دقائق": {"interval": "5m", "days": 7, "mins": 5},
        "10 دقائق": {"interval": "10m", "days": 10, "mins": 10},
        "15 دقيقة": {"interval": "15m", "days": 15, "mins": 15},
        "30 دقيقة": {"interval": "30m", "days": 30, "mins": 30},
        "45 دقيقة": {"interval": "45m", "days": 30, "mins": 45},
        "ساعة": {"interval": "1h", "days": 45, "mins": 60},
        "ساعتان": {"interval": "90m", "days": 60, "mins": 120},
        "4 ساعات": {"interval": "1h", "days": 60, "mins": 240},
        "8 ساعات": {"interval": "1h", "days": 60, "mins": 480},
        "يوم": {"interval": "1d", "days": 365, "mins": 1440},
        "أسبوعي": {"interval": "1wk", "days": 730, "mins": 10080},
        "شهري": {"interval": "1mo", "days": 1825, "mins": 43200}
    }
    selected_tf = st.selectbox("الفريم الزمني", list(timeframe_config.keys()), index=3)
    tf_info = timeframe_config[selected_tf]

@st.cache_data(ttl=15)
def load_data(symbol, interval, days):
    end_d = datetime.now()
    start_d = end_d - timedelta(days=days)
    try:
        df = yf.download(symbol, start=start_d, end=end_d, interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.dropna()
    except Exception:
        return pd.DataFrame()

df = load_data(stock_symbol, tf_info['interval'], tf_info['days'])

def analyze_pattern(df):
    if len(df) < 25:
        return "WAIT", 0, 0, 0
    
    lookback = 15
    df_sub = df.iloc[-lookback-3:-3]
    swing_low = df_sub['Low'].min()
    swing_high = df_sub['High'].max()
    
    c3, c2, c1 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    
    is_green = lambda c: c['Close'] > c['Open']
    is_red = lambda c: c['Close'] < c['Open']
    
    call_pattern = (
        (df.iloc[-4]['Low'] <= swing_low or c3['Low'] <= swing_low) and
        is_green(c2) and (c2['Close'] > swing_low) and
        is_red(c1)
    )
    
    put_pattern = (
        (c3['High'] >= swing_high) and
        is_red(c2) and
        is_green(c1) and (c1['High'] >= swing_high)
    )
    
    ep = float(c1['Close'])
    
    df['TR'] = np.maximum(df['High'] - df['Low'], np.abs(df['High'] - df['Close'].shift(1)))
    atr = float(df['TR'].rolling(14).mean().iloc[-1])
    if np.isnan(atr) or atr == 0: atr = ep * 0.005
    
    if call_pattern:
        sl = min(float(c1['Low']), float(c2['Low'])) - (atr * 0.2)
        return "CALL", ep, sl, atr
    elif put_pattern:
        sl = max(float(c1['High']), float(c2['High'])) + (atr * 0.2)
        return "PUT", ep, sl, atr
    else:
        is_bull = ep >= float(c1['Open'])
        sl = ep - (atr * 1.5) if is_bull else ep + (atr * 1.5)
        return ("CALL (جاهز)" if is_bull else "PUT (جاهز)"), ep, sl, atr

if not df.empty:
    signal, ep, sl, atr = analyze_pattern(df)
    
    is_bull = "CALL" in signal
    direction = "CALL 🟢" if is_bull else "PUT 🔴"
    card_style = "signal-call" if is_bull else "signal-put"
    
    st.markdown(f"""<div class="signal-header {card_style}">
<span style="font-size:11px; color:#8b949e;">{selected_stock} [{selected_tf}]</span> | 
<b style="font-size:15px;">{direction}</b> | 
<span style="font-size:12px;">EP: <b>${ep:.2f}</b></span> | 
<span style="font-size:12px; color:#f85149;">SL: <b>${sl:.2f}</b></span>
</div>""", unsafe_allow_html=True)
    
    targets_html = '<div class="targets-container">'
    risk = abs(ep - sl)
    for i in range(1, 5):
        tp = ep + (risk * i) if is_bull else ep - (risk * i)
        dist = abs(tp - ep)
        est_bars = max(1, int(dist / (atr * 0.75)))
        est_mins = est_bars * tf_info['mins']
        
        if est_mins < 60:
            time_txt = f"~{est_mins}m"
        elif est_mins < 1440:
            time_txt = f"~{round(est_mins/60, 1)}h"
        else:
            time_txt = f"~{round(est_mins/1440, 1)}d"
            
        targets_html += f'<div class="target-card"><div class="t-label">Target {i}</div><div class="t-val">${tp:.2f}</div><div class="t-time">⏱️ {time_txt}</div></div>'
    targets_html += '</div>'
    st.markdown(targets_html, unsafe_allow_html=True)

    df_chart = df.tail(50).copy()
    df_chart['DateStr'] = df_chart.index.strftime('%m-%d %H:%M')

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df_chart['DateStr'],
        open=df_chart['Open'], high=df_chart['High'],
        low=df_chart['Low'], close=df_chart['Close'], name="السعر"
    ))
    
    fig.add_hline(y=sl, line_dash="dash", line_color="#f85149", annotation_text="SL")
    for i in range(1, 5):
        tp = ep + (risk * i) if is_bull else ep - (risk * i)
        fig.add_hline(y=tp, line_dash="dot", line_color="#3fb950" if is_bull else "#f85149")

    fig.update_xaxes(type='category', nticks=5, showgrid=True, gridcolor='#21262d')
    fig.update_yaxes(showgrid=True, gridcolor='#21262d')
    fig.update_layout(
        template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False, paper_bgcolor="#0d1117", plot_bgcolor="#0d1117", showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.warning("جاري جلب البيانات أو أن الفريم المختار لا يحتوي على بيانات كافية حالياً.")
