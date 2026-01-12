import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TRADES_FILE = "trades.csv"

# =============================
# جلب بيانات السوق
# =============================
def fetch_market(market):
    url = f"https://scanner.tradingview.com/{market}/scan"
    payload = {
        "filter": [],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": [
            "name", "description", "close", "change", "relative_volume_10d_calc", "price_earnings_ttm"
        ],
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 300]
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
    except:
        st.warning(f"⚠️ تعذر جلب سوق {market}")
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
# RSI حقيقي
# =============================
def calculate_rsi(symbol, period=14):
    try:
        data = yf.download(symbol, period="3mo")
        if data.empty:
            return None
        delta = data['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except:
        return None

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
    df["RSI"] = None
    df["Score"] = 0
    df["تصنيف"] = "مضاربة"

    for idx, row in df.iterrows():
        rsi = calculate_rsi(row["Symbol"])
        df.at[idx, "RSI"] = round(rsi,2) if rsi else None
        score = 0

        # قاعدة إشارات
        if row["Change %"] > 2:
            score += 2
        if row["Relative Volume"] > 1.5:
            score += 2
        if row["PE"] and row["PE"] < 30:
            score += 1
        if rsi and rsi < 30:
            score += 2
        elif rsi and rsi > 70:
            score -= 1

        df.at[idx, "Score"] = score

        # تصنيف الحالة
        if score >= 5:
            df.at[idx, "الحالة"] = "⭐ قوي للشراء"
            df.at[idx, "قوة السهم"] = "⭐ قوي"
            df.at[idx, "إشارة"] = "🔥 شراء"
            df.at[idx, "سعر الدخول"] = row["Price"] * 0.995  # Pullback
            df.at[idx, "جني الأرباح"] = (row["Price"] * 1.05).round(2)
            df.at[idx, "وقف الخسارة"] = (row["Price"] * 0.975).round(2)
            df.at[idx, "تصنيف"] = "سوينق"
        elif score >=3:
            df.at[idx, "الحالة"] = "⚡ فرصة محتملة"
            df.at[idx, "قوة السهم"] = "⚡ متوسط"
            df.at[idx, "إشارة"] = "⚡ متابعة"
            df.at[idx, "سعر الدخول"] = row["Price"]
            df.at[idx, "جني الأرباح"] = (row["Price"] * 1.03).round(2)
            df.at[idx, "وقف الخسارة"] = (row["Price"] * 0.985).round(2)

    return df

# =============================
# الفوليوم التاريخي
# =============================
def fetch_historical_volume(symbol, period="1mo"):
    try:
        data = yf.download(symbol, period=period)
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

# =============================
# اختيار السوق
# =============================
market_choice = st.selectbox("اختر السوق", ["السعودي", "الأمريكي"])
with st.spinner(f"جلب بيانات سوق {market_choice}..."):
    df = fetch_market("ksa") if market_choice=="السعودي" else fetch_market("america")
df = add_signals(df)

# =============================
# تاب فرص مضاربية
# =============================
with page[0]:
    st.subheader("فرص مضاربية")
    if df.empty:
        st.info("لا توجد بيانات حالياً")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        # تنبيه للفرص القوية
        strong_alerts = df[df["Score"]>=5]
        for _, row in strong_alerts.iterrows():
            st.success(f"🔔 فرصة قوية: {row['Symbol']} - {row['الحالة']} - Score: {row['Score']}")

# =============================
# تاب أقوى الأسهم
# =============================
with page[1]:
    st.subheader("أقوى الأسهم")
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي", "⚡ متوسط"])]
    if strong_df.empty:
        st.info("لا توجد أسهم قوية حالياً")
    else:
        st.dataframe(strong_df, use_container_width=True, hide_index=True)

# =============================
# تاب إدارة الصفقة
# =============================
with page[2]:
    st.subheader("إدارة الصفقة")
    symbol = st.text_input("رمز السهم")
    price_buy = st.number_input("سعر الشراء", min_value=0.0, step=0.01)
    if st.button("تحليل الصفقة"):
        if symbol and price_buy > 0:
            try:
                current_price = yf.download(symbol, period="1d")['Close'][-1]
                result = trade_analysis(price_buy, current_price)
                st.write(f"السعر الحالي: {current_price:.2f}")
                st.write(f"التوصية: {result}")
            except:
                st.error("❌ تعذر جلب بيانات السهم")

# =============================
# تاب تتبع الصفقات
# =============================
with page[3]:
    st.subheader("تتبع الصفقات")
    trades_df = load_trades()
    st.dataframe(trades_df, use_container_width=True, hide_index=True)

    st.write("أضف صفقة جديدة")
    symbol_new = st.text_input("رمز السهم جديد")
    price_new = st.number_input("سعر الشراء جديد", min_value=0.0, step=0.01)
    qty_new = st.number_input("عدد الأسهم", min_value=1, step=1)
    date_new = st.date_input("تاريخ الشراء", datetime.today())
    if st.button("حفظ الصفقة"):
        if symbol_new and price_new>0 and qty_new>0:
            new_trade = pd.DataFrame([{
                "Date": date_new, "Symbol": symbol_new, "Price": price_new, "Quantity": qty_new
            }])
            trades_df = pd.concat([trades_df, new_trade], ignore_index=True)
            save_trades(trades_df)
            st.success("تم حفظ الصفقة")

# =============================
# تاب أعلى الفوليوم
# =============================
with page[4]:
    st.subheader("أعلى الفوليوم")
    high_volume_stocks = []
    for _, row in df.iterrows():
        current_volume, avg_volume_20 = fetch_historical_volume(row["Symbol"])
        if current_volume and avg_volume_20 and current_volume > avg_volume_20:
            row_copy = row.copy()
            row_copy["الفوليوم الحالي"] = current_volume
            row_copy["متوسط 20 جلسة"] = round(avg_volume_20, 2)
            high_volume_stocks.append(row_copy)
    hv_df = pd.DataFrame(high_volume_stocks)
    if hv_df.empty:
        st.info("لا توجد أسهم بفوليوم أعلى من متوسط 20 جلسة حالياً")
    else:
        st.dataframe(hv_df, use_container_width=True, hide_index=True)
