import sys
import os
import math
from datetime import datetime, timezone, timedelta
import pandas as pd
import yfinance as yf
import telebot

# Pengambilan token dari environment variable Railway
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

class SuppressStderr:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self._original_stderr

def safe_int(val, default=0):
    try:
        if isinstance(val, (pd.Series, pd.DataFrame)):
            val = val.iloc[0]
        if pd.isna(val) or math.isnan(float(val)):
            return default
        return int(round(float(val)))
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if isinstance(val, (pd.Series, pd.DataFrame)):
            val = val.iloc[0]
        if pd.isna(val) or math.isnan(float(val)):
            return default
        return float(val)
    except Exception:
        return default

def get_candlestick_pattern(df_last3):
    c1 = df_last3.iloc[0]
    c2 = df_last3.iloc[1]
    c3 = df_last3.iloc[2]

    o1, h1, l1, c1_close = safe_float(c1['Open']), safe_float(c1['High']), safe_float(c1['Low']), safe_float(c1['Close'])
    o2, h2, l2, c2_close = safe_float(c2['Open']), safe_float(c2['High']), safe_float(c2['Low']), safe_float(c2['Close'])
    o3, h3, l3, c3_close = safe_float(c3['Open']), safe_float(c3['High']), safe_float(c3['Low']), safe_float(c3['Close'])

    b1, range1 = abs(c1_close - o1), (h1 - l1)
    b2, range2 = abs(c2_close - o2), (h2 - l2)
    b3, range3 = abs(c3_close - o3), (h3 - l3)

    green1, red1 = c1_close > o1, c1_close < o1
    green2, red2 = c2_close > o2, c2_close < o2
    green3, red3 = c3_close > o3, c3_close < o3

    if green1 and green2 and green3 and c3_close > c2_close > c1_close and o3 > o2 > o1:
        return "Three White Soldiers 🟢🟢🟢 (Bullish Kuat)"
    if red1 and red2 and red3 and c3_close < c2_close < c1_close and o3 < o2 < o1:
        return "Three Black Crows 🔴🔴🔴 (Bearish Kuat)"
    if red1 and (b2 / range2 <= 0.3 if range2 > 0 else True) and green3 and c3_close >= (o1 + c1_close) / 2:
        return "Morning Star 🟢 (Pembalikan Arah Naik)"
    if green1 and (b2 / range2 <= 0.3 if range2 > 0 else True) and red3 and c3_close <= (o1 + c1_close) / 2:
        return "Evening Star 🔴 (Pembalikan Arah Turun)"
    if red1 and green2 and c2_close > o1 and green3 and c3_close > c2_close:
        return "Three Inside Up 🟢 (Konfirmasi Pembalikan Naik)"
    if green1 and red2 and c2_close < o1 and red3 and c3_close < c2_close:
        return "Three Inside Down 🔴 (Konfirmasi Pembalikan Turun)"

    upper_shade3 = h3 - max(o3, c3_close)
    lower_shade3 = min(o3, c3_close) - l3

    if range3 > 0 and b3 / range3 <= 0.1:
        return "Doji 🟡 (Konsolidasi/Netral)"
    if green3 and red2 and o3 <= c2_close and c3_close >= o2:
        return "Bullish Engulfing 🟢 (Sinyal Naik)"
    if red3 and green2 and o3 >= c2_close and c3_close <= o2:
        return "Bearish Engulfing 🔴 (Sinyal Turun)"
    if lower_shade3 >= 2 * b3 and upper_shade3 <= 0.2 * b3:
        return "Hammer 🟢 (Potensi Naik)" if green3 else "Hanging Man 🔴 (Potensi Turun)"
    if upper_shade3 >= 2 * b3 and lower_shade3 <= 0.2 * b3:
        return "Inverted Hammer 🟢 (Potensi Naik)" if green3 else "Shooting Star 🔴 (Potensi Turun)"
    if range3 > 0 and b3 / range3 >= 0.8:
        return "Bullish Marubozu 🟢 (Beli Sangat Kuat)" if green3 else "Bearish Marubozu 🔴 (Jual Sangat Kuat)"

    if c3_close > c2_close > c1_close:
        return "Tren Naik 3 Hari 🟢"
    elif c3_close < c2_close < c1_close:
        return "Tren Turun 3 Hari 🔴"

    return "Bullish Candle 🟢" if green3 else ("Bearish Candle 🔴" if red3 else "Netral 🟡")

