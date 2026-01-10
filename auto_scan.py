import streamlit as st
import pandas as pd
import hashlib
import os

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

# ======= فحص وجود الملف =======
if os.path.exists("latest_results.csv"):
    df = pd.read_csv("latest_results.csv")
    if df.empty:
        st.warning("⚠️ لم يتم العثور على أي بيانات في الفحص الأخير.")
        st.stop()
    st.caption(f"آخر تحديث: {df['scan_time'].iloc[0]}")
else:
    st.error("❌ ملف latest_results.csv غير موجود. شغّل auto_scan.py أولاً.")
    st.stop()

# ======= فلترة البيانات =======
market = st.selectbox("السوق", ["الكل", "السعودي", "الأمريكي"])
rating = st.selectbox("التقييم", ["الكل", "⭐⭐⭐⭐", "⭐⭐⭐"])

if market == "السعودي":
    if "symbol" in df.columns:
        df = df[df["symbol"].str.contains("TADAWUL")]
elif market == "الأمريكي":
    if "symbol" in df.columns:
        df = df[~df["symbol"].str.contains("TADAWUL")]

if rating != "الكل":
    if "rating" in df.columns:
        df = df[df["rating"] == rating]

st.dataframe(df, use_container_width=True)
