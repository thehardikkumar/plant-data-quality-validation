"""
Cleans stg_equipment in place. Only FIXES what can be fixed safely (formatting, spelling).
Anything that needs a human decision (missing values, out-of-range numbers, bad dates,
same tag with different details) is left as-is so the validation rules can flag it.

Install once:  pip install pandas sqlalchemy pymysql
Run AFTER:  CALL sp_run_validation('BEFORE');
"""
import os, re, difflib
import pandas as pd

TYPE_MAP = {
    "pump": "Pump", "pumps": "Pump",
    "vessel": "Vessel", "vessels": "Vessel",
    "heat exchanger": "Heat Exchanger", "exchanger": "Heat Exchanger", "hx": "Heat Exchanger",
    "valve": "Valve", "valves": "Valve",
    "tank": "Tank", "tanks": "Tank",
}
MATERIAL_MAP = {
    "cs": "Carbon Steel", "c.s.": "Carbon Steel", "carbon steel": "Carbon Steel",
    "ss304": "Stainless Steel 304", "ss 304": "Stainless Steel 304", "stainless steel 304": "Stainless Steel 304",
    "ss316": "Stainless Steel 316", "ss 316": "Stainless Steel 316",
    "stainless steel 316": "Stainless Steel 316", "stainless 316l": "Stainless Steel 316",
    "duplex ss": "Duplex Stainless Steel", "duplex": "Duplex Stainless Steel",
    "duplex stainless steel": "Duplex Stainless Steel",
}
TAG_RE = re.compile(r"^([A-Za-z]{1,2})-?(\d{3,4})([A-Za-z]?)$")


def _strip(x):
    return x.strip() if isinstance(x, str) else x


def _fix_tag(t):
    if not isinstance(t, str):
        return t
    m = TAG_RE.match(t.strip())
    return f"{m.group(1).upper()}-{m.group(2)}{m.group(3).upper()}" if m else t.strip()


def _fix_vendor(v, vendors):
    if not isinstance(v, str) or not v.strip():
        return v
    v = v.strip()
    if v in vendors:
        return v
    match = difflib.get_close_matches(v.lower(), [x.lower() for x in vendors], n=1, cutoff=0.9)
    if match:
        return next(x for x in vendors if x.lower() == match[0])
    return v  # unknown vendor: leave for the validation rule to flag


def clean(df, vendors):
    """Returns (cleaned_df, stats). Does not touch the database."""
    before = df.copy()
    out = df.copy()
    for c in ["tag_number", "equipment_type", "service", "material", "vendor", "po_number", "status"]:
        out[c] = out[c].map(_strip)

    out["tag_number"] = out["tag_number"].map(_fix_tag)
    out["equipment_type"] = out["equipment_type"].map(
        lambda x: TYPE_MAP.get(x.lower(), x) if isinstance(x, str) else x)
    out["material"] = out["material"].map(
        lambda x: MATERIAL_MAP.get(x.lower(), x) if isinstance(x, str) else x)
    out["vendor"] = out["vendor"].map(lambda x: _fix_vendor(x, vendors))

    changed = {}
    for c in ["tag_number", "equipment_type", "material", "vendor"]:
        diff = (before[c].fillna("<NA>") != out[c].fillna("<NA>"))
        changed[c] = int(diff.sum())

    # remove EXACT duplicate rows (all columns except record_id); keep the first
    cols = [c for c in out.columns if c != "record_id"]
    dup_mask = out.duplicated(subset=cols, keep="first")
    removed = int(dup_mask.sum())
    out = out[~dup_mask].reset_index(drop=True)

    stats = {"rows_before": len(before), "rows_after": len(out),
             "exact_duplicates_removed": removed, "values_fixed": changed}
    return out, stats


if __name__ == "__main__":
    from sqlalchemy import create_engine, text, inspect
    engine = create_engine(os.environ.get("DB_URL", "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/plant_dq"))

    with engine.begin() as conn:
        # keep an untouched copy of the raw data (created only once) for before/after comparison
        if not inspect(conn).has_table("stg_equipment_raw"):
            conn.execute(text("CREATE TABLE stg_equipment_raw AS SELECT * FROM stg_equipment"))
            print("Backed up raw data to stg_equipment_raw")
        df = pd.read_sql("SELECT * FROM stg_equipment_raw", conn)   # always clean from the raw copy
        vendors = pd.read_sql("SELECT vendor_name FROM vendor", conn)["vendor_name"].tolist()

        cleaned, stats = clean(df, vendors)

        conn.execute(text("DELETE FROM stg_equipment"))
        cleaned.to_sql("stg_equipment", conn, if_exists="append", index=False)

    print("Rows before:", stats["rows_before"])
    print("Rows after :", stats["rows_after"])
    print("Exact duplicates removed:", stats["exact_duplicates_removed"])
    print("Values standardized:", stats["values_fixed"])
    print("Next: CALL sp_run_validation('AFTER');  then run 06_publish_clean_data.sql")
