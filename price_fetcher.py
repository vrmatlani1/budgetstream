import sys
import yfinance as yf
import warnings

# Suppress warnings to keep stdout clean
warnings.filterwarnings("ignore")

def get_price(ticker):
    try:
        # Check if it's an index or stock
        t = yf.Ticker(ticker)
        # Fetch 5 days to be safe over weekends/holidays
        data = t.history(period="5d")
        if not data.empty:
            current_price = data['Close'].iloc[-1]
            
            # Get previous close for pct change
            if len(data) >= 2:
                prev_close = data['Close'].iloc[-2]
            else:
                prev_close = data['Open'].iloc[0]
            
            print(f"{current_price}|{prev_close}")
        else:
            print("NaN|NaN")
    except Exception as e:
        print("NaN|NaN")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_price(sys.argv[1])
