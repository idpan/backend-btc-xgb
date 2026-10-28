import pandas as pd
import numpy as np
import pandas_ta as ta
import joblib
import yfinance as yf
from datetime import datetime
from helper.db import insert_df_to_db

def get_btc_dataset():
    df = yf.download('BTC-USD', period='351d', interval='1d', auto_adjust=False, progress=False)

    #flattening data
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def feature_engineering():
        df = get_btc_dataset().copy()

        # A. Momentum & Trend
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_Signal'] = macd['MACDs_12_26_9']
        df['D_EMA20'] = df['Close'] / ta.ema(df['Close'], length=20)
        df['D_EMA200'] = df['Close'] / ta.ema(df['Close'], length=200)

        # B. Trend Strength (ADX)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['ADX'] = adx_df['ADX_14']

        # C. Volatility (BBW & BBP)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        df['BBW'] = (bbands['BBU_20_2.0_2.0'] - bbands['BBL_20_2.0_2.0']) / bbands['BBM_20_2.0_2.0']
        df['BBP'] = (df['Close'] - bbands['BBL_20_2.0_2.0']) / (bbands['BBU_20_2.0_2.0'] - bbands['BBL_20_2.0_2.0'])

        # D. Volume (MFI & Vol_Chg)
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['Vol_Chg'] = df['Volume'].pct_change()

        # E. Time Features
        df['day_of_week'] = df.index.dayofweek
        df['month'] = df.index.month
        df['Day_Sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['Day_Cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        df['Mon_Sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['Mon_Cos'] = np.cos(2 * np.pi * df['month'] / 12)

        # F. Log Return
        df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
        

        return df

import joblib
import pandas as pd

def get_prediction(df):
    try:
        # 1. Load Model & Columns (Pastikan file berada di folder /backend)
        # Ganti dengan path yang benar jika file tidak di root folder
        model = joblib.load('btc_price_direction_prediction_model.pkl')
        feature_cols = joblib.load('feature_columns.pkl')

        # Filter data frame input
        df_clean = df.dropna(subset=feature_cols)

        # Ambil satu baris terakhir untuk input prediksi
        input_row = df_clean[feature_cols].tail(1)
        
        if input_row.empty:
            print("❌ Error: Input row kosong setelah dropna().")
            return None

        # Lakukan Prediksi
        pred = model.predict(input_row)[0]
        proba = model.predict_proba(input_row)[0]
        confidence_level = proba.max()

        # --- Bagian yang Diperbaiki ---
        # Buat dictionary dengan koma yang benar
        prediction_result_dict = {
            'date': input_row.index[0].date().isoformat(),
            'direction' : 'up' if pred == 1 else 'down', # Sesuaikan logika 'pred == 1' jika diperlukan
            'confidence' : round(confidence_level, 2),
        }
        
        # Konversi dictionary ke DataFrame dengan orientasi yang benar (index=[0] memaksa single row)
        df_prediction_result = pd.DataFrame([prediction_result_dict])
        insert_df_to_db(df_prediction_result,'prediction_history')
        print(df_prediction_result)
        
        # Kembalikan dictionary yang sudah bersih, siap untuk API atau penyimpanan DB
        return prediction_result_dict
       

    except Exception as e:
        print(f"❌ Error: Terjadi masalah dalam get_prediction -> {e}")
        return None # Kembalikan None jika terjadi error

# Panggil fungsi (asumsikan feature_engineering() mengembalikan DataFrame yang valid)
get_prediction(feature_engineering())

