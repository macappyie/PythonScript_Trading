import time
import pandas as pd
import requests
from datetime import datetime
from kiteconnect import KiteConnect

# ========= CONFIG =========
API_KEY = "awh2j04pcd83zfvq"
API_SECRET = "gfjmlgcn28pirja9b1e3xtww8ep7xthb"

SCAN_INTERVAL = 180

RANGE_LOW = 1.0
RANGE_HIGH = 1.5
TOP_N = 10

# ========= TELEGRAM =========
BOT = "8060596624:AAEy0fb4tMTGtBJBywF-fHXmwjIYhVDQzjs"
with open("subscribers.txt") as f:
    CHAT_IDS = [x.strip() for x in f if x.strip()]

def tg(msg):
    for cid in CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{BOT}/sendMessage",
                data={
                    "chat_id": cid,
                    "text": msg,
                    "parse_mode": "Markdown"
                },
                timeout=5
            )
        except:
            pass

# ========= KITE =========
with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ========= INSTRUMENTS =========
df = pd.read_csv("instruments.csv", low_memory=False)
df = df[df["exchange"] == "NSE"]
symbol_to_token = dict(zip(df["tradingsymbol"], df["instrument_token"]))
token_to_symbol = dict(zip(df["instrument_token"], df["tradingsymbol"]))

# ========= WATCHLIST =========
with open("watchlist.txt") as f:
    STOCKS = [s.strip() for s in f if s.strip()]
TOKENS = [symbol_to_token[s] for s in STOCKS if s in symbol_to_token]

# ========= MAIN LOOP =========
while True:
    try:
        quotes = kite.quote(TOKENS)
        rows = []

        for token, q in quotes.items():
            symbol = token_to_symbol[int(token)]
            ltp = q["last_price"]
            prev_close = q["ohlc"]["close"]
            pct = ((ltp - prev_close) / prev_close) * 100

            rows.append({
                "Stock": symbol,
                "LTP": round(ltp, 2),
                "%Change": round(pct, 2)
            })

        df_live = pd.DataFrame(rows)

        # ===== RANGE FILTER =====
        gainers = df_live[
            (df_live["%Change"] >= RANGE_LOW) &
            (df_live["%Change"] <= RANGE_HIGH)
        ].sort_values("%Change", ascending=False).head(TOP_N)

        losers = df_live[
            (df_live["%Change"] <= -RANGE_LOW) &
            (df_live["%Change"] >= -RANGE_HIGH)
        ].sort_values("%Change").head(TOP_N)

        # ===== MESSAGE =====
        msg = "📊 *RANGE MARKET SCAN (1% – 1.5%)*\n\n"

        msg += f"🟢 *TOP {TOP_N} GAINERS*\n\n"
        for i, r in enumerate(gainers.to_dict("records"), 1):
            msg += f"#{i} 🟢 *{r['Stock']}* | {r['%Change']}% | ₹{r['LTP']}\n"

        msg += f"\n🔴 *TOP {TOP_N} LOSERS*\n\n"
        for i, r in enumerate(losers.to_dict("records"), 1):
            msg += f"#{i} 🔴 *{r['Stock']}* | {r['%Change']}% | ₹{r['LTP']}\n"

        tg(msg)

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(SCAN_INTERVAL)

