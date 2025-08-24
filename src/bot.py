"""
Exness MT5 Breakout Alert Bot
=============================

- Connects to Exness MT5 terminal
- Auto-detects broker symbols (e.g. EURUSDm, XAUUSDm)
- Monitors EURUSD, GBPUSD, NZDUSD, XAUUSD
- Sessions (IST):
    * Previous Day: 23:30 -> 05:29
    * Asian:       05:30 -> 12:29
    * London:      12:30 -> 17:30
- Resets daily at 23:00 IST
- Breakout confirmation: Closed M5 candles only
- Telegram Alerts:
    Symbol: XAUUSDm
    Point: 2335.620
    Remark: Asian High BreakOut Up
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict

import pytz
import MetaTrader5 as mt5
import telebot

# ========== CONFIG ==========
IST = pytz.timezone("Asia/Kolkata")

BASE_SYMBOLS = ["EURUSD", "GBPUSD", "NZDUSD", "XAUUSD"]
SYMBOLS = []

TIMEFRAME = mt5.TIMEFRAME_M1        # used for session levels
CHECK_TIMEFRAME = mt5.TIMEFRAME_M5  # breakout confirmation
TICK_INTERVAL_SEC = 10
RESET_HOUR_IST = 23
RESET_MINUTE_IST = 0

# ---- MT5 Credentials ----
ACCOUNT   = "Account login"     # your Exness account login
PASSWORD  = "Password"          # your Exness account password
SERVER    = "Server"            # Exness server name

# ---- Telegram ----
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
bot = telebot.TeleBot(BOT_TOKEN)

# ========== TELEGRAM ==========
def send_telegram(msg: str):
    bot.send_message(CHAT_ID, msg)
    print(f"[TELEGRAM] {msg.replace(chr(10), ' | ')}")

def send_levels_report(levels: dict):
    """Send PDH/PDL + AH/AL for all symbols"""
    parts = []
    for sym, sym_levels in levels.items():
        lines = [f"{sym}"]
        if "Previous Day" in sym_levels:
            lines.append(f"PDH: {sym_levels['Previous Day']['high']:.5f}")
            lines.append(f"PDL: {sym_levels['Previous Day']['low']:.5f}")
        if "Asian" in sym_levels:
            lines.append(f"AH: {sym_levels['Asian']['high']:.5f}")
            lines.append(f"AL: {sym_levels['Asian']['low']:.5f}")
        parts.append("\n".join(lines))
    full_msg = "\n\n".join(parts)
    send_telegram("📊 Daily Levels\n\n" + full_msg)

# ========== TIME HELPERS ==========
def utc_now():
    return datetime.utcnow().replace(tzinfo=pytz.utc)

def to_ist(dt_utc: datetime) -> datetime:
    return dt_utc.astimezone(IST)

def today_ist() -> datetime:
    now_ist = to_ist(utc_now())
    return IST.localize(datetime(now_ist.year, now_ist.month, now_ist.day, 0, 0, 0))

# ========== SESSION WINDOWS ==========
SESSION_DEFS = {
    "Previous Day": {"start": (23, 30), "end": (5, 29)},
    "Asian":        {"start": (5, 30),  "end": (12, 29)},
    "London":       {"start": (12, 30), "end": (17, 30)},
}

def session_window_ist(base_day_ist: datetime, session_name: str):
    sdef = SESSION_DEFS[session_name]
    sh, sm = sdef["start"]
    eh, em = sdef["end"]

    if session_name == "Previous Day":
        start_ist = (base_day_ist - timedelta(days=1)).replace(hour=sh, minute=sm)
        end_ist   = base_day_ist.replace(hour=eh, minute=em)
    else:
        start_ist = base_day_ist.replace(hour=sh, minute=sm)
        end_ist   = base_day_ist.replace(hour=eh, minute=em)

    start_utc = start_ist.astimezone(pytz.utc)
    end_utc_exclusive = (end_ist + timedelta(minutes=1)).astimezone(pytz.utc)
    return start_utc, end_utc_exclusive

# ========== MT5 CONNECTION ==========
def ensure_mt5():
    if not mt5.initialize(login=ACCOUNT, password=PASSWORD, server=SERVER):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    all_symbols = [s.name for s in mt5.symbols_get()]
    for base in BASE_SYMBOLS:
        match = next((s for s in all_symbols if s.startswith(base)), None)
        if match:
            SYMBOLS.append(match)
            if not mt5.symbol_info(match).visible:
                mt5.symbol_select(match, True)

    account_info = mt5.account_info()
    if account_info:
        print(f"✅ Connected to MT5 | Login: {account_info.login} | Balance: {account_info.balance}")
        print("📊 Using symbols:", SYMBOLS)

# ========== HISTORY & LEVELS ==========
def fetch_rates(symbol: str, date_from_utc: datetime, date_to_utc: datetime):
    total_minutes = int((date_to_utc - date_from_utc).total_seconds() // 60) + 10
    rates = mt5.copy_rates_from(symbol, TIMEFRAME, date_from_utc, total_minutes)
    if rates is None:
        return []
    out = []
    for r in rates:
        t = datetime.utcfromtimestamp(r['time']).replace(tzinfo=pytz.utc)
        if date_from_utc <= t < date_to_utc:
            out.append(r)
    return out

def compute_session_levels_for_day(symbol: str, base_day_ist: datetime):
    levels = {}
    for sname in SESSION_DEFS.keys():
        start_utc, end_utc = session_window_ist(base_day_ist, sname)
        bars = fetch_rates(symbol, start_utc, end_utc)
        if not bars:
            continue
        highs = [b['high'] for b in bars]
        lows = [b['low'] for b in bars]
        levels[sname] = {"high": max(highs), "low": min(lows)}
    return levels

def compute_all_levels(base_day_ist: datetime):
    all_levels = {}
    for sym in SYMBOLS:
        all_levels[sym] = compute_session_levels_for_day(sym, base_day_ist)
    return all_levels

# ========== ALERT THROTTLING ==========
alert_log = defaultdict(list)
ALERT_COOLDOWN_MIN = 30

def allow_alert(key: str, now_ist: datetime) -> bool:
    times = alert_log[key]
    if len(times) < 2:
        return True
    last_t = times[-1]
    return (now_ist - last_t) >= timedelta(minutes=ALERT_COOLDOWN_MIN)

def record_alert(key: str, ts_ist: datetime):
    alert_log[key].append(ts_ist)

# ========== BREAKOUT CHECK ==========
def check_breakouts(levels: dict):
    now_i = to_ist(utc_now())

    for sym in SYMBOLS:
        # get last closed M5 candle
        rates = mt5.copy_rates_from_pos(sym, CHECK_TIMEFRAME, 1, 1)
        if not rates:
            continue
        close_price = rates[0]['close']

        sym_levels = levels.get(sym, {})
        for session_name, lv in sym_levels.items():
            if "high" in lv and close_price > lv["high"]:
                key = f"{sym}|{session_name}|High|Up"
                if allow_alert(key, now_i):
                    remark = f"{session_name} High BreakOut Up"
                    send_telegram(f"Symbol: {sym}\nPoint: {close_price:.5f}\nRemark: {remark}")
                    record_alert(key, now_i)

            if "low" in lv and close_price < lv["low"]:
                key = f"{sym}|{session_name}|Low|Down"
                if allow_alert(key, now_i):
                    remark = f"{session_name} Low BreakOut Down"
                    send_telegram(f"Symbol: {sym}\nPoint: {close_price:.5f}\nRemark: {remark}")
                    record_alert(key, now_i)

# ========== DAILY RESET ==========
def time_until_next_reset(now_ist: datetime) -> float:
    target = now_ist.replace(hour=RESET_HOUR_IST, minute=RESET_MINUTE_IST, second=0, microsecond=0)
    if now_ist >= target:
        target += timedelta(days=1)
    return (target - now_ist).total_seconds()

# ========== MAIN LOOP ==========
def main():
    ensure_mt5()
    base_day = today_ist()
    print(f"ℹ️ Computing session levels for: {base_day.strftime('%Y-%m-%d')}")
    levels = compute_all_levels(base_day)
    print("✅ Levels initialized.")

    send_levels_report(levels)  # send initial daily levels

    now_ist = to_ist(utc_now())
    seconds_to_reset = time_until_next_reset(now_ist)
    next_reset_at = now_ist + timedelta(seconds=seconds_to_reset)
    print(f"🕚 Next daily reset at: {next_reset_at.strftime('%Y-%m-%d %H:%M:%S IST')}")

    while True:
        now_ist = to_ist(utc_now())
        if now_ist >= next_reset_at:
            print(f"\n🔄 Daily reset @ {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
            alert_log.clear()
            base_day = today_ist()
            levels = compute_all_levels(base_day)
            send_levels_report(levels)
            seconds_to_reset = time_until_next_reset(now_ist)
            next_reset_at = now_ist + timedelta(seconds=seconds_to_reset)

        try:
            check_breakouts(levels)
        except Exception as e:
            print(f"⚠️ check_breakouts error: {e}")

        time.sleep(TICK_INTERVAL_SEC)

# ========== ENTRY ==========
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("👋 Exiting...")
    finally:
        mt5.shutdown()
