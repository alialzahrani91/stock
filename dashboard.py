import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Market Dashboard", layout="wide")

# ملفات الأسواق
MARKET_FILES = {
    "السعودي": "ksa_stocks.csv",
    "الأمريكي": "usa_stocks.csv"
}
TRADES_FILE = "trades.csv"

# ==============================
# جلب بيانات السوق (TradingView API) للأعمدة الأساسية
# ==============================
def fetch_market_data(symbols):
    rows = []
    for sym in symbols:
        try:
            url = f"https://scanner.tradingview.com/america/scan"
            payload = {
                "filter": [{"left":"symbol","operation":"equal","right":sym}],
                "columns":["close","change","relative_volume_10d_calc","RSI","price_earnings_ttm"]
            }
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json().get("data", [])
            if data:
                d = data[0]["d"]
                rows.append({
                    "Symbol": sym,
                    "Price": float(d[0]),
                    "Change %": float(d[1]),
                    "Relative Volume": float(d[2]),
                    "RSI": float(d[3]),
                    "PE": float(d[4]) if d[4] else None
                })
        except:
            continue
    return pd.DataFrame(rows)

# ==============================
# إشارات وتحليل الأسهم
# ==============================
def analyze_stocks(df):
    df["الحالة"] = "🟡 مراقبة"
    df["إشارة"] = "❌ لا"
    df["سعر الدخول"] = None
    df["جني الأرباح"] = None
    df["وقف الخسارة"] = None
    df["قوة السهم"] = "🔴 ضعيف"
    df["Score"] = 0

    strong_buy = (df["Change %"]>2) & (df["Relative Volume"]>1.5) & (df["PE"].fillna(100)<30)
    potential_buy = ((df["Change %"]>1) | (df["Relative Volume"]>1.2)) & (df["PE"].fillna(100)<50)

    df.loc[strong_buy,"الحالة"]="⭐ قوي للشراء"
    df.loc[potential_buy & ~strong_buy,"الحالة"]="⚡ فرصة محتملة"
    df.loc[df["Change %"]<0,"الحالة"]="🔴 ضعيف"

    df.loc[strong_buy,"قوة السهم"]="⭐ قوي"
    df.loc[potential_buy & ~strong_buy,"قوة السهم"]="⚡ متوسط"

    df.loc[strong_buy,"إشارة"]="🔥 شراء"
    df.loc[strong_buy,"سعر الدخول"]=df["Price"]
    df.loc[strong_buy,"جني الأرباح"]=(df["Price"]*1.05).round(2)
    df.loc[strong_buy,"وقف الخسارة"]=(df["Price"]*0.975).round(2)
    df.loc[strong_buy,"Score"]=2

    df.loc[potential_buy & ~strong_buy,"إشارة"]="⚡ متابعة"
    df.loc[potential_buy & ~strong_buy,"سعر الدخول"]=df["Price"]
    df.loc[potential_buy & ~strong_buy,"جني الأرباح"]=(df["Price"]*1.03).round(2)
    df.loc[potential_buy & ~strong_buy,"وقف الخسارة"]=(df["Price"]*0.985).round(2)
    df.loc[potential_buy & ~strong_buy,"Score"]=1

    return df

# ==============================
# إدارة الصفقات وتحليلها
# ==============================
def trade_recommendation(price_buy, current_price):
    gain = (current_price-price_buy)/price_buy*100
    if gain>=5:
        return "💰 بيع جزئي"
    elif gain<=-3:
        return "⚠️ وقف الخسارة / بيع"
    else:
        return "⏳ استمر"

# ==============================
# تحميل وحفظ الصفقات
# ==============================
def load_trades():
    try:
        return pd.read_csv(TRADES_FILE)
    except:
        return pd.DataFrame(columns=["Date","Symbol","Price","Quantity","CurrentPrice","GainPercent","Recommendation"])

def save_trades(df):
    df.to_csv(TRADES_FILE,index=False)

