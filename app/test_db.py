
import os
import sys
sys.path.append('.')
from dotenv import load_dotenv

# Load environment variables dari folder backend
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from db_manager import DatabaseManager

def test_connection():
    print("Testing database connection...")
    print(f"DB_HOST: {os.getenv('DB_HOST')}")
    print(f"DB_USER: {os.getenv('DB_USER')}")
    print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
    print(f"DB_NAME: {os.getenv('DB_NAME')}")
    
    try:
        db = DatabaseManager()
        with db.engine.connect() as conn:
            print("Successfully connected to the database!")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    test_connection()
