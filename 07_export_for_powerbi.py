"""
Exports 4 CSV files for Power BI into the folder 'powerbi_data'.
Run in Anaconda Prompt after setting DB_URL (same as for 05_clean_data.py):
    set DB_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/plant_dq
    python 07_export_for_powerbi.py
"""
import os
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(os.environ.get("DB_URL", "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/plant_dq"))
os.makedirs("powerbi_data", exist_ok=True)

queries = {
    "equipment_raw": "SELECT * FROM stg_equipment_raw",
    "equipment_clean": "SELECT * FROM stg_equipment",
    "equipment_quarantine": "SELECT * FROM equipment_quarantine",
    # one row per failed rule per record, with rule details and (cleaned, else raw) vendor/type
    "issues": """
        SELECT l.run_label, l.record_id, l.tag_number, l.rule_id, r.rule_name, r.severity,
               COALESCE(NULLIF(TRIM(COALESCE(c.vendor, w.vendor)), ''), '(blank)') AS vendor,
               COALESCE(NULLIF(TRIM(COALESCE(c.equipment_type, w.equipment_type)), ''), '(blank)') AS equipment_type
        FROM validation_log l
        JOIN validation_rules r ON r.rule_id = l.rule_id
        JOIN stg_equipment_raw w ON w.record_id = l.record_id
        LEFT JOIN stg_equipment c ON c.record_id = l.record_id
    """,
}
for name, q in queries.items():
    df = pd.read_sql(q, engine)
    df.to_csv(os.path.join("powerbi_data", name + ".csv"), index=False)
    print(f"{name}.csv  ->  {len(df)} rows")
print("Done. Files are in the 'powerbi_data' folder.")
