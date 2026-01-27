import yfinance as yf
import pandas as pd
import numpy as np
import sys

def analyze_stock(ticker_input):
    symbol = ticker_input.strip().upper()
    if not symbol.endswith(".NS"):
        symbol += ".NS"
    
    print(f"\n🔍 Analyzing {symbol} (Warren Buffett Style Valuation)...")
    stock = yf.Ticker(symbol)
    
    # --- 1. Data Collection ---
    print("⏳ Fetching financial data...")
    financials = stock.income_stmt
    
    if financials.empty:
        print("❌ Error: No financial data found for this ticker.")
        return

    eps_row = None
    possible_names = ['Diluted EPS', 'Basic EPS']
    
    for name in possible_names:
        if name in financials.index:
            eps_row = financials.loc[name]
            break
            
    if eps_row is None:
        print("❌ Error: Could not find 'Diluted EPS' or 'Basic EPS' in financials.")
        return

    # Sort chronological (Oldest -> Newest) and clean NaNs
    eps_data = eps_row.sort_index(ascending=True).dropna()
    years_available = len(eps_data)
    
    if years_available < 2:
        print("❌ Error: Not enough data points for CAGR calculation.")
        return
        
    print(f"✅ Found {years_available} years of EPS data ({eps_data.index[0].year}-{eps_data.index[-1].year}).")
    print(f"   EPS Data: {eps_data.values}")

    # --- 2. CAGR Calculation (Normalized via Linear Regression) ---
    cagr = 0.05
    n_points = len(eps_data)
    
    if n_points >= 2:
        x = np.arange(n_points)
        y = eps_data.values
        
        # Fit linear regression (y = mx + c) to smooth out volatility
        slope, intercept = np.polyfit(x, y, 1)
        
        # Determine normalized start and end values from the trendline
        reg_start = intercept
        reg_end = slope * (n_points - 1) + intercept
        
        print(f"   Trendline: Start={reg_start:.2f}, End={reg_end:.2f}, Slope={slope:.2f}")

        if reg_start > 0 and reg_end > 0:
            cagr = (reg_end / reg_start) ** (1 / (n_points - 1)) - 1
        elif slope > 0:
             # Positive slope but negative start/end intercept issues
             cagr = 0.05
             print("⚠️ Trend positive but intercepts negative. Defaulting to 5%.")
        else:
             cagr = 0.0
             print("⚠️ Negative trend line. Future growth assumed 0%.")

    if np.isnan(cagr): cagr = 0.05
    print(f"📈 Normalized EPS CAGR: {cagr:.2%}")

    # --- 3. P/E Ratio Logic ---
    current_pe = stock.info.get('trailingPE')
    hist = stock.history(period="10y")
    
    # Ensure timezone naive for matching
    if hist.index.tz is not None:
        hist.index = hist.index.tz_localize(None)
    
    # Normalize EPS dates
    eps_dates = pd.to_datetime(eps_data.index)
    if eps_dates.tz is not None:
        eps_dates = eps_dates.tz_localize(None)
    
    if current_pe is None:
        try:
            curr_price = hist['Close'].iloc[-1]
            current_pe = curr_price / end_eps if end_eps > 0 else 15.0
        except:
            current_pe = 15.0

    pe_ratios = []
    # Calculate historical P/E based on the EPS dates we have
    for i in range(len(eps_data)):
        date = eps_dates[i]
        eps_val = float(eps_data.iloc[i])
        
        if eps_val <= 0: continue
        try:
            # Locate index of date
            idx = hist.index.get_indexer([date], method='nearest')[0]
            if idx != -1:
                price_at_date = hist['Close'].iloc[idx]
                pe = price_at_date / eps_val
                if 0 < pe < 150: 
                    pe_ratios.append(pe)
        except Exception as e:
            pass
            
    if pe_ratios:
        avg_pe = np.mean(pe_ratios)
    else:
        avg_pe = current_pe 
        
    projected_pe = min(current_pe, avg_pe)
    if projected_pe < 5: projected_pe = 5 
    
    print(f"📊 P/E Analysis: Current={current_pe:.2f}, Average ({len(pe_ratios)}y)={avg_pe:.2f} -> Projected={projected_pe:.2f}")

    # --- 4. Projections (10 Years) ---
    end_eps = float(eps_data.iloc[-1])
    base_eps = end_eps
    future_eps = base_eps * ((1 + cagr) ** 10)
    projected_price = future_eps * projected_pe
    
    current_annual_dividend = stock.info.get('dividendRate')
    
    if current_annual_dividend is None:
        divs = stock.dividends
        if not divs.empty:
            cutoff = pd.Timestamp.now() - pd.DateOffset(days=365)
            if divs.index.tz is not None:
                cutoff = cutoff.tz_localize(divs.index.tz)
            last_year_divs = divs[divs.index > cutoff]
            current_annual_dividend = last_year_divs.sum()
        else:
            current_annual_dividend = 0.0
            
    # Calculate Total Dividends (Growing at CAGR)
    projected_dividends = []
    for i in range(1, 11):
        d_val = current_annual_dividend * ((1 + cagr) ** i)
        projected_dividends.append(d_val)
        
    total_dividends = sum(projected_dividends)
    
    # --- 5. Valuation ---
    future_value = projected_price + total_dividends
    discount_rate = 0.15 
    yrs = 10
    intrinsic_value = future_value / ((1 + discount_rate) ** yrs)
    
    current_price = hist['Close'].iloc[-1]
    
    # --- 6. Output Table ---
    print("\n" + "="*60)
    print(f"💎 VALUATION RESULTS: {symbol}")
    print("="*60)
    
    results = [
        ["Metric", "Value"],
        ["-"*30, "-"*25],
        [f"EPS CAGR ({years_available-1}y)", f"{cagr:.2%}"],
        ["Current Diluted EPS", f"₹{base_eps:.2f}"],
        ["Projected P/E (Lower of Avg/Curr)", f"{projected_pe:.2f}"],
        ["Future EPS (10y)", f"₹{future_eps:.2f}"],
        ["Projected Stock Price (10y)", f"₹{projected_price:.2f}"],
        ["Total Dividends (10y Est.)", f"₹{total_dividends:.2f}"],
        ["Future Value (Price + Divs)", f"₹{future_value:.2f}"],
        ["-"*30, "-"*25],
        ["Intrinsic Value (Buy Price)", f"₹{intrinsic_value:.2f}"],
        ["Current Market Price", f"₹{current_price:.2f}"],
        ["Margin of Safety / Upside", f"{(intrinsic_value/current_price - 1):.2%}"]
    ]
    
    for row in results:
        print(f"{row[0]:<35} | {row[1]:<15}")
        
    print("="*60)
    
    if current_price <= intrinsic_value:
        print("✅ VERDICT: UNDERVALUED (Buy Candidate)")
    elif current_price <= intrinsic_value * 1.1:
        print("⚠️ VERDICT: FAIRLY VALUED (Watch)")
    else:
        print("❌ VERDICT: OVERVALUED (Wait for Dip)")
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    else:
        ticker = input("Enter Stock Symbol (e.g., RELIANCE): ")
    
    if ticker:
        analyze_stock(ticker)
