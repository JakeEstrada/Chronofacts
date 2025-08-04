import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    conn = psycopg2.connect(
        dbname="timeline_db",
        user="timeline_user",
        password="Paradox*456*",
        host="localhost"
    )
    return conn
