import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "tracker_universitario")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
DB_PORT = os.getenv("DB_PORT", "5432")

conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE usuarios ADD COLUMN email VARCHAR(100) UNIQUE;")
except Exception as e:
    print(f"Error adding email: {e}")
    conn.rollback()
else:
    conn.commit()

try:
    cur.execute("ALTER TABLE usuarios ADD COLUMN google_id VARCHAR(100) UNIQUE;")
except Exception as e:
    print(f"Error adding google_id: {e}")
    conn.rollback()
else:
    conn.commit()

try:
    cur.execute("ALTER TABLE usuarios ALTER COLUMN password_hash DROP NOT NULL;")
except Exception as e:
    print(f"Error altering password_hash: {e}")
    conn.rollback()
else:
    conn.commit()

print("Database altered successfully.")
