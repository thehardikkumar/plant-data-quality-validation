"""Loads equipment_raw.csv into MySQL table stg_equipment.
Install once:  pip install pandas sqlalchemy pymysql
Set your password via env var DB_URL or edit the default below."""
import os
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("DB_URL", "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/plant_dq")
engine = create_engine(DB_URL)

df = pd.read_csv("equipment_raw.csv", parse_dates=["po_date", "delivery_date"])
with engine.begin() as conn:
    conn.execute(text("DELETE FROM stg_equipment"))
    df.to_sql("stg_equipment", conn, if_exists="append", index=False)
    n = conn.execute(text("SELECT COUNT(*) FROM stg_equipment")).scalar()
print(f"Loaded {n} rows into stg_equipment")
