"""
Generates a SYNTHETIC plant equipment list with deliberately injected data-quality errors.
Output: equipment_raw.csv, injected_errors.csv (how many errors of each kind were injected).
Uses only the Python standard library.
"""
import csv, random
from datetime import date, timedelta

random.seed(42)
N_BASE = 3000

TYPES = {  # type: (tag prefix, services)
    "Pump": ("P", ["Feed Pump", "Reflux Pump", "Cooling Water Pump", "Booster Pump", "Transfer Pump"]),
    "Vessel": ("V", ["Separator", "Surge Drum", "Knock-out Drum", "Reactor Feed Drum"]),
    "Heat Exchanger": ("E", ["Feed Cooler", "Product Heater", "Condenser", "Reboiler"]),
    "Valve": ("XV", ["Isolation Valve", "Shutdown Valve", "Control Valve Isolation"]),
    "Tank": ("T", ["Storage Tank", "Day Tank", "Slop Tank"]),
}
VENDORS = ["Apex Flow Systems", "Northstar Process Equipment", "Meridian Valves Ltd",
           "Bluewave Heat Transfer", "Titan Fabricators", "Orion Instruments", "Sterling Pressure Vessels"]
MATERIALS = ["Carbon Steel", "Stainless Steel 304", "Stainless Steel 316", "Duplex Stainless Steel"]
STATUS = ["Planned", "Ordered", "Delivered", "Installed"]

MATERIAL_VARIANTS = ["CS", "carbon steel", "C.S.", "SS316", "SS 316", "ss304", "Stainless 316L", "Duplex SS"]
TYPE_VARIANTS = ["pump", "Pumps", "Vessels", "Exchanger", "HX", "Misc"]
VENDOR_VARIANTS = ["Apex Flow System", "NORTHSTAR Process Equipment", "Meridian Valve Ltd",
                   "Bluewave Heat Transfers", "Unknown Supplier XYZ"]

def base_rows():
    rows, counters = [], {t: 100 for t in TYPES}
    types = list(TYPES)
    for i in range(N_BASE):
        t = random.choice(types)
        prefix, services = TYPES[t]
        counters[t] += 1
        suffix = random.choice(["", "", "", "A", "B"]) if t == "Pump" else ""
        po_date = date(2023, 1, 1) + timedelta(days=random.randint(0, 900))
        rows.append({
            "tag_number": f"{prefix}-{counters[t]}{suffix}",
            "equipment_type": t,
            "service": random.choice(services),
            "design_pressure_barg": round(random.uniform(5, 150), 1),
            "design_temp_c": round(random.uniform(-20, 400), 0),
            "material": random.choice(MATERIALS),
            "vendor": random.choice(VENDORS),
            "po_number": f"PO-4500{random.randint(1000, 1400)}",
            "po_date": po_date,
            "delivery_date": po_date + timedelta(days=random.randint(60, 400)),
            "status": random.choice(STATUS),
        })
    return rows

def main():
    rows = base_rows()
    inj = {}
    def pick(k):
        return random.sample(range(len(rows)), k)

    for i in pick(50): rows[i]["vendor"] = None
    inj["Missing vendor"] = 50
    for i in pick(50): rows[i]["material"] = None
    inj["Missing material"] = 50
    for i in pick(40): rows[i]["design_pressure_barg"] = None
    inj["Missing design pressure"] = 40
    for i in pick(25): rows[i]["design_pressure_barg"] = random.choice([-5, 0, -12.5])
    for i in pick(25): rows[i]["design_pressure_barg"] = random.choice([999, 1500, 5000])
    inj["Design pressure out of range"] = 50
    for i in pick(20): rows[i]["design_temp_c"] = random.choice([-300, 900, 1200])
    inj["Design temp out of range"] = 20
    for i in pick(60):
        t = rows[i]["tag_number"]
        rows[i]["tag_number"] = random.choice([t.replace("-", ""), t.lower(), t.lower().replace("-", "")])
    inj["Tag format invalid"] = 60
    for i in pick(45):
        rows[i]["delivery_date"] = rows[i]["po_date"] - timedelta(days=random.randint(5, 120))
    inj["Delivery before PO date"] = 45
    for i in pick(40): rows[i]["equipment_type"] = random.choice(TYPE_VARIANTS)
    inj["Equipment type not allowed"] = 40
    for i in pick(150): rows[i]["material"] = random.choice(MATERIAL_VARIANTS)
    inj["Material not standard"] = 150
    for i in pick(35): rows[i]["vendor"] = random.choice(VENDOR_VARIANTS)
    inj["Vendor not in lookup"] = 35

    # duplicates (added after injection so exact copies are exact)
    exact = [dict(rows[i]) for i in pick(40)]
    inj["Exact duplicate rows"] = 40
    same_tag = []
    for i in pick(40):
        r = dict(rows[i])
        r["vendor"] = random.choice(VENDORS)
        r["design_pressure_barg"] = round(random.uniform(5, 150), 1)
        r["po_number"] = f"PO-4500{random.randint(1000, 1400)}"
        same_tag.append(r)
    inj["Same tag, different details"] = 40
    rows += exact + same_tag
    random.shuffle(rows)

    cols = list(rows[0].keys())
    with open("equipment_raw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    with open("injected_errors.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["error_type", "rows_injected"])
        for k, v in inj.items():
            w.writerow([k, v])
    print(f"Wrote equipment_raw.csv with {len(rows)} rows")
    for k, v in inj.items():
        print(f"  injected {v:>3}  {k}")

if __name__ == "__main__":
    main()
