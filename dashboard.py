import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

# =============================
# إعداد الصفحة
# =============================
st.set_page_config(page_title="📊 Market Dashboard", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TRADES_FILE = "trades.csv"

# =============================
# مؤشرات فنية
# =============================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# =============================
# TradingView Scanner
# =============================
def fetch_market(market):
    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "filter": [],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [
            "name", "description", "close", "change",
            "relative_volume_10d_calc", "price_earnings_ttm"
        ],
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 200]
    }

    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
    except:
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

# =============================
# إشارات أساسية
# =============================
def add_signals(df):
    if df.empty:
        return df

    df["قوة السهم"] = "🔴 ضعيف"
    df["إشارة"] = "❌ لا"

    strong = (df["Change %"] > 2) & (df["Relative Volume"] > 1.5)
    medium = (df["Change %"] > 1) | (df["Relative Volume"] > 1.2)

    df.loc[strong, "قوة السهم"] = "⭐ قوي"
    df.loc[medium & ~strong, "قوة السهم"] = "⚡ متوسط"

    df.loc[strong, "إشارة"] = "🔥 شراء"
    df.loc[medium & ~strong, "إشارة"] = "⚡ متابعة"

    return df

# =============================
# تحليل اختراق متقدم
# =============================
def detect_breakout(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 30:
            return None

        df["RSI"] = calculate_rsi(df["Close"])
        df["ATR"] = calculate_atr(df)

        last = df.iloc[-1]
        high_20 = df["High"].tail(20).max()
        avg_vol = df["Volume"].tail(20).mean()

        if last["Close"] <= high_20:
            return None

        score = 0
        if last["Volume"] > avg_vol * 2:
            score += 2
        if last["Volume"] > avg_vol * 3:
            score += 1
        if 60 <= last["RSI"] <= 70:
            score += 2
        if last["Close"] > high_20 * 1.01:
            score += 2

        if score >= 6:
            label = "🟢 اختراق حقيقي"
        elif score >= 4:
            label = "🟡 اختراق متوسط"
        else:
            label = "🔴 اختراق كاذب"

        entry = round(high_20 + last["ATR"] * 0.2, 2)
        stop = round(entry - last["ATR"], 2)
        target = round(entry + last["ATR"] * 2, 2)

        return {
            "Symbol": symbol,
            "Price": round(last["Close"], 2),
            "RSI": round(last["RSI"], 1),
            "ATR": round(last["ATR"], 2),
            "Entry": entry,
            "Stop": stop,
            "Target": target,
            "Score": score,
            "Type": label
        }
    except:
        return None

# =============================
# إدارة الصفقات
# =============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date", "Symbol", "Price", "Qty"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

# =============================
# الواجهة – التابات بالأعلى
# =============================
st.title("📊 Market Dashboard")

tabs = st.tabs([
    "فرص مضاربية",
    "أقوى الأسهم",
    "🚀 الاختراقات",
    "إدارة الصفقة",
    "تتبع الصفقات"
])

market = st.selectbox("اختر السوق", ["السعودي", "الأمريكي"])
df = fetch_market("ksa" if market == "السعودي" else "america")
df = add_signals(df)

# =============================
# تاب 1: فرص مضاربية
# =============================
with tabs[0]:
    st.dataframe(df, use_container_width=True)

# =============================
# تاب 2: أقوى الأسهم
# =============================
with tabs[1]:
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي", "⚡ متوسط"])]
    if strong_df.empty:
        st.info("لا توجد أسهم قوية حالياً")
    else:
        st.dataframe(strong_df, use_container_width=True)

# =============================
# تاب 3: الاختراقات + تنبيه
# =============================
with tabs[2]:
    results = []
    alert = 0

    for s in df["Symbol"].head(40):
        r = detect_breakout(s)
        if r:
            results.append(r)
            if r["Score"] >= 6:
                alert += 1

    bo_df = pd.DataFrame(results)

    if alert > 0:
        st.error(f"🚨 تنبيه: {alert} اختراق قوي الآن")

    if bo_df.empty:
        st.info("لا توجد اختراقات حالياً")
    else:
        st.dataframe(bo_df, use_container_width=True)

# =============================
# تاب 4: إدارة الصفقة
# =============================
with tabs[3]:
    sym = st.text_input("رمز السهم")
    buy_price = st.number_input("سعر الشراء", min_value=0.0, step=0.01)

    if st.button("تحليل"):
        try:
            price = yf.download(sym, period="1d", progress=False)["Close"][-1]
            pnl = (price - buy_price) / buy_price * 100
            st.write(f"السعر الحالي: {price:.2f}")
            if pnl >= 5:
                st.success("💰 يفضل جني أرباح جزئي")
            elif pnl <= -3:
                st.error("⛔ وقف خسارة")
            else:
                st.info("⏳ الاستمرار")
        except:
            st.error("تعذر جلب السهم")

# =============================
# تاب 5: تتبع الصفقات
# =============================
with tabs[4]:
    trades = load_trades()
    st.dataframe(trades, use_container_width=True)

    st.subheader("إضافة صفقة")
    s = st.text_input("رمز")
    p = st.number_input("سعر", min_value=0.0)
    q = st.number_input("الكمية", min_value=1)
    d = st.date_input("التاريخ", datetime.today())

    if st.button("حفظ"):
        trades = pd.concat([trades, pd.DataFrame([{
            "Date": d, "Symbol": s, "Price": p, "Qty": q
        }])])
        save_trades(trades)
        st.success("تم الحفظ")
