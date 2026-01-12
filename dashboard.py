import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

# ==============================
# ملفات الأسواق (CSV) – كل ملف يحتوي عمود Symbol فقط
# ==============================
MARKET_FILES = {
    "السوق السعودي": "ksa_stocks.csv",
    "السوق الأمريكي": "usa_stocks.csv"
}

TRADES_FILE = "trades.csv"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ==============================
# جلب سعر السهم الحالي من API مجاني (Yahoo Finance)
# ==============================
def fetch_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        price = data['quoteResponse']['result'][0]['regularMarketPrice']
        return float(price)
    except:
        return None

# ==============================
# تحميل الأسهم من CSV
# ==============================
def load_stocks(market_choice):
    try:
        df = pd.read_csv(MARKET_FILES[market_choice])
        return df
    except FileNotFoundError:
        st.error(f"❌ لم يتم العثور على ملف الأسهم للسوق: {market_choice}")
        return pd.DataFrame(columns=["Symbol"])

# ==============================
# تحليل الأسهم
# ==============================
def analyze_stocks(df):
    if df.empty:
        return df

    # جلب الأسعار مباشرة
    df["Price"] = df["Symbol"].apply(fetch_price)
    df = df.dropna(subset=["Price"])  # إزالة الأسهم التي لم تُجلب

    # تحويل الأعمدة إلى أرقام (ضروري لأي حساب لاحق)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Change %"] = pd.Series([0]*len(df))          # مثال، لاحقًا يمكن جلب التغير اليومي
    df["Relative Volume"] = pd.Series([1]*len(df))   # مثال

    # أعمدة التحليل
    df["الحالة"] = "🟡 مراقبة"
    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None
    df["قوة السهم"] = "🔴 ضعيف"

    # شروط الشراء
    strong_buy = (df["Change %"] > 2) & (df["Relative Volume"] > 1.5)
    potential_buy = ((df["Change %"] > 1) | (df["Relative Volume"] > 1.2)) & (~strong_buy)

    # تعيين الحالات
    df.loc[strong_buy, "الحالة"] = "⭐ قوي للشراء"
    df.loc[strong_buy, "قوة السهم"] = "⭐ قوي"
    df.loc[strong_buy, "إشارة"] = "🔥 شراء"
    df.loc[strong_buy, "سعر الدخول"] = df["Price"]
    df.loc[strong_buy, "جني الأرباح"] = (df["Price"] * 1.05).round(2)
    df.loc[strong_buy, "وقف الخسارة"] = (df["Price"] * 0.975).round(2)

    df.loc[potential_buy, "الحالة"] = "⚡ فرصة محتملة"
    df.loc[potential_buy, "قوة السهم"] = "⚡ متوسط"
    df.loc[potential_buy, "إشارة"] = "⚡ متابعة"
    df.loc[potential_buy, "سعر الدخول"] = df["Price"]
    df.loc[potential_buy, "جني الأرباح"] = (df["Price"] * 1.03).round(2)
    df.loc[potential_buy, "وقف الخسارة"] = (df["Price"] * 0.985).round(2)

    return df

# ==============================
# إدارة الصفقات
# ==============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date", "Symbol", "Price", "Quantity"])

def save_trades(df):
    df.to_csv(TRADES_FILE, index=False)

def trade_analysis(price_buy, current_price):
    gain_percent = (current_price - price_buy) / price_buy * 100
    if gain_percent >= 5:
        return "💰 يفضل بيع جزئي"
    elif gain_percent < -3:
        return "⚠️ وقف الخسارة / بيع"
    else:
        return "⏳ الاستمرار بالصفقة"

# ==============================
# واجهة المستخدم
# ==============================
st.title("📊 Market Dashboard")
tabs = ["تحليل الأسهم", "أقوى الأسهم", "توصيات شراء", "إدارة الصفقات", "تدريب النظام"]
page = st.tabs(tabs)

# اختيار السوق
market_choice = st.selectbox("اختر السوق", list(MARKET_FILES.keys()))
symbols_df = load_stocks(market_choice)
df = analyze_stocks(symbols_df)

# ==============================
# تاب 1: تحليل الأسهم
# ==============================
with page[0]:
    st.subheader("تحليل كل الأسهم")
    if df.empty:
        st.info("لا توجد بيانات")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

# ==============================
# تاب 2: أقوى الأسهم
# ==============================
with page[1]:
    st.subheader("أقوى الأسهم")
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي", "⚡ متوسط"])]
    if strong_df.empty:
        st.info("لا توجد أسهم قوية حالياً")
    else:
        st.dataframe(strong_df, use_container_width=True, hide_index=True)

# ==============================
# تاب 3: توصيات شراء
# ==============================
with page[2]:
    st.subheader("توصيات شراء")
    buy_df = df[df["إشارة"] == "🔥 شراء"]
    if buy_df.empty:
        st.info("لا توجد توصيات شراء حالياً")
    else:
        st.dataframe(buy_df, use_container_width=True, hide_index=True)

# ==============================
# تاب 4: إدارة الصفقات
# ==============================
with page[3]:
    st.subheader("تتبع وإدارة الصفقات")
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

    # تحليل الصفقات الحالية
    st.write("تحليل الصفقات الحالية")
    for i, row in trades_df.iterrows():
        current_price = fetch_price(row["Symbol"])
        if current_price:
            result = trade_analysis(row["Price"], current_price)
            st.write(f"{row['Symbol']}: السعر الحالي {current_price:.2f} → {result}")

# ==============================
# تاب 5: تدريب النظام
# ==============================
with page[4]:
    st.subheader("تدريب النظام على الصفقات السابقة")
    trades_df = load_trades()
    if trades_df.empty:
        st.info("لا توجد صفقات للتدريب")
    else:
        trades_df["Profit %"] = 0.0
        for i, row in trades_df.iterrows():
            current_price = fetch_price(row["Symbol"])
            if current_price:
                trades_df.at[i, "Profit %"] = (current_price - row["Price"])/row["Price"]*100
        st.dataframe(trades_df, use_container_width=True, hide_index=True)
        st.write("يمكنك الآن استخدام هذه البيانات لتطوير نظام نقاط أو نموذج ML لتوقع توصيات الشراء/البيع مستقبلاً")
