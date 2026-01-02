import time
import pandas as pd
import requests
from kiteconnect import KiteConnect
from datetime import datetime

# ================= CONFIG =================
API_KEY = "awh2j04pcd83zfvq"
API_SECRET = "gfjmlgcn28pirja9b1e3xtww8ep7xthb"

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ================ TELEGRAM ================
BOT = "8060596624:AAEy0fb4tMTGtBJBywF-fHXmwjIYhVDQzjs"
with open("subscribers.txt") as f:
    CHAT_IDS = [line.strip() for line in f if line.strip()]


def tg(msg):
    for cid in CHAT_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT}/sendMessage"
            requests.post(
                url,
                data={
                    "chat_id": cid,
                    "text": msg,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )
        except:
            pass


# ============ GET FUTURES % CHANGE ============
def get_stock_changes():
    df = pd.read_csv("instruments.csv")
    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
    today = datetime.today()

    futs = df[
        (df["segment"] == "NFO-FUT") &
        (~df["tradingsymbol"].str.contains("NIFTY|BANKNIFTY")) &
        (df["expiry"] >= today)
    ]

    if futs.empty:
        return []

    expiry = futs["expiry"].min()
    futs = futs[futs["expiry"] == expiry]

    changes = []

    for i in range(0, len(futs), 200):
        batch = futs.iloc[i:i + 200]

        try:
            quotes = kite.quote([f"NFO:{s}" for s in batch.tradingsymbol])

            for s in batch.tradingsymbol:
                d = quotes.get(f"NFO:{s}")
                if not d:
                    continue

                ltp = d["last_price"]
                prev = d["ohlc"]["close"]
                if prev == 0:
                    continue

                pct = ((ltp - prev) / prev) * 100
                changes.append(pct)

        except:
            pass

        time.sleep(0.25)

    return changes


# ============ RANGE COUNTING ============
def count_ranges(changes):
    ranges = [
        "0-0.8%",
        "0.8-1.5%",
        "1.5-2%",
        "2-3%",
        "3%+"
    ]

    bullish = {r: 0 for r in ranges}
    bearish = {r: 0 for r in ranges}

    total_bullish = 0
    total_bearish = 0

    for c in changes:
        if c > 0:
            total_bullish += 1
            if 0 < c < 0.8:
                bullish["0-0.8%"] += 1
            elif 0.8 <= c < 1.5:
                bullish["0.8-1.5%"] += 1
            elif 1.5 <= c < 2:
                bullish["1.5-2%"] += 1
            elif 2 <= c < 3:
                bullish["2-3%"] += 1
            elif c >= 3:
                bullish["3%+"] += 1

        elif c < 0:
            total_bearish += 1
            c = abs(c)
            if 0 < c < 0.8:
                bearish["0-0.8%"] += 1
            elif 0.8 <= c < 1.5:
                bearish["0.8-1.5%"] += 1
            elif 1.5 <= c < 2:
                bearish["1.5-2%"] += 1
            elif 2 <= c < 3:
                bearish["2-3%"] += 1
            elif c >= 3:
                bearish["3%+"] += 1

    return bullish, bearish, total_bullish, total_bearish


# ============ MARKET SENTIMENT ============
def get_sentiment(total_bullish, total_bearish):
    total = total_bullish + total_bearish
    if total == 0:
        return "⚪ *NO DATA*"

    bullish_pct = (total_bullish / total) * 100

    if bullish_pct >= 75:
        return f"🚀 *VERY STRONG BULLISH* ({bullish_pct:.2f}% green)"
    elif bullish_pct >= 60:
        return f"📈 *BULLISH* ({bullish_pct:.2f}% green)"
    elif bullish_pct >= 50:
        return f"⚪ *SIDEWAYS TO BULLISH* ({bullish_pct:.2f}% green)"
    elif bullish_pct <= 25:
        return f"🔥 *VERY STRONG BEARISH* ({bullish_pct:.2f}% green)"
    elif bullish_pct <= 40:
        return f"🔻 *BEARISH* ({bullish_pct:.2f}% green)"
    else:
        return f"⚪ *SIDEWAYS* ({bullish_pct:.2f}% green)"


# ============ MAIN LOOP ============
def main():
    print("🔄 Market sentiment engine started...")

    while True:
        try:
            changes = get_stock_changes()
            bullish, bearish, tb, tr = count_ranges(changes)
            sentiment = get_sentiment(tb, tr)

            msg = f"📊 *Stock Movement Summary*\n🕒 {datetime.now().strftime('%H:%M:%S')}\n"
            msg += "━━━━━━━━━━━━━━━━━━\n\n"

            msg += f"🟢 *Bullish Stocks* (Total: {tb})\n"
            for k, v in bullish.items():
                msg += f"{k}: {v}\n"

            msg += f"\n🔴 *Bearish Stocks* (Total: {tr})\n"
            for k, v in bearish.items():
                msg += f"{k}: {v}\n"

            msg += f"\n📌 *Market Sentiment:* {sentiment}\n"

            tg(msg)
            print(msg)

        except Exception as e:
            print("Error:", e)

        time.sleep(300)


if __name__ == "__main__":
    main()

