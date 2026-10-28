
from sqlalchemy import text
import sys
sys.path.append('.')
from db_manager import DatabaseManager

def check_schema():
    db = DatabaseManager()
    tables = ['historical_data', 'prediction_results']
    for table in tables:
        print(f"\nColumns for table: {table}")
        query = text(f"DESCRIBE {table}")
        try:
            with db.engine.connect() as conn:
                result = conn.execute(query).fetchall()
                for row in result:
                    print(row)
        except Exception as e:
            print(f"Error checking table {table}: {e}")

if __name__ == "__main__":
    check_schema()
