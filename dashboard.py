import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
TRADES_FILE = "trades.csv"
EXCEL_FILE = "stocks.xlsx"  # ملف الأسهم

# =============================
# جلب بيانات التحليل من الإنترنت (TradingView API)
# =============================
def fetch_analysis(symbol):
    url = "https://scanner.tradingview.com/america/scan"  # مثال على السوق الأمريكي
    payload = {
        "filter": [{"left": "name", "operation": "equal", "right": symbol}],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["close","change","relative_volume_10d_calc","price_earnings_ttm"],
        "range":[0,1]
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return None
        d = data[0]["d"]
        return {
            "Price": float(d[0]),
            "Change %": float(d[1]),
            "Relative Volume": float(d[2]),
            "PE": float(d[3]) if d[3] else None
        }
    except:
        return None

# =============================
# إضافة إشارات وتوصيات
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

    for idx, row in df.iterrows():
        analysis = fetch_analysis(row["Symbol"])
        if analysis:
            price = analysis["Price"]
            change = analysis["Change %"]
            vol = analysis["Relative Volume"]
            pe = analysis["PE"] if analysis["PE"] else 100

            strong_buy = (change > 2) & (vol > 1.5) & (pe < 30)
            potential_buy = ((change > 1) | (vol > 1.2)) & (pe < 50)

            if strong_buy:
                df.at[idx,"الحالة"]="⭐ قوي للشراء"
                df.at[idx,"قوة السهم"]="⭐ قوي"
                df.at[idx,"إشارة"]="🔥 شراء"
                df.at[idx,"سعر الدخول"]=price
                df.at[idx,"جني الأرباح"]=round(price*1.05,2)
                df.at[idx,"وقف الخسارة"]=round(price*0.975,2)
            elif potential_buy:
                df.at[idx,"الحالة"]="⚡ فرصة محتملة"
                df.at[idx,"قوة السهم"]="⚡ متوسط"
                df.at[idx,"إشارة"]="⚡ متابعة"
                df.at[idx,"سعر الدخول"]=price
                df.at[idx,"جني الأرباح"]=round(price*1.03,2)
                df.at[idx,"وقف الخسارة"]=round(price*0.985,2)
            elif change<0:
                df.at[idx,"الحالة"]="🔴 ضعيف"
    return df

# =============================
# حفظ وتتبع الصفقات
# =============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity","Current Price","Score","Recommendation"])

def save_trades(df):
    df.to_csv(TRADES_FILE,index=False)

def trade_score(price_buy,current_price,pe,vol):
    score = 0
    if current_price>price_buy: score+=2
    if pe<30: score+=1
    if vol>1.2: score+=1
    return score

def trade_recommendation(score):
    if score>=3: return "💰 بيع جزئي أو متابعة"
    elif score==2: return "⏳ الاستمرار"
    else: return "⚠️ بيع / وقف خسارة"

# =============================
# واجهة المستخدم
# =============================
st.title("📊 Market Dashboard")
tabs = ["فرص مضاربية","أقوى الأسهم","إدارة الصفقة","تتبع الصفقات","أعلى الفوليوم"]
page = st.tabs(tabs)

# =============================
# قراءة الأسهم من Excel
# =============================
try:
    df = pd.read_excel(EXCEL_FILE)
except:
    st.error("❌ لم يتم العثور على ملف الأسهم Excel")
    df = pd.DataFrame(columns=["Symbol","Company"])

df = add_signals(df)

# =============================
# تاب فرص مضاربية
# =============================
with page[0]:
    st.subheader("فرص مضاربية")
    if df.empty:
        st.info("لا توجد بيانات")
    else:
        st.dataframe(df,use_container_width=True,hide_index=True)

# =============================
# تاب أقوى الأسهم
# =============================
with page[1]:
    st.subheader("أقوى الأسهم")
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي","⚡ متوسط"])]
    st.dataframe(strong_df,use_container_width=True,hide_index=True)

# =============================
# تاب إدارة الصفقة
# =============================
with page[2]:
    st.subheader("إدارة الصفقة")
    symbol = st.text_input("رمز السهم")
    price_buy = st.number_input("سعر الشراء",min_value=0.0,step=0.01)
    current_price = st.number_input("السعر الحالي",min_value=0.0,step=0.01)
    pe = st.number_input("PE (اختياري)", min_value=0.0,step=0.1)
    vol = st.number_input("حجم نسبي (اختياري)", min_value=0.0,step=0.1)
    if st.button("تحليل الصفقة"):
        if symbol and price_buy>0 and current_price>0:
            score = trade_score(price_buy,current_price,pe,vol)
            recommendation = trade_recommendation(score)
            st.write(f"Score: {score} | Recommendation: {recommendation}")
        else:
            st.error("❌ يرجى إدخال جميع القيم")

# =============================
# تاب تتبع الصفقات
# =============================
with page[3]:
    st.subheader("تتبع الصفقات")
    trades_df = load_trades()
    st.dataframe(trades_df,use_container_width=True,hide_index=True)

    st.write("أضف صفقة جديدة")
    symbol_new = st.text_input("رمز جديد")
    price_new = st.number_input("سعر شراء جديد",min_value=0.0,step=0.01)
    qty_new = st.number_input("عدد الأسهم",min_value=1,step=1)
    date_new = st.date_input("تاريخ الشراء",datetime.today())
    if st.button("حفظ الصفقة"):
        if symbol_new and price_new>0 and qty_new>0:
            score = trade_score(price_new,price_new,pe=0,vol=1)  # عند إضافة الصفقة
            recommendation = trade_recommendation(score)
            new_trade = pd.DataFrame([{
                "Date": date_new,"Symbol": symbol_new,"Price": price_new,
                "Quantity": qty_new,"Current Price": price_new,
                "Score": score,"Recommendation": recommendation
            }])
            trades_df = pd.concat([trades_df,new_trade],ignore_index=True)
            save_trades(trades_df)
            st.success("تم حفظ الصفقة")

# =============================
# تاب أعلى الفوليوم
# =============================
with page[4]:
    st.subheader("أعلى الفوليوم")
    st.info("الميزة هذه تحتاج جلب الفوليوم التاريخي من مصدر خارجي أو Excel")
