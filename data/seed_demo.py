"""Generate realistic demo data matching UK fish processing factory operations."""
import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "compliance.db")


def julian_day(dt):
    """Convert datetime to YDDD format (Y=last digit of year, DDD=day of year)."""
    return f"{dt.year % 10}{dt.timetuple().tm_yday:03d}"


def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # === SCHEMA ===
    c.execute("""CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT, species TEXT, category TEXT,
        product_type TEXT,
        shelf_life_days INTEGER,
        storage_zone TEXT,
        unit_cost_per_kg REAL, sell_price_per_kg REAL,
        allergens TEXT,
        customer TEXT
    )""")

    c.execute("""CREATE TABLE raw_materials (
        id INTEGER PRIMARY KEY,
        product_id INTEGER, batch_code TEXT, supplier TEXT,
        quantity_kg REAL, received_date TEXT, expiry_date TEXT,
        temperature_on_arrival REAL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )""")

    c.execute("""CREATE TABLE production (
        id INTEGER PRIMARY KEY,
        product_id INTEGER, batch_code TEXT, date TEXT,
        pack_date TEXT, use_by_date TEXT,
        raw_material_batch TEXT,
        raw_input_kg REAL, finished_output_kg REAL, waste_kg REAL,
        yield_pct REAL, line_number INTEGER, shift TEXT, operator TEXT,
        concession_required INTEGER DEFAULT 0,
        concession_reason TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )""")

    c.execute("""CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer TEXT, product_id INTEGER,
        production_batch TEXT,
        quantity_kg REAL, order_date TEXT, delivery_date TEXT,
        status TEXT, price_per_kg REAL,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )""")

    c.execute("""CREATE TABLE temp_logs (
        id INTEGER PRIMARY KEY,
        location TEXT, temperature REAL,
        recorded_at TEXT, recorded_by TEXT
    )""")

    c.execute("""CREATE TABLE concessions (
        id INTEGER PRIMARY KEY,
        batch_code TEXT, product_id INTEGER,
        reason TEXT, pack_date TEXT, original_use_by TEXT,
        extended_use_by TEXT, approved_by TEXT,
        approved_date TEXT, status TEXT
    )""")

    # === PRODUCTS ===
    # Real fish processing products with correct shelf life
    products = [
        (1, "Atlantic Salmon Fillet (Fresh)", "Salmon", "Fresh Fish", "fresh", 19, "superchill", 8.50, 14.99, "Fish", "Lidl"),
        (2, "Atlantic Salmon Portion (Fresh)", "Salmon", "Fresh Fish", "fresh", 19, "superchill", 9.00, 15.99, "Fish", "Lidl"),
        (3, "Smoked Salmon Sliced", "Salmon", "Smoked", "fresh", 19, "superchill", 11.00, 22.99, "Fish", "Lidl"),
        (4, "Cod Loin (Defrost)", "Cod", "White Fish", "defrost", 11, "chiller", 7.20, 12.99, "Fish", "Lidl"),
        (5, "Haddock Fillet (Defrost)", "Haddock", "White Fish", "defrost", 11, "chiller", 6.80, 11.49, "Fish", "Lidl"),
        (6, "Sea Bass Whole (Fresh)", "Sea Bass", "Fresh Fish", "fresh", 19, "superchill", 9.50, 16.99, "Fish", "Lidl"),
        (7, "King Prawn (Defrost)", "Prawn", "Shellfish", "defrost", 11, "chiller", 12.00, 19.99, "Fish,Crustaceans", "Lidl"),
        (8, "Fish Cake", "Mixed", "Processed", "defrost", 11, "chiller", 3.50, 6.99, "Fish,Gluten,Eggs,Milk", "Lidl"),
        (9, "Breaded Cod Fillet", "Cod", "Processed", "defrost", 11, "chiller", 5.50, 9.99, "Fish,Gluten,Eggs", "Lidl"),
        (10, "Salmon En Croute", "Salmon", "Ready Meal", "defrost", 11, "chiller", 10.00, 18.99, "Fish,Gluten,Milk,Eggs", "Lidl"),
        (11, "Prawn Cocktail", "Prawn", "Ready Meal", "fresh", 19, "superchill", 8.00, 14.99, "Fish,Crustaceans,Eggs,Milk", "Lidl"),
        (12, "Mackerel Fillet (Fresh)", "Mackerel", "Fresh Fish", "fresh", 19, "superchill", 5.50, 9.99, "Fish", "Lidl"),
    ]
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?)", products)

    suppliers = ["Nordic Seafood AS", "Scottish Salmon Co", "Grimsby Fish Market",
                 "Plymouth Trawlers Ltd", "Irish Shellfish Co", "Faroe Islands Seafood"]

    operators = ["J. Smith", "A. Patel", "M. Kowalski", "S. Rahman", "K. Murphy",
                 "T. Jones", "R. Singh", "E. Williams", "P. Kapkoti", "D. Brown", "L. Chen"]

    locations = ["Superchill", "Chiller 1", "Chiller 2", "Freezer 1", "Production Floor", "Dispatch Bay"]
    temp_targets = {
        "Superchill": (0.0, 0.5),       # mean, spread
        "Chiller 1": (2.5, 1.0),
        "Chiller 2": (3.0, 1.0),
        "Freezer 1": (-20.0, 1.0),
        "Production Floor": (12.0, 1.5),
        "Dispatch Bay": (3.0, 1.5),
    }

    recorders = ["Auto-Sensor", "Auto-Sensor", "Auto-Sensor", "J. Smith", "A. Patel", "P. Kapkoti"]
    sub_batches = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    now = datetime.now()
    rm_id = 0
    prod_id = 0
    order_id = 0
    temp_id = 0
    conc_id = 0

    for day_offset in range(60, 0, -1):
        date = now - timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")
        jd = julian_day(date)

        # Raw materials (3-5 deliveries per day)
        day_rm_batches = []
        for delivery in range(random.randint(3, 5)):
            rm_id += 1
            prod = random.choice(products)
            product_type = prod[4]
            prefix = "F" if product_type == "fresh" else "D"
            batch = f"{prefix}{jd}{sub_batches[delivery]}"
            qty = round(random.uniform(80, 600), 1)
            shelf_days = prod[5]
            expiry = (date + timedelta(days=shelf_days)).strftime("%Y-%m-%d")
            temp = round(random.uniform(-1.0, 3.0), 1)
            c.execute("INSERT INTO raw_materials VALUES (?,?,?,?,?,?,?,?)",
                      (rm_id, prod[0], batch, random.choice(suppliers), qty, date_str, expiry, temp))
            day_rm_batches.append(batch)

        # Production (6-14 runs per day)
        day_prod_batches = []
        for run in range(random.randint(6, 14)):
            prod_id += 1
            prod = random.choice(products)
            product_type = prod[4]
            shelf_days = prod[5]
            prefix = "F" if product_type == "fresh" else "D"
            batch = f"{prefix}{jd}{sub_batches[run % len(sub_batches)]}"

            pack_date = date_str
            use_by = (date + timedelta(days=shelf_days)).strftime("%Y-%m-%d")

            raw_kg = round(random.uniform(100, 800), 1)
            waste_pct = random.uniform(0.05, 0.22)
            waste_kg = round(raw_kg * waste_pct, 1)
            output_kg = round(raw_kg - waste_kg, 1)
            yield_pct = round((output_kg / raw_kg) * 100, 1)
            shift = random.choice(["Day", "Night"])
            line = random.randint(1, 3)

            # Concession check: sometimes defrost products go over 11 days
            concession = 0
            conc_reason = None
            if product_type == "defrost" and random.random() < 0.08:
                extra_days = random.randint(1, 3)
                use_by = (date + timedelta(days=shelf_days + extra_days)).strftime("%Y-%m-%d")
                concession = 1
                conc_reason = f"Extended shelf life by {extra_days} days due to late dispatch"

                conc_id += 1
                c.execute("INSERT INTO concessions VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (conc_id, batch, prod[0], conc_reason, pack_date,
                           (date + timedelta(days=shelf_days)).strftime("%Y-%m-%d"),
                           use_by, random.choice(["Quality Manager", "Site Manager"]),
                           date_str, random.choice(["Approved", "Approved", "Pending"])))

            rm_batch = random.choice(day_rm_batches) if day_rm_batches else None
            c.execute("""INSERT INTO production
                      (id, product_id, batch_code, date, pack_date, use_by_date,
                       raw_material_batch, raw_input_kg, finished_output_kg, waste_kg,
                       yield_pct, line_number, shift, operator, concession_required, concession_reason)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (prod_id, prod[0], batch, date_str, pack_date, use_by, rm_batch,
                       raw_kg, output_kg, waste_kg, yield_pct, line, shift,
                       random.choice(operators), concession, conc_reason))
            day_prod_batches.append(batch)

        # Orders (3-6 per day, mainly Lidl)
        for _ in range(random.randint(3, 6)):
            order_id += 1
            prod = random.choice(products)
            qty = round(random.uniform(50, 400), 1)
            delivery = (date + timedelta(days=random.randint(1, 3))).strftime("%Y-%m-%d")
            status = random.choice(["Delivered", "Delivered", "Delivered", "Pending", "In Transit"])
            prod_batch = random.choice(day_prod_batches) if day_prod_batches else None
            customer = "Lidl" if random.random() < 0.7 else random.choice(["Iceland", "Tesco", "M&S"])
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)",
                      (order_id, customer, prod[0], prod_batch,
                       qty, date_str, delivery, status, prod[9]))

        # Temperature logs (8 readings per location per day)
        for loc in locations:
            mean, spread = temp_targets[loc]
            for hour in range(0, 24, 3):
                temp_id += 1
                ts = date.replace(hour=hour, minute=random.randint(0, 59))

                # Normal reading with occasional excursion (~3%)
                if random.random() < 0.03:
                    temp = round(mean + spread * random.choice([-4, 4, 5]), 1)
                else:
                    temp = round(mean + random.uniform(-spread * 0.4, spread * 0.4), 1)

                c.execute("INSERT INTO temp_logs VALUES (?,?,?,?,?)",
                          (temp_id, loc, temp, ts.strftime("%Y-%m-%d %H:%M:%S"),
                           random.choice(recorders)))

    conn.commit()
    conn.close()

    print(f"Demo database seeded: {DB_PATH}")
    print(f"  Products: {len(products)}")
    print(f"  Raw materials: {rm_id}")
    print(f"  Production runs: {prod_id}")
    print(f"  Orders: {order_id}")
    print(f"  Temperature logs: {temp_id}")
    print(f"  Concessions: {conc_id}")


if __name__ == "__main__":
    seed()
