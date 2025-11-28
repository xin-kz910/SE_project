# db.py
import psycopg

DB_NAME = "1141se"
DB_USER = "postgres"
DB_PASS = "123"
DB_HOST = "localhost"
DB_PORT = 5432

def get_conn():
    # 每次用完自動關閉
    return psycopg.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS,
        host=DB_HOST, port=DB_PORT
    )
