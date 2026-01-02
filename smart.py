import time
import pandas as pd
import requests
from datetime import datetime, timedelta
from kiteconnect import KiteConnect

# ========= CONFIG =========
API_KEY = "awh2j04pcd83zfvq"
API_SECRET = "gfjmlgcn28pirja9b1e3xtww8ep7xthb"

SCAN_INTERVAL = 180
CANDLE_INTERVAL = "5minute"

VOL_MULT = 1.5
RANGE_MULT = 1.3
MAX_PRICE_MOVE = 1.2

TOP_N = 20   # 🔥 TOP 20 ONLY (NO RANGE FILTER)

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

# ========= MEMORY =========
prev_gainer_ranks = {}
prev_loser_ranks = {}

# ========= SMART MONEY =========
def is_smart_money(token, pct_change, prev_close):
    try:
        if abs(pct_change) > MAX_PRICE_MOVE:
            return False

        now = datetime.now()
        candles = kite.historical_data(
            token,
            now - timedelta(minutes=90),
            now,
            CANDLE_INTERVAL
        )

        if len(candles) < 6:
            return False

        last5 = candles[-6:-1]
        curr = candles[-1]

        avg_vol = sum(c["volume"] for c in last5) / 5
        avg_rng = sum((c["high"] - c["low"]) for c in last5) / 5

        vol_ok = curr["volume"] >= VOL_MULT * avg_vol
        rng_ok = (curr["high"] - curr["low"]) >= RANGE_MULT * avg_rng
        context_ok = curr["close"] >= prev_close

        return vol_ok and rng_ok and context_ok
    except:
        return False

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
                "Token": int(token),
                "LTP": round(ltp, 2),
                "%Change": round(pct, 2),
                "PrevClose": prev_close
            })

        df_live = pd.DataFrame(rows)

        # ===== MARKET SENTIMENT (NO RANGE) =====
        bull = len(df_live[df_live["%Change"] > 0])
        bear = len(df_live[df_live["%Change"] < 0])

        if bull > bear:
            sentiment = "🟢 *BULLISH MARKET*"
        elif bear > bull:
            sentiment = "🔴 *BEARISH MARKET*"
        else:
            sentiment = "🟡 *SIDEWAYS MARKET*"

        # ===== TOP 20 DIRECT =====
        gainers = df_live.sort_values("%Change", ascending=False).head(TOP_N)
        losers = df_live.sort_values("%Change").head(TOP_N)

        # ===== MESSAGE =====
        msg = (
            "📊 *MARKET SENTIMENT*\n"
            f"🟢 Advancing: {bull} stocks\n"
            f"🔴 Declining: {bear} stocks\n"
            f"{sentiment}\n\n"
        )

        msg += f"📊 *TOP {TOP_N} GAINERS (NO RANGE)*\n\n"
        for rank, r in enumerate(gainers.to_dict("records"), start=1):
            swap = ""
            old = prev_gainer_ranks.get(r["Stock"])
            if old:
                if rank < old:
                    swap = f" (↑ from #{old})"
                elif rank > old:
                    swap = f" (↓ from #{old})"

            smart = " 🧠 SMART MONEY" if is_smart_money(
                r["Token"], r["%Change"], r["PrevClose"]
            ) else ""

            msg += (
                f"#{rank} 🟢 *{r['Stock']}* | "
                f"{r['%Change']}% | ₹{r['LTP']}{swap}{smart}\n"
            )

        msg += f"\n📉 *TOP {TOP_N} LOSERS (NO RANGE)*\n\n"
        for rank, r in enumerate(losers.to_dict("records"), start=1):
            swap = ""
            old = prev_loser_ranks.get(r["Stock"])
            if old:
                if rank < old:
                    swap = f" (↑ from #{old})"
                elif rank > old:
                    swap = f" (↓ from #{old})"

            smart = " 🧠 SMART MONEY" if is_smart_money(
                r["Token"], r["%Change"], r["PrevClose"]
            ) else ""

            msg += (
                f"#{rank} 🔴 *{r['Stock']}* | "
                f"{r['%Change']}% | ₹{r['LTP']}{swap}{smart}\n"
            )

        tg(msg)

        prev_gainer_ranks = {s: i+1 for i, s in enumerate(gainers["Stock"])}
        prev_loser_ranks = {s: i+1 for i, s in enumerate(losers["Stock"])}

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(SCAN_INTERVAL)

