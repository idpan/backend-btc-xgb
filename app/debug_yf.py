
import yfinance as yf
import pandas as pd

def debug_yf():
    print("Downloading BTC-USD data...")
    df = yf.download('BTC-USD', period='5d', interval='1d', auto_adjust=False, progress=False)
    print("\nOriginal Columns:", df.columns.tolist())
    print("Original Index Name:", df.index.name)
    
    if isinstance(df.columns, pd.MultiIndex):
        print("MultiIndex detected. Flattening...")
        df.columns = df.columns.get_level_values(0)
        print("Flattened Columns:", df.columns.tolist())
    
    df_reset = df.reset_index()
    print("Columns after reset_index:", df_reset.columns.tolist())
    
    # Check lower case conversion
    cols_lower = [c.lower() for c in df_reset.columns]
    print("Lower case columns:", cols_lower)

if __name__ == "__main__":
    debug_yf()
