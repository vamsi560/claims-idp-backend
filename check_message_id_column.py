import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_HOST = os.getenv('POSTGRES_HOST')
DB_PORT = os.getenv('POSTGRES_PORT')
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD')

def check_message_id_column():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT column_name FROM information_schema.columns WHERE table_name = 'fnol_work_items';
        """)
        columns = [row[0] for row in cur.fetchall()]
        if 'message_id' in columns:
            print("message_id column exists in fnol_work_items table.")
        else:
            print("message_id column DOES NOT exist in fnol_work_items table.")
        print("Current columns:", columns)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    check_message_id_column()