def analyze_stock(ticker_symbol):
    ticker = ticker_symbol.upper().strip()
    if not ticker.endswith('.JK'):
        ticker += '.JK'
        
    try:
        waktu_wib = datetime.now(timezone(timedelta(hours=7)))
        waktu_ambil = waktu_wib.strftime("%d-%m-%Y %H:%M:%S WIB")

        with SuppressStderr():
            t = yf.Ticker(ticker)
            df = t.history(period='3mo')
        
        if df.empty or len(df) < 50:
            return f"❌ Data tidak ditemukan atau tidak cukup untuk kode saham: {ticker_symbol.upper()}"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.loc[:, ~df.columns.duplicated()]
        df = df.dropna(subset=['Close'])
        df = df[df['Close'] > 0]

        if len(df) < 50:
            return f"❌ Data transaksi tidak cukup untuk kode saham: {ticker_symbol.upper()}"

        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        low14 = df['Low'].rolling(window=14).min()
        high14 = df['High'].rolling(window=14).max()
        df['%K'] = ((df['Close'] - low14) / (high14 - low14)) * 100
        df['%D'] = df['%K'].rolling(window=3).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        df_1m = df.tail(20)
        close_1m_ago = safe_float(df_1m.iloc[0]['Close'])
        high_1m = safe_float(df_1m['High'].max())
        low_1m = safe_float(df_1m['Low'].min())

        close = safe_float(last['Close'])
        prev_close = safe_float(prev['Close'])
        high_today = safe_float(last['High'])
        low_today = safe_float(last['Low'])

        ma5 = safe_float(last['MA5'])
        ma20 = safe_float(last['MA20'])
        ma50 = safe_float(last['MA50'])

        rsi_today = safe_float(last['RSI'])
        stoch_k = safe_float(last['%K'])
        stoch_d = safe_float(last['%D'])

        vol_today = safe_float(last['Volume'])
        vol_yesterday = safe_float(prev['Volume'])
        vol_ma20 = safe_float(last['Vol_MA20'])
        vol_ratio = (vol_today / vol_ma20) if vol_ma20 > 0 else 1.0

        change_1d = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
        change_1m = ((close - close_1m_ago) / close_1m_ago * 100) if close_1m_ago > 0 else 0.0

        df_last3 = df.tail(3)
        candle_pattern = get_candlestick_pattern(df_last3)
        clean_ticker = ticker.replace('.JK', '')

        if change_1m > 10:
            trend_desc = f"Bullish Kuat (+{change_1m:.2f}%)"
        elif change_1m > 0:
            trend_desc = f"Bullish Moderat (+{change_1m:.2f}%)"
        else:
            trend_desc = f"Konsolidasi/Bearish ({change_1m:.2f}%)"

        if ma5 > ma20 > ma50:
            ma_desc = "Bullish (MA5 &gt; MA20 &gt; MA50)"
        elif ma5 > ma20:
            ma_desc = "Pembalikan Arah (MA5 &gt; MA20)"
        else:
            ma_desc = "Tren Melemah (MA5 &lt; MA20)"

        if rsi_today >= 70:
            rsi_desc = "🔴 Overbought"
        elif rsi_today <= 30:
            rsi_desc = "🟢 Oversold"
        else:
            rsi_desc = "🟡 Netral"

        if stoch_k >= 80:
            stoch_desc = "🔴 Overbought"
        elif stoch_k <= 20:
            stoch_desc = "🟢 Oversold"
        else:
            stoch_desc = "🟡 Netral"

        if vol_ratio >= 1.5 and change_1d > 0:
            flow_desc = "🟢 AKUMULASI BESAR (High Volume Buying)"
        elif vol_ratio >= 1.5 and change_1d < 0:
            flow_desc = "🔴 DISTRIBUSI BESAR (High Volume Selling)"
        elif vol_ratio < 0.8:
            flow_desc = "⚪ VOLUME SEPI (Konsolidasi/Sepi Transaksi)"
        else:
            flow_desc = "🟡 NORMAL (Transaksi Stabil)"

        entry_low = safe_int(min(ma20, ma5 * 0.98))
        entry_high = safe_int(ma5)
        tp1 = safe_int(close * 1.05)
        tp2 = safe_int(close * 1.10)
        sl = safe_int(ma20 * 0.98)

        msg = "<pre>"
        msg += f"==============================\n"
        msg += f"   ANALISIS TEKNIKAL SAHAM: {clean_ticker}\n"
        msg += f"==============================\n"
        msg += f"🕒 Waktu Ambil : {waktu_ambil} (Delay 15 Menit)\n"
        msg += f"🌐 Sumber Data : Yahoo Finance (yfinance)\n"
        msg += f"------------------------------\n\n"
        msg += f"1. RINGKASAN DATA HARI INI\n"
        msg += f"   • Harga Terakhir : Rp{safe_int(close):,} ({change_1d:+.2f}%)\n"
        msg += f"   • High / Low 1D  : Rp{safe_int(high_today):,} / Rp{safe_int(low_today):,}\n"
        msg += f"   • Pola 3 Candle  : {candle_pattern}\n"
        msg += f"   • Volume Hari Ini: {safe_int(vol_today):,} lembar\n"
        msg += f"   • Volume Kemarin : {safe_int(vol_yesterday):,} lembar\n"
        msg += f"   • Perubahan 1M   : {change_1m:+.2f}% (dari Rp{safe_int(close_1m_ago):,})\n"
        msg += f"   • High / Low 1M  : Rp{safe_int(high_1m):,} / Rp{safe_int(low_1m):,}\n"
        msg += f"   • MA5  (Mingguan): Rp{safe_int(ma5):,}\n"
        msg += f"   • MA20 (Bulanan) : Rp{safe_int(ma20):,}\n"
        msg += f"   • MA50 (2.5 Bln) : Rp{safe_int(ma50):,}\n\n"
        msg += f"2. ANALISIS TREN & OSCILLATOR\n"
        msg += f"   • Tren Utama : {trend_desc}\n"
        msg += f"   • Struktur MA: {ma_desc}\n"
        msg += f"   • RSI (14)   : {rsi_today:.1f} - {rsi_desc}\n"
        msg += f"   • Stochastic : %K {stoch_k:.1f} / %D {stoch_d:.1f} - {stoch_desc}\n\n"
        msg += f"3. INDIKATOR VOLUMETRIK & FLOW\n"
        msg += f"   • Vol MA20     : {safe_int(vol_ma20):,} (Rata-rata Bulanan)\n"
        msg += f"   • Rasio Volume : {vol_ratio:.2f}x rata-rata\n"
        msg += f"   • Status Flow  : {flow_desc}\n\n"
        msg += f"4. TRADING PLAN\n"
        msg += f"   • Strategi  : Buy on Weakness\n"
        msg += f"   • Area Beli : Rp{entry_low:,} - Rp{entry_high:,}\n"
        msg += f"   • Target 1  : Rp{tp1:,} (+5%)\n"
        msg += f"   • Target 2  : Rp{tp2:,} (+10%)\n"
        msg += f"   • Stop Loss : Rp{sl:,} (Di bawah MA20)\n"
        msg += f"=============================="
        msg += "</pre>"

        return msg

    except Exception as e:
        return f"❌ Terjadi kesalahan saat memproses saham {ticker_symbol}: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Halo! Kirimkan kode saham IHSG (contoh: BMRI, BBCA, TLKM) untuk menganalisis teknikalnya.")

@bot.message_handler(func=lambda message: True)
def handle_stock_request(message):
    kode = message.text.strip()
    if kode.startswith('/'):
        return

    loading_msg = bot.reply_to(message, f"Sedang menganalisis saham {kode.upper()}...\nMohon tunggu sebentar ⏳")
    hasil_analisis = analyze_stock(kode)
    bot.edit_message_text(hasil_analisis, chat_id=loading_msg.chat.id, message_id=loading_msg.message_id, parse_mode='HTML')

if __name__ == '__main__':
    print("Bot Telegram Screener Saham berjalan...")
    
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Catatan Webhook: {e}")
        
    bot.infinity_polling()
