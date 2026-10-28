import pandas as pd
import numpy as np
import pandas_ta as ta
import joblib
import yfinance as yf
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables dari folder backend
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from db_manager import DatabaseManager
import json
import xgboost as xgb
from xgboost import XGBClassifier
    

def get_btc_dataset():

    if not os.getenv("OFFLINE_MODE", "False").lower() in ("true", "1", "t"):
        try:
            df = yf.download('BTC-USD', period='351d', interval='1d', auto_adjust=False, progress=False)
            if df.empty:
                csv_path = os.path.join(os.path.dirname(__file__), 'btc_dataset.csv')
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        except Exception:
            csv_path = os.path.join(os.path.dirname(__file__), 'btc_dataset.csv')
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    else:
        csv_path = os.path.join(os.path.dirname(__file__), 'btc_dataset.csv')
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

    # Buang baris terakhir (data hari ini yang belum closed)
    df = df.iloc[:-1]
    
    #flattening data
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # upsert ohlcv data to database
    db = DatabaseManager()

    if not df.empty:
        db.write_ohlcv_to_db(df)
    
    return df


def feature_engineering():
    df = get_btc_dataset().copy()
   
    # Pastikan tipe data numeric untuk menghindari error pandas_ta
    cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- A. MOMENTUM ---
    df['RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    df['MACD']        = macd['MACD_12_26_9']
    df['MACD_Signal'] = macd['MACDs_12_26_9']
    df['MACD_Hist']   = macd['MACDh_12_26_9']

    # --- B. TREN & VOLATILITAS ---
    df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
    df['ATR']     = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df['EMA_20']  = ta.ema(df['Close'], length=20)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['D_EMA20']  = df['Close'] / df['EMA_20']
    df['D_EMA200'] = df['Close'] / df['EMA_200']

    bbands    = ta.bbands(df['Close'], length=20, std=2)
    df['BBW'] = (bbands['BBU_20_2.0_2.0'] - bbands['BBL_20_2.0_2.0']) / bbands['BBM_20_2.0_2.0']

    # --- C. VOLUME ---
    df['OBV']     = ta.obv(df['Close'], df['Volume'])
    df['Vol_Chg'] = df['Volume'].pct_change()

    # --- D. WAKTU (Cyclical Encoding) ---
    df.index = pd.to_datetime(df.index)
    df['day_of_week'] = df.index.dayofweek
    df['month']       = df.index.month
    df['Day_Sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['Day_Cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['Mon_Sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['Mon_Cos'] = np.cos(2 * np.pi * df['month'] / 12)

    # ============================================================
    # 3. CONTINUOUS REGIME FEATURES
    # ============================================================

    # Regime 1: Seberapa jauh harga dari EMA200
    # Positif = bull territory, negatif = bear territory
    # Lebih informatif dari binary 0/1
    df['regime_trend_strength'] = (df['Close'] - df['EMA_200']) / df['EMA_200']

    # Regime 2: Volatility regime — ATR relatif terhadap rata-rata historisnya
    # > 1 = volatility sedang ekspansi, < 1 = kontraksi
    df['regime_vol_ratio'] = df['ATR'] / df['ATR'].rolling(50).mean()

    # Regime 3: ADX — kekuatan trend secara continuous
    # Semakin tinggi = semakin kuat trendnya (tidak peduli arah)
    adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    df['regime_adx'] = adx['ADX_14']

    # Regime 4: RSI normalized ke [-1, 1]
    # Lebih halus dari binary overbought/oversold
    df['regime_rsi_norm'] = (df['RSI'] - 50) / 50

    # Regime 5: EMA spread — jarak antara EMA20 dan EMA200
    # Positif dan besar = momentum bull kuat
    # Negatif = bearish
    df['regime_ema_spread'] = (df['EMA_20'] - df['EMA_200']) / df['EMA_200']

    # Regime 6: Volatility trend — apakah volatility sedang naik atau turun
    # Rolling std of ATR changes
    df['regime_vol_trend'] = df['ATR'].pct_change().rolling(10).mean()


    return df


def get_prediction():
    try:
        model_path = os.path.join(os.path.dirname(__file__), '../ml_model/v2_xgboost_btc_model.json')
        model = XGBClassifier()
        model.load_model(model_path)
        
        feature_cols = model.feature_names_in_.tolist()
        df = feature_engineering()

        df_clean = df.dropna(subset=feature_cols)

        if df_clean.empty:
            print("❌ Error: df_clean kosong setelah dropna().")
            return None

        input_row = df_clean[feature_cols].tail(1) 
        dataset_date = input_row.index[0].date()
        
        # Ambil harga penutupan terakhir (Previous Close)
        previous_close = float(df_clean['Close'].iloc[-1])

        X_input = input_row.values 
        
        pred = model.predict(X_input)[0]
        proba = model.predict_proba(X_input)[0]
        
        # ------------------------------------------------------------
        # Ekstraksi Detail Trees & Margin untuk XGBoost
        # ------------------------------------------------------------
        booster = model.get_booster()
        # Ambil prediksi dalam bentuk margin raw (sebelum sigmoid)
        # raw_margin = float(booster.predict(xgb.DMatrix(input_row), output_margin=True)[0])
        # Ubah bagian ini di engine_2.py:
        raw_margin = float(booster.predict(xgb.DMatrix(input_row, feature_names=feature_cols), output_margin=True)[0])
        # Dapatkan struktur dump tree dari XGBoost
        dump_list = booster.get_dump(dump_format='json')
        trees_detail = []
        
        for tree_id, tree_json_str in enumerate(dump_list):
            tree_data = json.loads(tree_json_str)
            # Telusuri tree untuk menemukan leaf node
            curr = tree_data
            while 'leaf' not in curr:
                split_feat = curr['split']
                split_val = curr['split_condition']
                feat_val = input_row[split_feat].iloc[0]
                
                # Beralih ke child node berdasarkan kondisi split
                if feat_val < split_val:
                    curr = next(child for child in curr['children'] if child['nodeid'] == curr['yes'])
                else:
                    curr = next(child for child in curr['children'] if child['nodeid'] == curr['no'])
            
            trees_detail.append({
                "id": tree_id,
                "leafId": curr['nodeid'],
                "leafScore": round(float(curr['leaf']), 8)
            })

        # Hitung kalkulasi margin & probabilitas dalam persentase
        prob_up_pct = round(float(1 / (1 + np.exp(-raw_margin))) * 100, 2)

        # Format daftar fitur
        features_list = [
            {"name": col, "value": round(float(input_row[col].iloc[0]), 4)}
            for col in feature_cols
        ]

        prediction_result_dict = {
            'dataset_date': dataset_date,
            'direction': 'up' if pred == 1 else 'down',
            'confidence': prob_up_pct,
            'previous_close': previous_close,
            'calculation': {
                'base_margin': 0.0,
                'total_leaf_score': round(raw_margin, 4),
                'margin_aktar': round(raw_margin, 4),
                'probability_up': prob_up_pct
            },
            'features': features_list,
            'trees': trees_detail
        }
        
        return prediction_result_dict

    except Exception as e:
        print(f"❌ Error dalam get_prediction -> {e}")
        return None