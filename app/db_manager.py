import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
from typing import Literal  
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables dari folder backend
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

class DatabaseManager:
    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")

    # db_host = 'localhost'
    # db_user = 'root'
    # db_password = ''
    # db_name = 'btc_predict_app'

    def __init__(self):
        try:
            self.connection_string = f'mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}/{self.db_name}'
            self.engine = create_engine(self.connection_string)
            with self.engine.connect() as conn:
                pass
            self.is_sqlite = False
        except Exception:
            db_path = os.path.join(os.path.dirname(__file__), 'btc_predict_app.db')
            self.connection_string = f'sqlite:///{db_path}'
            self.engine = create_engine(self.connection_string)
            self.is_sqlite = True
            self._init_sqlite_tables()

    def _init_sqlite_tables(self):
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS historical_data (
                    date TEXT PRIMARY KEY,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS prediction_results (
                    prediction_date TEXT,
                    target_date TEXT PRIMARY KEY,
                    predicted_direction INTEGER,
                    confidence_level REAL,
                    created_at TEXT
                )
            """))

    def get_user_by_email(self, email):
        query = text("SELECT * FROM users WHERE email = :email")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query, {"email": email}).fetchone()
                if result:
                    return dict(result._mapping)
            return None
        except Exception as e:
            print(f"Error Database User: {e}")
            return None

    def create_user(self, email, hashed_password, role='user'):
        query = text("""
            INSERT INTO users (email, password, role) 
            VALUES (:email, :password, :role)
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(query, {
                    "email": email,
                    "password": hashed_password,
                    "role": role
                })
            return True
        except Exception as e:
            print(f"Error Create User: {e}")
            return False

    def read_table_to_df(self, table_name, index_col=None):
        """Membaca tabel SQL dan mengembalikan Pandas DataFrame."""
        try:
            df = pd.read_sql_table(table_name, con=self.engine, index_col=index_col)
            return df
        except Exception as e:
            print(f"❌ DB Read Error: {e}")
            return pd.DataFrame()

    def write_ohlcv_to_db(self, df):
        # 1. Pastikan 'date' menjadi kolom, bukan index
        if df.index.name is not None or 'date' not in [c.lower() for c in df.columns]:
            df = df.reset_index()

        # 2. STANDARISASI NAMA KOLOM
        df.columns = [c.replace(' ', '_').lower() for c in df.columns]

        # 3. SQL Template
        if self.is_sqlite:
            upsert_query_template = text("""
                INSERT INTO historical_data (date, open, high, low, close, volume)
                VALUES (:date, :open, :high, :low, :close, :volume)
                ON CONFLICT(date) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
            """)
        else:
            upsert_query_template = text("""
                INSERT INTO historical_data (date, open, high, low, close, volume)
                VALUES (:date, :open, :high, :low, :close, :volume)
                ON DUPLICATE KEY UPDATE
                    open = VALUES(open),
                    high = VALUES(high),
                    low = VALUES(low),
                    close = VALUES(close),
                    volume = VALUES(volume)
            """)

        try:
            with self.engine.connect() as connection:
                # 4. Konversi ke list of dicts
                list_of_dicts = df.to_dict(orient='records')
                
                # Pastikan kolom date adalah string format ISO
                for d in list_of_dicts:
                    if 'date' in d and not isinstance(d['date'], str):
                        d['date'] = d['date'].strftime('%Y-%m-%d')

                connection.execute(upsert_query_template, list_of_dicts)
                connection.commit() 
                print(f"✅ Berhasil UPSERT {len(list_of_dicts)} baris ke tabel historical_data.")
                
        except Exception as e:
            print(f"❌ DB Write Error: {e}")
            raise e

    def upsert_prediction_history(
        self, 
        target_date: str, 
        direction: Literal['up','down'], 
        confidence_level: float
        )-> None:
        
        # Konversi direction ke tinyint (1 untuk up, 0 untuk down)
        direction_val = 1 if direction == 'up' else 0
        prediction_date = datetime.now().strftime('%Y-%m-%d')

        if self.is_sqlite:
            query_template = text("""
            INSERT INTO prediction_results (prediction_date, target_date, predicted_direction, confidence_level, created_at)
            VALUES (:prediction_date, :target_date, :predicted_direction, :confidence_level, :prediction_date)
            ON CONFLICT(target_date) DO UPDATE SET
                predicted_direction = excluded.predicted_direction,
                confidence_level = excluded.confidence_level,
                prediction_date = excluded.prediction_date;
            """)
        else:
            query_template = text("""
            INSERT INTO prediction_results (prediction_date, target_date, predicted_direction, confidence_level, created_at)
            VALUES (:prediction_date, :target_date, :predicted_direction, :confidence_level, NOW())
            ON DUPLICATE KEY UPDATE
                predicted_direction = :predicted_direction,
                confidence_level = :confidence_level,
                prediction_date = :prediction_date;
            """)

        try:
            with self.engine.begin() as connection:
                connection.execute(query_template, {
                    "prediction_date": prediction_date,
                    "target_date": target_date,
                    "predicted_direction": direction_val,
                    "confidence_level": confidence_level
                })
                print("prediction_results UPSERT successfully.")
        except Exception as e:
                print(f"Database Error : {e}")
                raise

    def get_prediction_history(self, limit: int = 10):
        query = text("""
            SELECT target_date, predicted_direction, confidence_level, prediction_date 
            FROM prediction_results 
            ORDER BY target_date DESC 
            LIMIT :limit
        """)
        
        try:
            with self.engine.connect() as connection:
                result = connection.execute(query, {"limit": limit})
                
                history = [
                    {
                        "date": str(row.target_date),
                        "direction": "up" if row.predicted_direction == 1 else "down",
                        "confidence_level": float(row.confidence_level),
                        "prediction_time": row.prediction_date.strftime("%Y-%m-%d") if hasattr(row.prediction_date, 'strftime') else str(row.prediction_date or "")
                    } 
                    for row in result
                ]
                return history
        except Exception as e:
            print(f"❌ Error Fetching Data: {e}")
            return []

    def delete_user(self, email):
        query = text("DELETE FROM users WHERE email = :email")
        try:
            with self.engine.begin() as conn:
                conn.execute(query, {"email": email})
            return True
        except Exception as e:
            print(f"Error Delete User: {e}")
            return False

    def get_all_users_list(self):
        query = text("SELECT email, role FROM users")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query).fetchall()
                users = [{"email": row.email, "role": row.role} for row in result]
                return users
        except Exception as e:
            print(f"Error Database get_all_users_list: {e}")
            return []