from sqlalchemy import create_engine
import time

def retry_connection(create_engine_func, retries=5, delay=5):
    for i in range(retries):
        try:
            engine = create_engine_func()
            conn = engine.connect()
            conn.close()
            print("[INFO] Connected successfully")
            return engine
        except Exception as e:
            print(f"[ERROR] Retry {i+1}: {e}")
            time.sleep(delay)
    raise Exception("Cannot connect to database")

# MySQL
def mysql_engine():
    return create_engine(
        "mysql+pymysql://root:123456@mysql_db:3306/noah_retail"
    )

# PostgreSQL
def postgres_engine():
    return create_engine(
        "postgresql://postgres:postgres123@postgres_db:5432/noah_finance"
    )

mysql_db = retry_connection(mysql_engine)
postgres_db = retry_connection(postgres_engine)