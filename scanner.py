import yfinance as yf
import pandas as pd
import ta

def scan_market(symbols):
    results = []
    for symbol in symbols:
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if df.empty or len(df) < 200:
                continue

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

            if ".TADAWUL" in symbol:
                value_traded = last["Close"] * last["Volume"]
                change_pct = abs((last["Close"] - prev["Close"]) / prev["Close"]) * 100
                if value_traded < 10_000_000 or change_pct > 8:
                    continue

            entry = last["Close"]
            stop = entry - (last["atr"] * 1.2)
            risk = entry - stop
            target1 = entry + risk
            target2 = entry + (2 * risk)

            if volume_ratio >= 2 and 58 <= last["rsi"] <= 65:
                rating = "⭐⭐⭐⭐"
            elif volume_ratio >= 1.5:
                rating = "⭐⭐⭐"
            else:
                rating = "⭐⭐"

            if rating in ["⭐⭐⭐", "⭐⭐⭐⭐"]:
                results.append({
                    "symbol": symbol,
                    "rating": rating,
                    "entry": round(entry,2),
                    "stop": round(stop,2),
                    "target_1": round(target1,2),
                    "target_2": round(target2,2),
                    "rsi": round(last["rsi"],1),
                    "volume_power": round(volume_ratio,2)
                })
        except:
            continue
    return pd.DataFrame(results).sort_values(by=["rating","volume_power"], ascending=False)
