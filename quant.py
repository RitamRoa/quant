import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- CONFIG ---
CSV_FILE = "nifty100.csv"
INITIAL_CAPITAL = 100000
RISK_PER_TRADE_PCT = 0.01 
TRAIL_STOP_PCT = 0.02
MAX_HOLDING_DAYS = 10 
MAX_OPEN_POSITIONS = 5 
FORCE_BYPASS_MARKET_FILTER = False 

def add_indicators(df):
    if df.empty or len(df) < 20: return pd.DataFrame()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
    df['SMA20'] = df['Close'].rolling(20).mean()
    df['Std'] = df['Close'].rolling(20).std()
    df['Lower'] = df['SMA20'] - (2 * df['Std'])
    df['Upper'] = df['SMA20'] + (1.5 * df['Std'])
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
    return df.dropna()

def get_clean_symbol(symbol):
    return str(symbol).strip().replace("M&M", "M%26M").replace("M_M", "M%26M") + ".NS"

def run_pro_simulation():
    try:
        raw_data = pd.read_csv(CSV_FILE)
        symbols_data = raw_data[['Symbol', 'Sector_Index']].drop_duplicates()
        unique_sectors = symbols_data['Sector_Index'].unique()
    except Exception as e:
        print(f"CSV Error: {e}")
        return

    # 1. Market Health Check
    nifty = yf.download("^NSEI", period="100d", interval="1d", progress=False)
    if isinstance(nifty.columns, pd.MultiIndex): nifty.columns = nifty.columns.droplevel(1)
    market_bullish = nifty['Close'].iloc[-1] > nifty['Close'].rolling(50).mean().iloc[-1]
    nifty_3d_ret = nifty['Close'].pct_change(3).iloc[-1]
    
    # 2. Pre-fetch Sector Data
    sector_bullish_map = {}
    for sector_ticker in unique_sectors:
        if not isinstance(sector_ticker, str) or sector_ticker == 'nan': continue
        sdf = yf.download(sector_ticker, period="100d", interval="1d", progress=False)
        if not sdf.empty:
            if isinstance(sdf.columns, pd.MultiIndex): sdf.columns = sdf.columns.droplevel(1)
            sector_bullish_map[sector_ticker] = sdf['Close'].iloc[-1] > sdf['Close'].rolling(50).mean().iloc[-1]

    current_cap = INITIAL_CAPITAL
    scanner_results = []
    log_entries = [] # Buffer for the text file

    header = f"🚀 Market Status: {'BULLISH' if market_bullish else 'BEARISH'} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    print(header)
    log_entries.append(header + "\n" + "-"*50)

    for idx, row in symbols_data.iterrows():
        symbol, sector_idx = row['Symbol'], row['Sector_Index']
        try:
            df = add_indicators(yf.download(get_clean_symbol(symbol), period="60d", interval="1d", progress=False))
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            if df.empty: continue

            latest = df.iloc[-1]
            is_sec_bull = sector_bullish_map.get(sector_idx, False)
            
            # Distance to Band
            dist = ((latest['Close'] / latest['Lower']) - 1) * 100
            
            # Calculate RS Trend (3-day relative to Nifty)
            stock_3d_ret = df['Close'].pct_change(3).iloc[-1]
            rs_trend = (stock_3d_ret - nifty_3d_ret) * 100

            scanner_results.append({
                "Symbol": symbol, "RSI": latest['RSI'], "Dist": dist, "Price": latest['Close'], "S_Bull": is_sec_bull, "RS_Trend": rs_trend
            })
        except: continue

    # Process Heat Map with Price Targets
    s_df = pd.DataFrame(scanner_results).sort_values(by="RSI").head(10)
    
    print("\n🔥 NIFTY 100 HEAT MAP (With Leader Analysis)")
    print("-" * 105)
    print(f"{'SYMBOL':<12} | {'RSI':<6} | {'DIST':<8} | {'SECTOR':<8} | {'RS TREND':<10} | {'EXIT TARGET':<12}")
    print("-" * 105)
    
    for _, s in s_df.iterrows():
        # Target Price calculation
        target_price = s['Price'] * (1 + (abs(s['Dist'])/100) + 0.03)
        
        # Calculate RS Trend (Simple 3-day logic)
        # s['RS_Trend'] is now part of the scanner_results logic
        trend_icon = "📈 LEADER" if s['RS_Trend'] > 0 else "📉 LAGGARD"
        
        line = f"{s['Symbol']:<12} | {s['RSI']:<6.2f} | {s['Dist']:>+7.2f}% | {'✅' if s['S_Bull'] else '❌':<8} | {trend_icon:<10} | ₹{target_price:>10.2f}"
        print(line)
        log_entries.append(line)

    # --- SAVE LOG TO FILE ---
    if not os.path.exists('logs'): os.makedirs('logs')
    filename = f"logs/scan_{datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(log_entries))
    print(f"\n💾 Daily log saved to: {filename}")

    # --- PAPER TRADE PERFORMANCE LOG ---
    # This assumes you entered at Sunday's RSI 10:59 prices
    if not os.path.exists('logs/portfolio.csv'):
        pd.DataFrame(columns=['Date', 'Symbol', 'Entry', 'Current', 'PnL_Pct']).to_csv('logs/portfolio.csv', index=False)
    
    # We will start recording from tomorrow's first 'Green Tick' (✅)
    print("\n📝 PAPER TRADE MODE: Ready to record the first 'Green Tick' (✅) Signal.")

if __name__ == "__main__":
    run_pro_simulation()