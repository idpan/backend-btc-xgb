import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
# from sqlalchemy.dialects import mysql # Tidak diperlukan untuk kode ini

class DatabaseManager:
    # ... (Properti db_host, db_user, dll. tetap sama) ...
    db_host = 'localhost'
    db_user = 'root'
    db_password = ''
    db_name = 'btc_predict_app'

    def __init__(self):
        self.connection_string = f'mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}'
        self.engine = create_engine(self.connection_string)

    # ... (Fungsi read_table_to_df tetap sama) ...
    def read_table_to_df(self, table_name, index_col=None):
        """Membaca tabel SQL dan mengembalikan Pandas DataFrame."""
        try:
            df = pd.read_sql_table(table_name, con=self.engine, index_col=index_col)
            return df
        except Exception as e:
            print(f"❌ DB Read Error: {e}")
            return pd.DataFrame()

    def write_ohlcv_to_db(self, df, table_name):
        """
        Menulis Pandas DataFrame ke tabel MySQL menggunakan UPSERT (ON DUPLICATE KEY UPDATE).
        """
        
        # 1. Pastikan 'Date' menjadi kolom, bukan index
        if df.index.name == 'Date' or 'Date' not in df.columns:
            df = df.reset_index()

        # 2. STANDARISASI NAMA KOLOM
        # Ini memastikan 'Adj Close' menjadi 'Adj_Close' agar sesuai dengan SQL template
        df.columns = [c.replace(' ', '_') for c in df.columns]
        df.columns = [c.lower() for c in df.columns ]
        # 3. SQL Template (Gunakan format :key untuk SQLAlchemy)
        upsert_query_template = text(f"""
            INSERT INTO {table_name} (date, adj_close, close, high, low, open, volume)
            VALUES (:date, :adj_close, :close, :high, :low, :open, :volume)
            ON DUPLICATE KEY UPDATE
                adj_close = VALUES(adj_close),
                close = VALUES(close),
                high = VALUES(high),
                low = VALUES(low),
                open = VALUES(open),
                volume = VALUES(volume);
        """)

        try:
            with self.engine.connect() as connection:
                # 4. Konversi ke list of dicts
                list_of_dicts = df.to_dict(orient='records')
                
                # Eksekusi batch
                connection.execute(upsert_query_template, list_of_dicts)
                connection.commit() 
                print(f"✅ Data UPSERT-ed to MySQL table '{table_name}' successfully.")
                
        except Exception as e:
            print(f"❌ DB Write Error using MySQL UPSERT: {e}")
            raise e