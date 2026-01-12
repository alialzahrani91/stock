import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# =============================
# ملفات الأسهم لكل سوق
# =============================
MARKET_FILES = {
    "السعودي": "saudi_symbols.csv",
    "الأمريكي": "usa_symbols.csv"
}

# =============================
# تحميل الرموز من ملف CSV
# =============================
def load_symbols(market):
    try:
        df = pd.read_csv(MARKET_FILES[market])
        return df['Symbol'].tolist()
    except Exception as e:
        st.error(f"❌ لم يتم العثور على ملف الأسهم للسوق {market}")
        return []

# =============================
# جلب البيانات الحقيقية من الإنترنت
# =============================
def fetch_stock_data(symbols):
    rows = []
    for sym in symbols:
        try:
            data = yf.Ticker(sym).history(period="1d")
            if data.empty:
                continue
            last_price = data['Close'][-1]
            change = ((last_price - data['Open'][-1]) / data['Open'][-1]) * 100
            rows.append({
                "Symbol": sym,
                "Price": round(last_price,2),
                "Change %": round(change,2)
            })
        except:
            continue
    return pd.DataFrame(rows)

# =============================
# إشارات وحالة الأسهم
# =============================
def analyze_stocks(df):
    if df.empty:
        return df
    df["Signal"] = "❌ متابعة"
    df["Status"] = "🟡 مراقبة"
    df["Score"] = 0

    strong_buy = (df["Change %"] > 2)
    potential_buy = (df["Change %"] > 1)

    df.loc[strong_buy, "Signal"] = "🔥 شراء"
    df.loc[strong_buy, "Status"] = "⭐ قوي"
    df.loc[strong_buy, "Score"] = 3

    df.loc[potential_buy & ~strong_buy, "Signal"] = "⚡ متابعة"
    df.loc[potential_buy & ~strong_buy, "Status"] = "⚡ متوسط"
    df.loc[potential_buy & ~strong_buy, "Score"] = 2

    return df

# =============================
# إدارة الصفقات
# =============================
TRADES_FILE = "trades.csv"

def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity"])

def save_trades(df):
    df.to_csv(TRADES_FILE,index=False)

def trade_recommendation(price_buy, current_price):
    gain_pct = (current_price - price_buy) / price_buy * 100
    if gain_pct >= 5:
        return "💰 يفضل بيع جزئي"
    elif gain_pct <= -3:
        return "⚠️ وقف الخسارة / بيع"
    else:
        return "⏳ الاستمرار بالصفقة"

# =============================
# واجهة المستخدم
# =============================
st.title("📊 Stock Dashboard")
tabs = ["تحليل الأسهم","أقوى الأسهم","توصيات شراء","إدارة الصفقات","تدريب النظام"]
page = st.tabs(tabs)

# =============================
# اختيار السوق
# =============================
market_choice = st.selectbox("اختر السوق", list(MARKET_FILES.keys()))
symbols = load_symbols(market_choice)
stock_df = fetch_stock_data(symbols)
stock_df = analyze_stocks(stock_df)

# =============================
# تاب تحليل الأسهم
# =============================
with page[0]:
    st.subheader("تحليل كل الأسهم")
    st.dataframe(stock_df,use_container_width=True)

# =============================
# تاب أقوى الأسهم
# =============================
with page[1]:
    st.subheader("أقوى الأسهم")
    strong_df = stock_df[stock_df["Score"]>=2]
    st.dataframe(strong_df,use_container_width=True)

# =============================
# تاب توصيات شراء
# =============================
with page[2]:
    st.subheader("توصيات شراء")
    buy_df = stock_df[stock_df["Signal"]=="🔥 شراء"]
    st.dataframe(buy_df,use_container_width=True)

# =============================
# تاب إدارة الصفقات
# =============================
with page[3]:
    st.subheader("إدارة الصفقات")
    trades_df = load_trades()
    st.dataframe(trades_df,use_container_width=True)

    st.write("أضف صفقة جديدة")
    symbol_new = st.text_input("رمز السهم جديد")
    price_new = st.number_input("سعر الشراء",0.0,step=0.01)
    qty_new = st.number_input("عدد الأسهم",1,step=1)
    date_new = st.date_input("تاريخ الشراء",datetime.today())

    if st.button("حفظ الصفقة"):
        if symbol_new and price_new>0 and qty_new>0:
            new_trade = pd.DataFrame([{
                "Date":date_new,"Symbol":symbol_new,"Price":price_new,"Quantity":qty_new
            }])
            trades_df = pd.concat([trades_df,new_trade],ignore_index=True)
            save_trades(trades_df)
            st.success("تم حفظ الصفقة")

    st.write("تحليل الصفقات الحالية")
    for idx,row in trades_df.iterrows():
        try:
            current_price = yf.Ticker(row["Symbol"]).history(period="1d")['Close'][-1]
            recommendation = trade_recommendation(row["Price"],current_price)
            st.write(f"{row['Symbol']}: السعر الحالي {current_price:.2f} → {recommendation}")
        except:
            st.write(f"{row['Symbol']}: تعذر جلب البيانات")

# =============================
# تاب تدريب النظام
# =============================
with page[4]:
    st.subheader("تدريب النظام على الصفقات السابقة")
    st.write("يمكن هنا إضافة نماذج تعلم آلي لتحليل الصفقات السابقة وتحسين التوصيات")
    st.dataframe(trades_df,use_container_width=True)
