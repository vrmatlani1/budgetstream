import sys
import yfinance as yf
import warnings

# Suppress warnings to keep stdout clean
warnings.filterwarnings("ignore")

def get_price(ticker):
    try:
        # Check if it's an index or stock
        t = yf.Ticker(ticker)
        data = t.history(period="1d")
        if not data.empty:
            # We want Close, Open for indices, just Close for stock
            close_price = data['Close'].iloc[-1]
            try:
                open_price = data['Open'].iloc[0]
            except:
                open_price = close_price
            
            print(f"{close_price}|{open_price}")
        else:
            print("NaN|NaN")
    except Exception as e:
        print("NaN|NaN")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_price(sys.argv[1])
