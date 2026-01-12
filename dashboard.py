import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TRADES_FILE = "trades.csv"
STOCKS_FILE = "stocks.csv"

# =============================
# جلب الأسهم من CSV + TradingView
# =============================
def fetch_market(market):
    try:
        symbols_df = pd.read_csv(STOCKS_FILE)
        tickers = symbols_df["Symbol"].dropna().unique().tolist()
    except:
        st.error("❌ تعذر قراءة ملف stocks.csv")
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
        data = r.json().get("data", [])
    except:
        st.warning("⚠️ تعذر جلب البيانات من TradingView")
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
# إشارات وحالة السهم
# =============================
def add_signals(df):
    if df.empty:
        return df

    df["الحالة"] = "🟡 مراقبة"
    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None
    df["قوة السهم"] = "🔴 ضعيف"

    strong_buy = (df["Change %"] > 2) & (df["Relative Volume"] > 1.5) & (df["PE"].fillna(100) < 30)
    potential_buy = ((df["Change %"] > 1) | (df["Relative Volume"] > 1.2)) & (df["PE"].fillna(100) < 50)

    df.loc[strong_buy, "الحالة"] = "⭐ قوي للشراء"
    df.loc[potential_buy & ~strong_buy, "الحالة"] = "⚡ فرصة محتملة"
    df.loc[df["Change %"] < 0, "الحالة"] = "🔴 ضعيف"

    df.loc[strong_buy, "قوة السهم"] = "⭐ قوي"
    df.loc[potential_buy & ~strong_buy, "قوة السهم"] = "⚡ متوسط"

    df.loc[strong_buy, "إشارة"] = "🔥 شراء"
    df.loc[strong_buy, "سعر الدخول"] = df["Price"]
    df.loc[strong_buy, "جني الأرباح"] = (df["Price"] * 1.05).round(2)
    df.loc[strong_buy, "وقف الخسارة"] = (df["Price"] * 0.975).round(2)

    df.loc[potential_buy & ~strong_buy, "إشارة"] = "⚡ متابعة"
    df.loc[potential_buy & ~strong_buy, "سعر الدخول"] = df["Price"]
    df.loc[potential_buy & ~strong_buy, "جني الأرباح"] = (df["Price"] * 1.03).round(2)
    df.loc[potential_buy & ~strong_buy, "وقف الخسارة"] = (df["Price"] * 0.985).round(2)

    return df

# =============================
# الفوليوم التاريخي (Yahoo فقط للفوليوم)
# =============================
def fetch_historical_volume(symbol, period="1mo"):
    try:
        yf_symbol = symbol.split(":")[-1]
        data = yf.download(yf_symbol, period=period)
        if data.empty:
            return None, None
        last_volume = data['Volume'].iloc[-1]
        avg_volume_20 = data['Volume'].tail(20).mean()
        return last_volume, avg_volume_20
    except:
        return None, None

# =============================
# إدارة الصفقة
# =============================
def trade_analysis(price_buy, current_price):
    gain_percent = (current_price - price_buy) / price_buy * 100
    if gain_percent >= 5:
        return "💰 يفضل بيع جزئي"
    elif gain_percent < -3:
        return "⚠️ وقف الخسارة / بيع"
    else:
        return "⏳ الاستمرار بالصفقة"

# =============================
# حفظ وتابع الصفقات
# =============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date", "Symbol", "Price", "Quantity"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

# =============================
# واجهة المستخدم
# =============================
st.title("📊 Market Dashboard")

tabs = ["فرص مضاربية", "أقوى الأسهم", "إدارة الصفقة", "تتبع الصفقات", "أعلى الفوليوم"]
page = st.tabs(tabs)

market_choice = st.selectbox("اختر السوق", ["السعودي", "الأمريكي"])
with st.spinner("جلب البيانات..."):
    df = fetch_market("ksa") if market_choice == "السعودي" else fetch_market("america")

df = add_signals(df)

# =============================
# فرص مضاربية
# =============================
with page[0]:
    st.subheader("فرص مضاربية")
    st.dataframe(df, use_container_width=True, hide_index=True)

# =============================
# أقوى الأسهم
# =============================
with page[1]:
    st.subheader("أقوى الأسهم")
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي", "⚡ متوسط"])]
    st.dataframe(strong_df, use_container_width=True, hide_index=True)

# =============================
# إدارة الصفقة
# =============================
with page[2]:
    st.subheader("إدارة الصفقة")
   symbol = st.text_input("رمز السهم (EXCHANGE:SYMBOL)", key="trade_symbol")
price_buy = st.number_input("سعر الشراء", min_value=0.0, step=0.01, key="trade_price")

    if st.button("تحليل الصفقة"):
        try:
            yf_symbol = symbol.split(":")[-1]
            current_price = yf.download(yf_symbol, period="1d")['Close'][-1]
            st.write(f"السعر الحالي: {current_price:.2f}")
            st.write(f"التوصية: {trade_analysis(price_buy, current_price)}")
        except:
            st.error("❌ تعذر جلب السعر الحالي")

# =============================
# تتبع الصفقات
# =============================
with page[3]:
    st.subheader("تتبع الصفقات")
    trades_df = load_trades()
    st.dataframe(trades_df, use_container_width=True, hide_index=True)

    st.write("إضافة صفقة جديدة")
   symbol_new = st.text_input("رمز السهم", key="new_trade_symbol")
price_new = st.number_input("سعر الشراء", min_value=0.0, step=0.01, key="new_trade_price")
qty_new = st.number_input("عدد الأسهم", min_value=1, key="new_trade_qty")

    date_new = st.date_input("تاريخ الشراء", datetime.today())

    if st.button("حفظ الصفقة"):
        new_trade = pd.DataFrame([{
            "Date": date_new,
            "Symbol": symbol_new,
            "Price": price_new,
            "Quantity": qty_new
        }])
        save_trades(pd.concat([trades_df, new_trade], ignore_index=True))
        st.success("✅ تم حفظ الصفقة")

# =============================
# أعلى الفوليوم
# =============================
with page[4]:
    st.subheader("أعلى الفوليوم")
    high_volume = []
    for _, row in df.iterrows():
        cur, avg = fetch_historical_volume(row["Symbol"])
        if cur and avg and cur > avg:
            r = row.copy()
            r["الفوليوم الحالي"] = cur
            r["متوسط 20 جلسة"] = round(avg, 2)
            high_volume.append(r)

    hv_df = pd.DataFrame(high_volume)
    st.dataframe(hv_df, use_container_width=True, hide_index=True)
