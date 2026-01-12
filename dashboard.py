import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

# ملفات الأسهم لكل سوق (تحتوي فقط على الرموز)
MARKET_FILES = {
    "السوق السعودي": "saudi_symbols.csv",
    "السوق الأمريكي": "usa_symbols.csv"
}

TRADES_FILE = "trades.csv"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

# ===========================
# تحميل الرموز من CSV
# ===========================
def load_symbols(file):
    try:
        return pd.read_csv(file)
    except:
        st.warning(f"⚠️ لم يتم العثور على الملف: {file}")
        return pd.DataFrame(columns=["Symbol"])

# ===========================
# جلب بيانات الأسهم من النت
# ===========================
def fetch_market_data(symbols, market):
    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "filter": [],
        "symbols": {"query":{"types":[]},"tickers":symbols.tolist()},
        "columns":["name","description","close","change","relative_volume_10d_calc","price_earnings_ttm"],
        "range":[0, len(symbols)]
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
    except:
        st.warning("⚠️ تعذر جلب بيانات السوق من الإنترنت")
        return pd.DataFrame()

    rows = []
    for d in data:
        try:
            rows.append({
                "Symbol": d["s"],
                "Company": d["d"][1],
                "Price": float(d["d"][2]),
                "Change %": float(d["d"][3]),
                "Relative Volume": float(d["d"][4]),
                "PE": float(d["d"][5]) if d["d"][5] else None
            })
        except:
            continue
    return pd.DataFrame(rows)

# ===========================
# تحليل الأسهم
# ===========================
def add_signals(df):
    if df.empty:
        return df
    df["الحالة"] = "🟡 مراقبة"
    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None
    df["قوة السهم"] = "🔴 ضعيف"

    strong_buy = (df["Change %"]>2) & (df["Relative Volume"]>1.5)
    potential_buy = ((df["Change %"]>1) | (df["Relative Volume"]>1.2))

    df.loc[strong_buy, "الحالة"] = "⭐ قوي للشراء"
    df.loc[potential_buy & ~strong_buy, "الحالة"] = "⚡ فرصة محتملة"

    df.loc[strong_buy, "قوة السهم"] = "⭐ قوي"
    df.loc[potential_buy & ~strong_buy, "قوة السهم"] = "⚡ متوسط"

    df.loc[strong_buy, "إشارة"] = "🔥 شراء"
    df.loc[strong_buy, "سعر الدخول"] = df["Price"]
    df.loc[strong_buy, "جني الأرباح"] = (df["Price"]*1.05).round(2)
    df.loc[strong_buy, "وقف الخسارة"] = (df["Price"]*0.975).round(2)

    df.loc[potential_buy & ~strong_buy, "إشارة"] = "⚡ متابعة"
    df.loc[potential_buy & ~strong_buy, "سعر الدخول"] = df["Price"]
    df.loc[potential_buy & ~strong_buy, "جني الأرباح"] = (df["Price"]*1.03).round(2)
    df.loc[potential_buy & ~strong_buy, "وقف الخسارة"] = (df["Price"]*0.985).round(2)

    return df

# ===========================
# تحميل وتخزين الصفقات
# ===========================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

# ===========================
# واجهة المستخدم
# ===========================
st.title("📊 Market Dashboard")
tabs = st.tabs(["تحليل الأسهم","أقوى الأسهم","توصيات شراء","إدارة الصفقة","تدريب النظام"])

# اختيار السوق
market_choice = st.selectbox("اختر السوق", list(MARKET_FILES.keys()))
symbols_df = load_symbols(MARKET_FILES[market_choice])

if not symbols_df.empty:
    market_name = "ksa" if market_choice=="السوق السعودي" else "america"
    df = fetch_market_data(symbols_df["Symbol"], market_name)
    df = add_signals(df)
else:
    df = pd.DataFrame()

# باقي التابات تبقى مثل السابق
