#!/usr/bin/env python3
"""BTC signal (bir martalik). Rejalashtirilgan vazifa (GitHub Actions) ishga tushiradi.
Muhit o'zgaruvchilari: TG_TOKEN (BotFather tokeni), TG_CHAT_ID (sizning chat ID).
Chat ID topish: TG_TOKEN o'rnatib, botga /start yozing, so'ng: python signal_once.py chatid
"""
import json
import os
import sys
import requests

SYMBOL, INTERVAL = "BTCUSDT", "1h"
HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]
TOKEN, CHAT = os.getenv("TG_TOKEN"), os.getenv("TG_CHAT_ID")
STATE = "state.json"


def klines():
    err = None
    for h in HOSTS:
        try:
            r = requests.get(f"{h}/api/v3/klines", timeout=15,
                             params={"symbol": SYMBOL, "interval": INTERVAL, "limit": 300})
            r.raise_for_status()
            k = r.json()
            return [float(x[2]) for x in k], [float(x[3]) for x in k], [float(x[4]) for x in k]
        except Exception as e:
            err = e
    raise SystemExit(f"Binance ulanmadi: {err}")


def ema(a, n):
    k, p, out = 2 / (n + 1), a[0], []
    for v in a:
        p = v * k + p * (1 - k)
        out.append(p)
    return out


def rsi(c, n=14):
    g = l = 0.0
    for i in range(1, n + 1):
        d = c[i] - c[i - 1]
        g += max(d, 0)
        l += max(-d, 0)
    g, l = g / n, l / n
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n
        l = (l * (n - 1) + max(-d, 0)) / n
    return 100 - 100 / (1 + g / (l or 1e-9))


def analyze():
    h, l, c = klines()
    p = c[-1]
    r = rsi(c)
    m = [a - b for a, b in zip(ema(c, 12), ema(c, 26))]
    hist = m[-1] - ema(m, 9)[-1]
    s20, s50 = sum(c[-20:]) / 20, sum(c[-50:]) / 50
    sd = (sum((x - s20) ** 2 for x in c[-20:]) / 20) ** 0.5
    lo, up = s20 - 2 * sd, s20 + 2 * sd
    score = (1 if r < 30 else -1 if r > 70 else 0) + (1 if hist > 0 else -1) \
        + (1 if p > s50 else -1) + (1 if s20 > s50 else -1) + (1 if p < lo else -1 if p > up else 0)
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]
    a = sum(tr[-14:]) / 14
    head = f"{SYMBOL} · {INTERVAL}\nNarx: {p:,.2f}\nRSI {r:.1f} | ball {score:+d}\n"
    if score >= 2:
        return "BUY", head + f"\n🟢 SOTIB OLISH signali\nStop-loss: {p - 1.5 * a:,.0f}\nTake-profit: {p + 3 * a:,.0f}"
    if score <= -2:
        return "SELL", head + "\n🔴 SOTISH / pozitsiyadan chiqish signali"
    return "NEUTRAL", head + "\n⚪ Neytral: yangi pozitsiya ochmaslik ma'qul"


def send(text):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", timeout=15,
                  json={"chat_id": CHAT, "text": text + "\n\nBu moliyaviy maslahat emas."}).raise_for_status()


def main():
    if not TOKEN:
        raise SystemExit("TG_TOKEN o'rnatilmagan")
    if len(sys.argv) > 1 and sys.argv[1] == "chatid":
        u = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=15).json()
        ids = {x["message"]["chat"]["id"] for x in u.get("result", []) if "message" in x}
        print("Chat ID:", ids or "topilmadi: botga avval /start yozing")
        return
    if not CHAT:
        raise SystemExit("TG_CHAT_ID o'rnatilmagan")
    try:
        last = json.load(open(STATE)).get("last")
    except Exception:
        last = None
    sig, text = analyze()
    print(sig, "(oldingi:", last, ")")
    if sig != last:
        send(text)
        json.dump({"last": sig}, open(STATE, "w"))


if __name__ == "__main__":
    main()
  
