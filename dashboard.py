import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# =============================
# Config
# =============================
st.set_page_config(page_title="Market Dashboard", layout="wide")
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
STOCKS_FILE = "stocks.csv"
TRADES_FILE = "trades.csv"

# =============================
# Data Layer
# =============================
def load_watchlist():
    try:
        return pd.read_csv(STOCKS_FILE)["Symbol"].dropna().unique().tolist()
    except:
        st.error("❌ خطأ في قراءة ملف stocks.csv")
        return []

def fetch_tradingview_data(market, tickers):
    if not tickers:
        return pd.DataFrame()

    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "filter": [],
        "symbols": {"tickers": tickers},
        "columns": [
            "name",
            "description",
            "close",
            "change",
            "relative_volume_10d_calc",
            "price_earnings_ttm"
        ]
    }

    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        raw = r.json().get("data", [])
    except:
        st.warning("⚠️ فشل الاتصال بـ TradingView")
        return pd.DataFrame()

    rows = []
    for item in raw:
        try:
            rows.append({
                "Symbol": item["s"],
                "Company": item["d"][1],
                "Price": float(item["d"][2]),
                "Change %": float(item["d"][3]),
                "Relative Volume": float(item["d"][4]),
                "PE": float(item["d"][5]) if item["d"][5] else None
            })
        except:
            continue
    return pd.DataFrame(rows)

def fetch_tv_price(symbol, market):
    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "symbols": {"tickers": [symbol]},
        "columns": ["close", "change"]
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None, None
        return data[0]["d"][0], data[0]["d"][1]
    except:
        return None, None

# =============================
# Business Logic
# =============================
def add_signals(df):
    if df.empty:
        return df
    df = df.copy()
    df["الحالة"] = "🟡 مراقبة"
    df["قوة السهم"] = "🔴 ضعيف"
    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None

    strong = (df["Change %"] > 2) & (df["Relative Volume"] > 1.5) & (df["PE"].fillna(100) < 30)
    medium = (df["Change %"] > 1) & (df["Relative Volume"] > 1.2)

    df.loc[strong, ["الحالة", "قوة السهم", "إشارة"]] = ["⭐ قوي للشراء", "⭐ قوي", "🔥 شراء"]
    df.loc[medium & ~strong, ["الحالة", "قوة السهم", "إشارة"]] = ["⚡ فرصة محتملة", "⚡ متوسط", "⚡ متابعة"]

    df.loc[strong, "سعر الدخول"] = df["Price"]
    df.loc[strong, "جني الأرباح"] = (df["Price"] * 1.05).round(2)
    df.loc[strong, "وقف الخسارة"] = (df["Price"] * 0.975).round(2)
    return df

def trade_decision(buy, current):
    p = (current - buy) / buy * 100
    if p >= 5:
        return "💰 بيع جزئي"
    if p <= -3:
        return "⛔ وقف خسارة"
    return "⏳ استمرار"

# =============================
# Trades Storage
# =============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date", "Symbol", "Price", "Quantity"])

def save_trade(trades, trade):
    trades = pd.concat([trades, trade], ignore_index=True)
    trades.to_csv(TRADES_FILE, index=False)
    return trades

# =============================
# UI
# =============================
st.title("📊 Market Dashboard")
tabs = st.tabs([
    "📈 فرص مضاربية",
    "⭐ أقوى الأسهم",
    "🧮 إدارة الصفقة",
    "📋 تتبع الصفقات",
    "📊 أعلى الفوليوم"
])

# --- Market Selection
market = st.selectbox("اختر السوق", ["السعودي", "الأمريكي"], key="market")
market_code = "ksa" if market == "السعودي" else "america"

# --- Load Data
tickers = load_watchlist()
df = fetch_tradingview_data(market_code, tickers)
df = add_signals(df)

# --- Tab 1: Opportunities
with tabs[0]:
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- Tab 2: Strong Stocks
with tabs[1]:
    st.dataframe(df[df["قوة السهم"] != "🔴 ضعيف"], use_container_width=True, hide_index=True)

# --- Tab 3: Trade Management
with tabs[2]:
    st.subheader("إدارة الصفقة")
    symbol = st.text_input("رمز السهم (TradingView)", placeholder="TADAWUL:4300", key="trade_symbol")
    buy_price = st.number_input("سعر الشراء", min_value=0.0, step=0.01, key="trade_price")

    if st.button("تحليل الصفقة", key="trade_analyze"):
        if not symbol or buy_price <= 0:
            st.warning("أدخل الرمز وسعر الشراء")
        else:
            price, change = fetch_tv_price(symbol, market_code)
            if price is None:
                st.error("❌ تعذر جلب بيانات السهم من TradingView")
            else:
                decision = trade_decision(buy_price, price)
                st.success(f"السعر الحالي: {price:.2f}")
                st.info(f"التغير اليومي: {change:.2f}%")
                st.write(f"📌 التوصية: **{decision}**")

# --- Tab 4: Track Trades
with tabs[3]:
    trades = load_trades()
    st.dataframe(trades, use_container_width=True, hide_index=True)

    with st.expander("➕ إضافة صفقة"):
        s = st.text_input("رمز السهم", key="new_symbol")
        p = st.number_input("سعر الشراء", min_value=0.0, step=0.01, key="new_price")
        q = st.number_input("الكمية", min_value=1, key="new_qty")
        d = st.date_input("التاريخ", datetime.today(), key="new_date")
        if st.button("حفظ الصفقة"):
            trade = pd.DataFrame([{"Date": d, "Symbol": s, "Price": p, "Quantity": q}])
            trades = save_trade(trades, trade)
            st.success("✅ تم الحفظ")

# --- Tab 5: High Volume
with tabs[4]:
    volume_rows = []
    for _, r in df.iterrows():
        try:
            url = f"https://scanner.tradingview.com/{market_code}/scan"
            payload = {"symbols": {"tickers": [r['Symbol']]}, "columns": ["relative_volume_10d_calc"]}
            res = requests.post(url, json=payload, headers=HEADERS, timeout=10).json().get("data", [])
            if res:
                current_volume = float(res[0]["d"][0])
                if current_volume > 1:  # فوق المتوسط
                    row_copy = r.copy()
                    row_copy["Relative Volume Today"] = current_volume
                    volume_rows.append(row_copy)
        except:
            continue
    st.dataframe(pd.DataFrame(volume_rows), use_container_width=True, hide_index=True)
