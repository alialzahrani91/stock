import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="Market Dashboard", layout="wide")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json"
}

# =============================
# دالة جلب السوق
# =============================
def fetch_market(market):
    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "filter": [],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "description", "close", "change", "relative_volume_10d_calc"],
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 300]
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except requests.exceptions.RequestException:
        st.warning(f"⚠️ تعذر جلب سوق {market}")
        return pd.DataFrame()

    data = r.json().get("data", [])
    rows = []
    for d in data:
        rows.append({
            "Symbol": d["s"],
            "Company": d["d"][1],
            "Price": d["d"][2],
            "Change %": d["d"][3],
            "Relative Volume": d["d"][4]
        })
    return pd.DataFrame(rows)

# =============================
# دالة حساب RSI بسيطة
# =============================
def compute_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-6)
    rsi = 100 - (100 / (1 + rs))
    return rsi

# =============================
# دالة إضافة إشارات التداول
# =============================
def add_signals(df):
    if df.empty:
        return df

    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None
    df["قوة السهم"] = "🔴 ضعيف"

    # إضافة RSI وهمي بناءً على السعر الحالي للتجربة
    df["RSI"] = compute_rsi(df["Price"].astype(float).cumsum())  # استخدام cumsum لمحاكاة تغير السعر

    # شروط الشراء: تغيير سعر + حجم تداول + RSI منخفض
    buy = (df["Change %"] > 1.5) & (df["Relative Volume"] > 1.2) & (df["RSI"] < 40)

    df.loc[buy, "إشارة"] = "🔥 شراء"
    df.loc[buy, "سعر الدخول"] = (df["Price"] * 0.998).round(2)  # الدخول عند سعر أقل قليلاً
    df.loc[buy, "جني الأرباح"] = (df["Price"] * 1.05).round(2)
    df.loc[buy, "وقف الخسارة"] = (df["Price"] * 0.975).round(2)
    df.loc[buy, "قوة السهم"] = "⭐ قوي"

    return df

# =============================
# واجهة المستخدم
# =============================
st.title("📊 Dashboard الفرص المضاربية")

# اختيار السوق
market_choice = st.selectbox("اختر السوق:", ["السوق السعودي", "السوق الأمريكي"])

with st.spinner(f"جلب بيانات {market_choice}..."):
    if market_choice == "السوق السعودي":
        df = fetch_market("ksa")
    else:
        df = fetch_market("america")

df = add_signals(df)

if df.empty:
    st.error("❌ لم يتم جلب أي بيانات من TradingView")
    st.stop()

st.success(f"تم تحميل {len(df)} سهم")
st.dataframe(df, use_container_width=True, hide_index=True)
