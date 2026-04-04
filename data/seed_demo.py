"""Generate realistic demo data for the compliance dashboard."""
import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "compliance.db")


def seed():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # === SCHEMA ===
    c.execute("""CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT, species TEXT, category TEXT,
        unit_cost_per_kg REAL, sell_price_per_kg REAL,
        allergens TEXT
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
        raw_material_batch TEXT,
        raw_input_kg REAL, finished_output_kg REAL, waste_kg REAL,
        yield_pct REAL, line_number INTEGER, shift TEXT, operator TEXT,
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

    # === PRODUCTS ===
    products = [
        (1, "Atlantic Salmon Fillet", "Salmon", "Fresh Fish", 8.50, 14.99, "Fish"),
        (2, "Cod Loin", "Cod", "Fresh Fish", 7.20, 12.99, "Fish"),
        (3, "Haddock Fillet", "Haddock", "Fresh Fish", 6.80, 11.49, "Fish"),
        (4, "King Prawn", "Prawn", "Shellfish", 12.00, 19.99, "Fish,Crustaceans"),
        (5, "Sea Bass Whole", "Sea Bass", "Fresh Fish", 9.50, 16.99, "Fish"),
        (6, "Smoked Salmon", "Salmon", "Smoked", 11.00, 22.99, "Fish"),
        (7, "Fish Cake", "Mixed", "Processed", 3.50, 6.99, "Fish,Gluten,Eggs,Milk"),
        (8, "Prawn Cocktail", "Prawn", "Ready Meal", 8.00, 14.99, "Fish,Crustaceans,Eggs,Milk"),
        (9, "Breaded Cod", "Cod", "Processed", 5.50, 9.99, "Fish,Gluten,Eggs"),
        (10, "Salmon En Croute", "Salmon", "Ready Meal", 10.00, 18.99, "Fish,Gluten,Milk,Eggs"),
    ]
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", products)

    # === SUPPLIERS ===
    suppliers = ["Nordic Seafood AS", "Scottish Salmon Co", "Grimsby Fish Market",
                 "Plymouth Trawlers Ltd", "Irish Shellfish Co"]

    # === STAFF ===
    operators = ["J. Smith", "A. Patel", "M. Kowalski", "S. Rahman", "K. Murphy",
                 "T. Jones", "R. Singh", "E. Williams"]

    customers = ["Lidl UK", "Iceland Foods", "Tesco", "M&S", "Aldi", "Morrisons", "Asda"]

    locations = ["Cold Room 1", "Cold Room 2", "Freezer 1", "Production Floor", "Dispatch Bay"]
    temp_ranges = {
        "Cold Room 1": (1.0, 4.5, 0.8),      # mean, normal_range, excursion_prob
        "Cold Room 2": (1.5, 4.0, 0.6),
        "Freezer 1": (-20.0, 3.0, 0.4),
        "Production Floor": (11.0, 3.0, 0.3),
        "Dispatch Bay": (3.5, 3.0, 0.5),
    }

    recorders = ["Auto-Sensor", "Auto-Sensor", "Auto-Sensor", "J. Smith", "A. Patel"]

    now = datetime.now()
    rm_id = 0
    prod_id = 0
    order_id = 0
    temp_id = 0

    for day_offset in range(60, 0, -1):
        date = now - timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")

        # Raw materials (2-4 deliveries per day)
        for _ in range(random.randint(2, 4)):
            rm_id += 1
            prod = random.choice(products)
            batch = f"RM-{date.strftime('%y%m%d')}-{rm_id:04d}"
            qty = round(random.uniform(50, 500), 1)
            expiry = (date + timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
            temp = round(random.uniform(-1.0, 4.0), 1)
            c.execute("INSERT INTO raw_materials VALUES (?,?,?,?,?,?,?,?)",
                      (rm_id, prod[0], batch, random.choice(suppliers), qty, date_str, expiry, temp))

        # Production (5-12 runs per day)
        day_rm_batches = [f"RM-{date.strftime('%y%m%d')}-{i:04d}" for i in range(rm_id - 3, rm_id + 1)]
        for _ in range(random.randint(5, 12)):
            prod_id += 1
            prod = random.choice(products)
            batch = f"PR-{date.strftime('%y%m%d')}-{prod_id:04d}"
            raw_kg = round(random.uniform(100, 800), 1)
            waste_pct = random.uniform(0.05, 0.25)
            waste_kg = round(raw_kg * waste_pct, 1)
            output_kg = round(raw_kg - waste_kg, 1)
            yield_pct = round((output_kg / raw_kg) * 100, 1)
            shift = random.choice(["Day", "Night"])
            line = random.randint(1, 3)
            rm_batch = random.choice(day_rm_batches) if day_rm_batches else None
            c.execute("INSERT INTO production VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (prod_id, prod[0], batch, date_str, rm_batch,
                       raw_kg, output_kg, waste_kg, yield_pct, line, shift,
                       random.choice(operators)))

        # Orders (3-6 per day)
        day_prod_batches = [f"PR-{date.strftime('%y%m%d')}-{i:04d}" for i in range(prod_id - 5, prod_id + 1)]
        for _ in range(random.randint(3, 6)):
            order_id += 1
            prod = random.choice(products)
            qty = round(random.uniform(50, 300), 1)
            delivery = (date + timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
            status = random.choice(["Delivered", "Delivered", "Delivered", "Pending", "In Transit"])
            prod_batch = random.choice(day_prod_batches) if day_prod_batches else None
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)",
                      (order_id, random.choice(customers), prod[0], prod_batch,
                       qty, date_str, delivery, status, prod[5]))

        # Temperature logs (8 readings per location per day)
        for loc in locations:
            mean, spread, exc_prob = temp_ranges[loc]
            for hour in range(0, 24, 3):
                temp_id += 1
                ts = date.replace(hour=hour, minute=random.randint(0, 59))

                # Normal reading with occasional excursion
                if random.random() < exc_prob * 0.05:  # ~5% of exc_prob
                    temp = round(mean + spread * random.choice([-3, 3, 4]), 1)
                else:
                    temp = round(mean + random.uniform(-spread * 0.3, spread * 0.3), 1)

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


if __name__ == "__main__":
    seed()
