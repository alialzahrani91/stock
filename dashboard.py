import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import hashlib
import requests

# ===== حماية بكلمة مرور =====
PASSWORD_HASH = hashlib.sha256("mypassword123".encode()).hexdigest()
def check_password():
    st.sidebar.header("🔐 تسجيل الدخول")
    password = st.sidebar.text_input("كلمة المرور", type="password")
    if hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH:
        return True
    return False

if not check_password():
    st.warning("❌ كلمة المرور غير صحيحة")
    st.stop()

st.set_page_config(page_title="Market Scanner", layout="wide")
st.title("📊 Market Scanner Dashboard")

# ===== دوال لجلب الأسهم ديناميكيًا =====
@st.cache_data
def get_us_symbols():
    # جلب الشركات المدرجة في S&P500 كمثال
    tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    df = tables[0]
    symbols = df['Symbol'].tolist()
    return symbols

@st.cache_data
def get_saudi_symbols():
    # جلب الأسهم السعودية من Tadawul أو مصدر HTML مباشر
    url = "https://www.saudiexchange.sa/wps/portal/tadawul/markets/equities/market-watch"  # مثال
    try:
        tables = pd.read_html(url)
        df = tables[0]  # افتراض أن جدول الأسهم هو الأول
        symbols = df['رمز الشركة'].astype(str) + ".TADAWUL"
        return symbols.tolist()
    except:
        st.warning("⚠️ تعذر جلب الأسهم السعودية، يرجى التحقق من الرابط أو الاتصال بالإنترنت")
        return []

# ===== اختيار السوق =====
market = st.selectbox("السوق", ["الكل", "السعودي", "الأمريكي"])
rating_filter = st.selectbox("التقييم", ["الكل", "⭐⭐⭐⭐", "⭐⭐⭐"])

if market == "السعودي":
    symbols = get_saudi_symbols()
elif market == "الأمريكي":
    symbols = get_us_symbols()
else:
    symbols = get_saudi_symbols() + get_us_symbols()

st.info(f"⏳ جاري فحص {len(symbols)} سهم مباشرة من الإنترنت... قد يستغرق عدة دقائق")

# ===== الفحص الفني المباشر =====
results = []

progress = st.progress(0)
total = len(symbols)

for i, symbol in enumerate(symbols):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 200: continue

        # المؤشرات الفنية
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma50"] = df["Close"].rolling(50).mean()
        df["ma200"] = df["Close"].rolling(200).mean()
        df["rsi"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
        df["vol_avg"] = df["Volume"].rolling(20).mean()
        df["atr"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        strong_trend = last["Close"] > last["ma20"] > last["ma50"] > last["ma200"]
        breakout = last["Close"] >= df["High"].rolling(20).max().iloc[-1]
        volume_ratio = last["Volume"] / last["vol_avg"]

        if not (strong_trend and breakout and 55 < last["rsi"] < 68 and volume_ratio > 1.3):
            continue

        # فلترة خاصة بالسعودي
        if ".TADAWUL" in symbol:
            value_traded = last["Close"] * last["Volume"]
            change_pct = abs((last["Close"] - prev["Close"])/prev["Close"])*100
            if value_traded < 10_000_000 or change_pct > 8: continue

        entry = last["Close"]
        stop = entry - (last["atr"]*1.2)
        risk = entry - stop
        target1 = entry + risk
        target2 = entry + (2*risk)

        if volume_ratio>=2 and 58<=last["rsi"]<=65: rating="⭐⭐⭐⭐"
        elif volume_ratio>=1.5: rating="⭐⭐⭐"
        else: rating="⭐⭐"

        if rating in ["⭐⭐⭐","⭐⭐⭐⭐"]:
            results.append({
                "symbol":symbol,
                "rating":rating,
                "entry":round(entry,2),
                "stop":round(stop,2),
                "target_1":round(target1,2),
                "target_2":round(target2,2),
                "rsi":round(last["rsi"],1),
                "volume_power":round(volume_ratio,2)
            })
    except:
        continue
    progress.progress((i+1)/total)

# ===== عرض النتائج =====
if results:
    df_results = pd.DataFrame(results)
    if rating_filter != "الكل":
        df_results = df_results[df_results["rating"]==rating_filter]
    st.dataframe(df_results, use_container_width=True)
else:
    st.warning("❌ لم يتم العثور على أي فرص حالياً")
