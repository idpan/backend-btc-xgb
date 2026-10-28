import pandas as pd
import yfinance as yf

def get_btc_dataset():
    # 1. Download data
    df = yf.download('BTC-USD', period='351d', interval='1d', auto_adjust=False, progress=False)
    
    # 2. Buang baris terakhir (data hari ini yang belum closed)
    # df = df.iloc[:-1]
    
    # 3. Flattening data jika kolomnya MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 4. Simpan ke file CSV
    # Menentukan nama file, misalnya 'btc_dataset.csv'
    nama_file = 'btc_dataset.csv'
    df.to_csv(nama_file, index=True) # index=True agar kolom Tanggal (Date) ikut tersimpan
    print(f"Data berhasil disimpan ke {nama_file}")
    
    # --- Kode Database Anda (Tetap dijalankan jika masih butuh dimasukkan ke DB) ---
    # db = DatabaseManager()
    # if not df.empty:
    #     db.write_ohlcv_to_db(df)
    # ------------------------------------------------------------------------------
    
    return df

get_btc_dataset()