def update_trades(df, market_symbols):
    market_data = fetch_market_data(market_symbols)
    for idx,row in df.iterrows():
        sym_data = market_data[market_data["Symbol"]==row["Symbol"]]
        if not sym_data.empty:
            current_price = sym_data["Price"].values[0]
            gain = (current_price-row["Price"])/row["Price"]*100
            rec = trade_recommendation(row["Price"], current_price)
            df.at[idx,"CurrentPrice"]=current_price
            df.at[idx,"GainPercent"]=round(gain,2)
            df.at[idx,"Recommendation"]=rec
    return df

# ==============================
# واجهة المستخدم
# ==============================
st.title("📊 Market Dashboard")

# اختيار السوق
market_choice = st.selectbox("اختر السوق", list(MARKET_FILES.keys()))
symbols_df = pd.read_csv(MARKET_FILES[market_choice])
symbols = symbols_df["Symbol"].tolist()

# التابات
tabs = st.tabs(["تحليل الأسهم","أقوى الأسهم","توصيات شراء","إدارة الصفقة","تتبع الصفقات"])

# ==============================
# تاب 1: تحليل الأسهم
# ==============================
with tabs[0]:
    st.subheader("تحليل الأسهم")
    df = fetch_market_data(symbols)
    df = analyze_stocks(df)
    st.dataframe(df,use_container_width=True)

# ==============================
# تاب 2: أقوى الأسهم
# ==============================
with tabs[1]:
    st.subheader("أقوى الأسهم")
    strong_df = df[df["قوة السهم"].isin(["⭐ قوي","⚡ متوسط"])]
    st.dataframe(strong_df,use_container_width=True)

# ==============================
# تاب 3: توصيات شراء
# ==============================
with tabs[2]:
    st.subheader("توصيات شراء")
    buy_df = df[df["إشارة"]=="🔥 شراء"]
    st.dataframe(buy_df,use_container_width=True)

# ==============================
# تاب 4: إدارة الصفقة
# ==============================
with tabs[3]:
    st.subheader("إدارة الصفقة")
    symbol_input = st.text_input("رمز السهم")
    price_input = st.number_input("سعر الشراء", min_value=0.0, step=0.01)
    if st.button("تحليل الصفقة"):
        if symbol_input and price_input>0:
            sym_data = df[df["Symbol"]==symbol_input]
            if not sym_data.empty:
                current_price = sym_data["Price"].values[0]
                rec = trade_recommendation(price_input, current_price)
                st.write(f"السعر الحالي: {current_price}")
                st.write(f"التوصية: {rec}")
            else:
                st.warning("❌ السهم غير موجود في قائمة السوق")

# ==============================
# تاب 5: تتبع الصفقات + التدريب
# ==============================
with tabs[4]:
    st.subheader("تتبع الصفقات + تدريب النظام")
    trades_df = load_trades()
    trades_df = update_trades(trades_df, symbols)
    st.dataframe(trades_df,use_container_width=True)

    st.write("أضف صفقة جديدة")
    new_symbol = st.text_input("رمز السهم جديد")
    new_price = st.number_input("سعر الشراء جديد",min_value=0.0,step=0.01)
    new_qty = st.number_input("عدد الأسهم",min_value=1,step=1)
    new_date = st.date_input("تاريخ الشراء", datetime.today())
    if st.button("حفظ الصفقة"):
        if new_symbol and new_price>0 and new_qty>0:
            new_trade = pd.DataFrame([{
                "Date": new_date,
                "Symbol": new_symbol,
                "Price": new_price,
                "Quantity": new_qty,
                "CurrentPrice": new_price,
                "GainPercent": 0.0,
                "Recommendation": "⏳ استمر"
            }])
            trades_df = pd.concat([trades_df,new_trade],ignore_index=True)
            save_trades(trades_df)
            st.success("✅ تم حفظ الصفقة")
