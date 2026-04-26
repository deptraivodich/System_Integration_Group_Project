from fastapi import FastAPI
import pandas as pd
from db import mysql_db, postgres_db

app = FastAPI()

@app.get("/api/report")
def get_report(page: int = 1, limit: int = 10):
    offset = (page - 1) * limit

    # 1. Lấy dữ liệu orders từ MySQL
    orders_query = f"""
        SELECT id as order_id, user_id, product_id, quantity, status
        FROM orders
        LIMIT {limit} OFFSET {offset}
    """
    orders_df = pd.read_sql(orders_query, mysql_db)

    # 2. Lấy dữ liệu transactions từ PostgreSQL
    transactions_query = """
        SELECT order_id, amount, created_at
        FROM transactions
    """
    transactions_df = pd.read_sql(transactions_query, postgres_db)

    # 3. Data Stitching (JOIN)
    merged_df = pd.merge(
        orders_df,
        transactions_df,
        on="order_id",
        how="left"
    )

    # 4. Tính doanh thu theo user
    revenue_by_user = merged_df.groupby("user_id")["amount"].sum().reset_index()

    # 5. Format JSON
    return {
        "orders": merged_df.fillna("").to_dict(orient="records"),
        "revenue_by_user": revenue_by_user.to_dict(orient="records"),
        "pagination": {
            "page": page,
            "limit": limit
        }
    }