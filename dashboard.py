import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
CSV_FILE = "stocks.csv"
TRADES_FILE = "trades.csv"

# =============================
# تحميل بيانات الأسهم من CSV
# =============================
def load_stocks():
    import os
    if not os.path.exists(CSV_FILE):
        st.warning(f"❌ لم يتم العثور على ملف {CSV_FILE}. سيتم استخدام بيانات اختبارية.")
        data = {
            "Symbol": ["AAPL","TSLA","AMZN","MSFT","NVDA"],
            "Company": ["Apple Inc.","Tesla Inc.","Amazon.com","Microsoft Corp","Nvidia Corp"],
            "Price": [170,700,130,310,420],
            "Change %": [1.2,2.5,0.8,1.5,3.0],
            "Relative Volume": [1.3,1.8,1.0,1.6,2.0],
            "PE": [28,50,60,35,45]
        }
        return pd.DataFrame(data)
    else:
        return pd.read_csv(CSV_FILE)

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
# حفظ ومتابعة الصفقات
# =============================
def load_trades():
    import os
    if os.path.exists(TRADES_FILE):
        return pd.read_csv(TRADES_FILE)
    else:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

# =============================
# واجهة المستخدم
# =============================
st.title("📊 Market Dashboard")
tabs = ["فرص مضاربية", "أقوى الأسهم", "إدارة الصفقة", "تتبع الصفقات", "أعلى الفوليوم"]
page = st.tabs(tabs)

# تحميل البيانات
df = load_stocks()
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
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي","⚡ متوسط"])]
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
    current_price = st.number_input("السعر الحالي", min_value=0.0, step=0.01)
    if st.button("تحليل الصفقة"):
        if symbol and price_buy>0 and current_price>0:
            result = trade_analysis(price_buy, current_price)
            st.write(f"التوصية: {result}")

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
    # حالياً مجرد عرض الفوليوم النسبي الموجود في CSV
    hv_df = df[df["Relative Volume"] > 1.5]  # مثال: أعلى من المتوسط 1.5
    if hv_df.empty:
        st.info("لا توجد أسهم بفوليوم مرتفع حالياً")
    else:
        st.dataframe(hv_df, use_container_width=True, hide_index=True)
