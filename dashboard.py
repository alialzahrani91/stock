import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import ta
import hashlib

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
st.title("📊 Market Scanner Dashboard - Saudi & US Stocks from TradingView")

# ===== دالة جلب الأسهم السعودية =====
@st.cache_data(ttl=24*3600)
def get_saudi_symbols():
    url = "https://ar.tradingview.com/markets/stocks-ksa/market-movers-all-stocks/"
    res = requests.get(url)
    if res.status_code != 200:
        st.warning("⚠️ تعذر جلب الأسهم السعودية من TradingView")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    symbols = []
    for row in soup.select("table tbody tr"):
        cells = row.find_all("td")
        if len(cells) > 0:
            symbol_text = cells[0].get_text(strip=True)
            symbols.append(symbol_text + ".TADAWUL")
    return symbols

# ===== دالة جلب الأسهم الأمريكية =====
@st.cache_data(ttl=24*3600)
def get_us_symbols():
    url = "https://ar.tradingview.com/markets/stocks-usa/market-movers-all-stocks/"
    res = requests.get(url)
    if res.status_code != 200:
        st.warning("⚠️ تعذر جلب الأسهم الأمريكية من TradingView")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    symbols = []
    for row in soup.select("table tbody tr"):
        cells = row.find_all("td")
        if len(cells) > 0:
            symbol_text = cells[0].get_text(strip=True)
            symbols.append(symbol_text)
    return symbols

# ===== اختيار السوق =====
market = st.selectbox("اختر السوق", ["السعودي", "الأمريكي", "الكل"])

symbols = []
if market == "السعودي":
    symbols = get_saudi_symbols()
elif market == "الأمريكي":
    symbols = get_us_symbols()
else:
    symbols = get_saudi_symbols() + get_us_symbols()

st.info(f"⏳ جاري فحص {len(symbols)} سهم من {market}... قد يستغرق عدة دقائق")

# ===== الفحص الفني =====
results = []
progress = st.progress(0)
total = len(symbols)

for i, symbol in enumerate(symbols):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 50: 
            continue

        # مؤشرات فنية
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma50"] = df["Close"].rolling(50).mean()
        df["ma200"] = df["Close"].rolling(200).mean()
        df["rsi"] = ta.momentum.RSIIndicator(df["Close"]).rsi()
        df["vol_avg"] = df["Volume"].rolling(20).mean()
        df["atr"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

        last = df.iloc[-1]

        strong_trend = last["Close"] > last["ma20"] > last["ma50"] > last["ma200"]
        breakout = last["Close"] >= df["High"].rolling(20).max().iloc[-1]
        volume_ratio = last["Volume"] / last["vol_avg"]

        if not (strong_trend and breakout and 55 < last["rsi"] < 68 and volume_ratio > 1.3):
            continue

        # إعداد الدخول والخروج
        entry = last["Close"]
        stop = entry - (last["atr"]*1.2)
        risk = entry - stop
        target1 = entry + risk
        target2 = entry + (2*risk)

        if volume_ratio>=2 and 58<=last["rsi"]<=65: rating="⭐⭐⭐⭐"
        elif volume_ratio>=1.5: rating="⭐⭐⭐"
        else: rating="⭐⭐"

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
    st.dataframe(df_results, use_container_width=True)
else:
    st.warning("❌ لم يتم العثور على أي فرص حالياً")
