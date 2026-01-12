import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TRADES_FILE = "trades.csv"
EXCEL_FILE = "stocks.xlsx"  # ملف الأسهم الأساسي

# =============================
# 1️⃣ جلب البيانات الأولية من Excel
# =============================
def load_stocks():
    try:
        df = pd.read_excel(EXCEL_FILE)
        return df
    except FileNotFoundError:
        st.error(f"❌ لم يتم العثور على ملف {EXCEL_FILE}")
        return pd.DataFrame()
        
# =============================
# 2️⃣ تحليل الأسهم وجلب التوصيات من الإنترنت
# =============================
def fetch_recommendations(symbol):
    """مثال: جلب توصيات من TradingView API"""
    try:
        url = f"https://scanner.tradingview.com/america/scan"  # مثال للسوق الأمريكي
        payload = {
            "filter": [{"left": "name", "operation": "equal", "right": symbol}],
            "columns": ["RSI", "close", "change", "relative_volume_10d_calc"]
        }
        r = requests.post(url, json=payload, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        return data[0]["d"]  # بيانات أول صف
    except:
        return None

def add_signals(df):
    """إضافة إشارات علمية وحالة السهم"""
    if df.empty:
        return df
    
    df["الحالة"] = "🟡 مراقبة"
    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None
    df["قوة السهم"] = "🔴 ضعيف"
    
    for idx, row in df.iterrows():
        rsi = fetch_recommendations(row["Symbol"])
        # مثال حساب إشارات بناءً على البيانات
        if rsi:
            rsi_val = float(rsi[0])  # افتراض RSI في أول عمود
            if rsi_val < 30:
                df.at[idx, "إشارة"] = "🔥 شراء"
                df.at[idx, "سعر الدخول"] = row["Price"]
                df.at[idx, "جني الأرباح"] = round(row["Price"] * 1.05, 2)
                df.at[idx, "وقف الخسارة"] = round(row["Price"] * 0.975, 2)
                df.at[idx, "قوة السهم"] = "⭐ قوي"
                df.at[idx, "الحالة"] = "⭐ فرصة قوية"
            elif rsi_val < 50:
                df.at[idx, "إشارة"] = "⚡ متابعة"
                df.at[idx, "سعر الدخول"] = row["Price"]
                df.at[idx, "جني الأرباح"] = round(row["Price"] * 1.03, 2)
                df.at[idx, "وقف الخسارة"] = round(row["Price"] * 0.985, 2)
                df.at[idx, "قوة السهم"] = "⚡ متوسط"
                df.at[idx, "الحالة"] = "⚡ فرصة محتملة"
    return df

# =============================
# 3️⃣ إدارة وتدريب الصفقات
# =============================
def trade_analysis(price_buy, current_price):
    gain_percent = (current_price - price_buy) / price_buy * 100
    if gain_percent >= 5:
        return "💰 يفضل بيع جزئي"
    elif gain_percent <= -3:
        return "⚠️ وقف الخسارة / بيع"
    else:
        return "⏳ الاستمرار بالصفقة"

def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

# =============================
# 4️⃣ واجهة المستخدم - Tabs
# =============================
st.title("📊 Market Dashboard")
tabs = st.tabs(["فرص مضاربية", "أقوى الأسهم", "إدارة الصفقة", "تتبع الصفقات"])

# =============================
# تاب فرص مضاربية
# =============================
with tabs[0]:
    st.subheader("فرص مضاربية")
    df = load_stocks()
    df = add_signals(df)
    if df.empty:
        st.info("لا توجد بيانات حالياً")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

# =============================
# تاب أقوى الأسهم
# =============================
with tabs[1]:
    st.subheader("أقوى الأسهم")
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي","⚡ متوسط"])]
    if strong_df.empty:
        st.info("لا توجد أسهم قوية حالياً")
    else:
        st.dataframe(strong_df, use_container_width=True, hide_index=True)

# =============================
# تاب إدارة الصفقة
# =============================
with tabs[2]:
    st.subheader("إدارة الصفقة")
    symbol = st.text_input("رمز السهم")
    price_buy = st.number_input("سعر الشراء", min_value=0.0, step=0.01)
    current_price = st.number_input("السعر الحالي", min_value=0.0, step=0.01)
    if st.button("تحليل الصفقة"):
        if symbol and price_buy>0 and current_price>0:
            result = trade_analysis(price_buy, current_price)
            st.write(f"التوصية: {result}")

# =============================
# تاب تتبع الصفقات
# =============================
with tabs[3]:
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
