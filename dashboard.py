import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="📊 Market Dashboard", layout="wide")

# ==============================
# إعدادات الملفات لكل سوق
# ==============================
MARKET_FILES = {
    "السعودي": "ksa_symbols.csv",
    "الأمريكي": "usa_symbols.csv"
}

TRADES_FILE = "trades.csv"
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

# ==============================
# دالة لجلب بيانات الأسهم من الإنترنت
# ==============================
def fetch_stock_data(symbol):
    """
    جلب البيانات الأساسية من TradingView API أو أي مصدر متاح
    """
    url = "https://scanner.tradingview.com/america/scan"  # مثال للسوق الأمريكي
    payload = {
        "filter":[{"left":"name","operation":"equal","right":symbol}],
        "symbols":{"query":{"types":[]},"tickers":[]},
        "columns":["close","change","relative_volume_10d_calc","price_earnings_ttm"]
    }
    try:
        r = requests.post(url,json=payload,headers=HEADERS,timeout=10)
        data = r.json().get("data",[])
        if not data:
            return {"Price": None, "Change %": None, "Relative Volume": None, "PE": None}
        d = data[0]["d"]
        return {
            "Price": float(d[0]),
            "Change %": float(d[1]),
            "Relative Volume": float(d[2]),
            "PE": float(d[3]) if d[3] else None
        }
    except:
        return {"Price": None, "Change %": None, "Relative Volume": None, "PE": None}

# ==============================
# تحميل الرموز من ملف CSV
# ==============================
def load_symbols(market):
    try:
        df = pd.read_csv(MARKET_FILES[market])
        df = df.rename(columns={df.columns[0]: "Symbol"})
        return df
    except:
        st.error(f"❌ لم يتم العثور على ملف الأسهم للسوق {market}")
        return pd.DataFrame(columns=["Symbol"])

# ==============================
# تحليل الأسهم
# ==============================
def analyze_stocks(df):
    if df.empty:
        return df
    df["Price"] = None
    df["Change %"] = None
    df["Relative Volume"] = None
    df["PE"] = None

    # جلب البيانات لكل سهم
    for idx, row in df.iterrows():
        data = fetch_stock_data(row["Symbol"])
        df.at[idx, "Price"] = data["Price"]
        df.at[idx, "Change %"] = data["Change %"]
        df.at[idx, "Relative Volume"] = data["Relative Volume"]
        df.at[idx, "PE"] = data["PE"]

    # تصنيف الأسهم
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

# ==============================
# حفظ وتابع الصفقات
# ==============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity","Action"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

# ==============================
# واجهة المستخدم
# ==============================
st.title("📊 Market Dashboard")

market_choice = st.selectbox("اختر السوق", list(MARKET_FILES.keys()))
symbols_df = load_symbols(market_choice)
df = analyze_stocks(symbols_df)

tabs = st.tabs(["تحليل الأسهم","أقوى الأسهم","توصيات شراء","إدارة الصفقات","تدريب النظام"])

# ==============================
# تاب تحليل الأسهم
# ==============================
with tabs[0]:
    st.subheader("تحليل جميع الأسهم")
    if df.empty:
        st.info("لا توجد بيانات")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

# ==============================
# تاب أقوى الأسهم
# ==============================
with tabs[1]:
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي","⚡ متوسط"])]
    st.subheader("أقوى الأسهم")
    if strong_df.empty:
        st.info("لا توجد أسهم قوية")
    else:
        st.dataframe(strong_df, use_container_width=True, hide_index=True)

# ==============================
# تاب توصيات شراء
# ==============================
with tabs[2]:
    buy_df = df[df["إشارة"]=="🔥 شراء"]
    st.subheader("توصيات شراء")
    if buy_df.empty:
        st.info("لا توجد توصيات شراء حالياً")
    else:
        st.dataframe(buy_df, use_container_width=True, hide_index=True)

# ==============================
# تاب إدارة الصفقات
# ==============================
with tabs[3]:
    st.subheader("إدارة الصفقات")
    trades_df = load_trades()
    st.dataframe(trades_df, use_container_width=True, hide_index=True)

    st.write("أضف صفقة جديدة")
    symbol_new = st.text_input("رمز السهم")
    price_new = st.number_input("سعر الشراء", min_value=0.0, step=0.01)
    qty_new = st.number_input("عدد الأسهم", min_value=1, step=1)
    date_new = st.date_input("تاريخ الشراء", datetime.today())
    action_new = st.selectbox("نوع العملية", ["شراء","بيع"])

    if st.button("حفظ الصفقة"):
        if symbol_new and price_new>0 and qty_new>0:
            new_trade = pd.DataFrame([{
                "Date": date_new,
                "Symbol": symbol_new,
                "Price": price_new,
                "Quantity": qty_new,
                "Action": action_new
            }])
            trades_df = pd.concat([trades_df,new_trade],ignore_index=True)
            save_trades(trades_df)
            st.success("تم حفظ الصفقة")

# ==============================
# تاب تدريب النظام
# ==============================
with tabs[4]:
    st.subheader("تدريب النظام على الصفقات")
    trades_df = load_trades()
    st.write("بيانات الصفقات السابقة")
    st.dataframe(trades_df, use_container_width=True)
