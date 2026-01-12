import streamlit as st
import requests
import pandas as pd
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

    for idx, row in df.iterrows():
        if strong_buy.get(idx, False):
            df.at[idx, "الحالة"] = "⭐ قوي للشراء"
            df.at[idx, "قوة السهم"] = "⭐ قوي"
            df.at[idx, "إشارة"] = "🔥 شراء"
            df.at[idx, "سعر الدخول"] = row["Price"]
            df.at[idx, "جني الأرباح"] = round(row["Price"] * 1.05, 2)
            df.at[idx, "وقف الخسارة"] = round(row["Price"] * 0.975, 2)
        elif potential_buy.get(idx, False):
            df.at[idx, "الحالة"] = "⚡ فرصة محتملة"
            df.at[idx, "قوة السهم"] = "⚡ متوسط"
            df.at[idx, "إشارة"] = "⚡ متابعة"
            df.at[idx, "سعر الدخول"] = row["Price"]
            df.at[idx, "جني الأرباح"] = round(row["Price"] * 1.03, 2)
            df.at[idx, "وقف الخسارة"] = round(row["Price"] * 0.985, 2)
        elif row["Change %"] < 0:
            df.at[idx, "الحالة"] = "🔴 ضعيف"

    return df

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
    current_price = st.number_input("السعر الحالي للسهم (اختياري)", min_value=0.0, step=0.01)
    if st.button("تحليل الصفقة"):
        if symbol and price_buy > 0 and current_price > 0:
            result = trade_analysis(price_buy, current_price)
            st.write(f"السعر الحالي: {current_price:.2f}")
            st.write(f"التوصية: {result}")
        else:
            st.error("❌ يرجى إدخال السعر الحالي والشراء")

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
    st.info("الميزة هذه ستحتاج الربط بمصدر الفوليوم التاريخي من TradingView أو Excel")
