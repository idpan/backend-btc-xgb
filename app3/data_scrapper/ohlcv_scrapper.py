import yfinance as yf
import pandas as pd


def get_btc_dataset():

    df = yf.download('BTC-USD', period='351d', interval='1d', auto_adjust=False, progress=False)

    #flattening data
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df
