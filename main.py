from datetime import datetime
import time
import pytz
import requests
import yfinance as yf

# ================= إعدادات البوت =================
BOT_TOKEN = "9011103343:AAEiDDLP0-kWe4kcOC6GPikMPoFn6a8pIfk"
CHAT_ID = "2038409393"

SYMBOLS = {"NQ=F": "NAS100", "ES=F": "S&P 500", "GC=F": "Gold"}

active_setups = {}


def send_alert(message):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message}
  try:
    requests.post(url, json=payload, timeout=5)
  except Exception as e:
    print(f"Error: {e}")


def is_ny_session():
  ny_tz = pytz.timezone("America/New_York")
  now_ny = datetime.now(ny_tz)
  if now_ny.weekday() > 4:
    return False
  start = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
  end = now_ny.replace(hour=11, minute=30, second=0, microsecond=0)
  return start <= now_ny <= end


def get_1h_bias(ticker):
  try:
    df_1h = yf.download(
        tickers=ticker, period="3d", interval="1h", progress=False
    )
    if df_1h is None or len(df_1h) < 10:
      return None

    highs = df_1h["High"].squeeze()
    lows = df_1h["Low"].squeeze()
    closes = df_1h["Close"].squeeze()
    opens = df_1h["Open"].squeeze()

    last_high = float(highs.iloc[-6:-1].max())
    last_low = float(lows.iloc[-6:-1].min())
    recent_close = float(closes.iloc[-2])

    if recent_close > last_high:
      return "BULLISH"
    elif recent_close < last_low:
      return "BEARISH"
    return "BULLISH" if recent_close > float(opens.iloc[-5]) else "BEARISH"
  except Exception as e:
    print(f"Bias error {ticker}: {e}")
    return None


def track_market():
  if not is_ny_session():
    return

  for ticker, name in SYMBOLS.items():
    try:
      bias = get_1h_bias(ticker)
      if not bias:
        continue

      df_15m = yf.download(
          tickers=ticker, period="1d", interval="15m", progress=False
      )
      if df_15m is None or len(df_15m) < 3:
        continue

      highs_15 = df_15m["High"].squeeze()
      lows_15 = df_15m["Low"].squeeze()
      closes_15 = df_15m["Close"].squeeze()

      c1_high = float(highs_15.iloc[-3])
      c1_low = float(lows_15.iloc[-3])

      c2_high = float(highs_15.iloc[-2])
      c2_low = float(lows_15.iloc[-2])
      c2_close = float(closes_15.iloc[-2])
      c2_time = str(df_15m.index[-2])

      if (
          bias == "BEARISH"
          and c2_high > c1_high
          and c1_low < c2_close < c1_high
      ):
        trigger_level = c2_low
        setup_id = f"{ticker}_SELL_{c2_time}"

        df_1m = yf.download(
            tickers=ticker, period="1d", interval="1m", progress=False
        )
        if df_1m is not None and not df_1m.empty:
          lows_1m = df_1m["Low"].squeeze()
          current_low = float(lows_1m.iloc[-1])
          if current_low < trigger_level and setup_id not in active_setups:
            send_alert(f"إشارة بيع - {name}")
            active_setups[setup_id] = True

      elif (
          bias == "BULLISH"
          and c2_low < c1_low
          and c1_low < c2_close < c1_high
      ):
        trigger_level = c2_high
        setup_id = f"{ticker}_BUY_{c2_time}"

        df_1m = yf.download(
            tickers=ticker, period="1d", interval="1m", progress=False
        )
        if df_1m is not None and not df_1m.empty:
          highs_1m = df_1m["High"].squeeze()
          current_high = float(highs_1m.iloc[-1])
          if current_high > trigger_level and setup_id not in active_setups:
            send_alert(f"إشارة شراء - {name}")
            active_setups[setup_id] = True

    except Exception as e:
      print(f"Error {name}: {e}")


if __name__ == "__main__":
  while True:
    track_market()
    time.sleep(60)
