"""Generate 60 days of realistic food factory data with intentional excursions."""
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.database import get_engine, init_db, drop_all, Product, Batch, TemperatureLog, Order, Base, load_config
from sqlalchemy.orm import sessionmaker


def julian_day(dt):
    return f"{dt.year % 10}{dt.timetuple().tm_yday:03d}"


def seed():
    config = load_config()

    # Reset database — delete file and recreate from scratch
    from modules.database import DB_PATH
    if DB_PATH and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    init_db()

    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    # === PRODUCTS ===
    IMG_SAL = "https://images.unsplash.com/photo-1574781330855-d0db8cc6a79c?w=80&h=80&fit=crop"
    IMG_COD = "https://images.unsplash.com/photo-1510130387422-82bed34b37e9?w=80&h=80&fit=crop"
    IMG_HAD = "https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?w=80&h=80&fit=crop"
    IMG_SBS = "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=80&h=80&fit=crop"
    IMG_MAR = "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=80&h=80&fit=crop"

    products = [
        # === LIDL — GG Salmon (superchilled +11/+12) ===
        Product(id=1, code="GG-SAL-240", name="GG Salmon Fillets 240g", species="Salmon", category="Fresh Fish", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=11, storage_zone="Superchill", certification="GG", allergens="Fish", image_url=IMG_SAL, customer="Lidl"),
        Product(id=2, code="GG-SAL-280", name="GG Salmon Fillets 280g", species="Salmon", category="Fresh Fish", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=11, storage_zone="Superchill", certification="GG", allergens="Fish", image_url=IMG_SAL, customer="Lidl"),
        # === LIDL — Simply Salmon (normal +9) ===
        Product(id=3, code="GG-SIM-250", name="Simply Salmon 250g", species="Salmon", category="Fresh Fish", product_type="fresh", shelf_life_type="normal", shelf_life_days=9, storage_zone="Chiller", certification="GG", allergens="Fish", image_url=IMG_SAL, customer="Lidl"),
        # === LIDL — Salmon Marinades (normal +9) ===
        Product(id=4, code="GG-GH-220", name="Salmon Garlic & Herb Marinade 220g", species="Salmon", category="Marinades", product_type="fresh", shelf_life_type="normal", shelf_life_days=9, storage_zone="Chiller", certification="GG", allergens="Fish,Milk", image_url=IMG_MAR, customer="Lidl"),
        Product(id=5, code="GG-SC-220", name="Salmon Sweet Chilli Marinade 220g", species="Salmon", category="Marinades", product_type="fresh", shelf_life_type="normal", shelf_life_days=9, storage_zone="Chiller", certification="GG", allergens="Fish,Soya", image_url=IMG_MAR, customer="Lidl"),
        # === LIDL — Cod (MSC, defrost +9 normal) ===
        Product(id=6, code="MSC-COD-260", name="Cod Loins 260g", species="Cod", category="White Fish", product_type="defrost", shelf_life_type="superchilled", shelf_life_days=11, storage_zone="Chiller", certification="MSC", allergens="Fish", image_url=IMG_COD, customer="Lidl"),
        Product(id=7, code="MSC-COD-250", name="Cod Fillets 250g", species="Cod", category="White Fish", product_type="defrost", shelf_life_type="normal", shelf_life_days=9, storage_zone="Chiller", certification="MSC", allergens="Fish", image_url=IMG_COD, customer="Lidl"),
        Product(id=8, code="MSC-SIM-250", name="Simply Cod 250g", species="Cod", category="White Fish", product_type="defrost", shelf_life_type="normal", shelf_life_days=9, storage_zone="Chiller", certification="MSC", allergens="Fish", image_url=IMG_COD, customer="Lidl"),
        # === LIDL — Haddock (MSC, normal +9) ===
        Product(id=9, code="MSC-HAD-230", name="Haddock Fillets 230g", species="Haddock", category="White Fish", product_type="defrost", shelf_life_type="normal", shelf_life_days=9, storage_zone="Chiller", certification="MSC", allergens="Fish", image_url=IMG_HAD, customer="Lidl"),
        # === LIDL — Multi-pack Salmon (GG, superchilled +11) ===
        Product(id=10, code="GG-4SAL-480", name="4 Salmon Fillets 480g", species="Salmon", category="Multi-pack", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=11, storage_zone="Superchill", certification="GG", allergens="Fish", image_url=IMG_SAL, customer="Lidl"),
        Product(id=11, code="GG-SALJNT", name="Salmon Fillet Joint", species="Salmon", category="Joint", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=11, storage_zone="Superchill", certification="GG", allergens="Fish", image_url=IMG_SAL, customer="Lidl"),
        Product(id=12, code="GG-6SAL-660", name="6 Salmon Fillets 660g", species="Salmon", category="Multi-pack", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=11, storage_zone="Superchill", certification="GG", allergens="Fish", image_url=IMG_SAL, customer="Lidl"),
        # === ALMARIA — Dubai/UAE, Halal certified ===
        Product(id=17, code="ALM-SAL-240", name="Salmon 240g (Almaria)", species="Salmon", category="Fresh Fish", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=19, storage_zone="Superchill", certification="Halal", allergens="Fish", image_url=IMG_SAL, customer="Almaria (Dubai)"),
        Product(id=18, code="ALM-SWC-220", name="Salmon Sweet Chilli Marinade 220g (Almaria)", species="Salmon", category="Marinades", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=19, storage_zone="Superchill", certification="Halal", allergens="Fish,Soya,Gluten", image_url=IMG_MAR, customer="Almaria (Dubai)"),
        Product(id=19, code="ALM-BSB-455", name="Butterfly Sea Bass Lemon & Parsley 455g (Almaria)", species="Sea Bass", category="Prepared", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=19, storage_zone="Superchill", certification="Halal", allergens="Fish", image_url=IMG_SBS, customer="Almaria (Dubai)"),
        Product(id=20, code="ALM-SBS-180", name="Sea Bass 180g (Almaria)", species="Sea Bass", category="Fresh Fish", product_type="fresh", shelf_life_type="superchilled", shelf_life_days=19, storage_zone="Superchill", certification="Halal", allergens="Fish", image_url=IMG_SBS, customer="Almaria (Dubai)"),
    ]
    session.add_all(products)
    session.flush()

    suppliers = ["Nordic Seafood AS", "Scottish Salmon Co", "Grimsby Fish Market", "Plymouth Trawlers", "Irish Shellfish Co"]
    operators = ["J. Smith", "A. Patel", "M. Kowalski", "S. Rahman", "K. Murphy", "T. Jones", "P. Kapkoti", "R. Singh"]
    run_counter = 100000
    customers = ["Lidl", "Iceland", "Tesco", "M&S", "Almaria (Dubai)"]
    locations = list(config["temperature"]["locations"].keys())
    sub_batches = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    now = datetime.now()
    batch_id = 0
    order_id = 0
    temp_id = 0

    for day_offset in range(60, 0, -1):
        date = now - timedelta(days=day_offset)
        date_str = date.strftime("%Y-%m-%d")
        jd = julian_day(date)

        # === BATCHES (8-14 per day) ===
        day_batches = []
        for run in range(random.randint(8, 14)):
            batch_id += 1
            prod = random.choice(products)
            prefix = "F" if prod.product_type == "fresh" else "D"
            batch_code = f"{prefix}{jd}{sub_batches[run % 26]}"

            raw_kg = round(random.uniform(100, 800), 1)
            waste_pct = random.uniform(0.05, 0.22)
            waste_kg = round(raw_kg * waste_pct, 1)
            output_kg = round(raw_kg - waste_kg, 1)
            yield_pct = round((output_kg / raw_kg) * 100, 1)

            # Tag use-by = pack date + shelf life days
            tag_use_by_dt = date + timedelta(days=prod.shelf_life_days)
            tag_use_by = tag_use_by_dt.strftime("%Y-%m-%d")

            # Plan use-by = what Lidl's plan says (sometimes ahead of tag)
            # Concession required if plan_use_by > tag_use_by
            plan_offset = 0
            concession = False
            conc_reason = None
            if random.random() < 0.08:
                plan_offset = random.randint(1, 3)
                concession = True
                conc_reason = f"Plan use-by +{plan_offset}d ahead of tag use-by"
            plan_use_by = (tag_use_by_dt + timedelta(days=plan_offset)).strftime("%Y-%m-%d")
            use_by = tag_use_by  # Effective use-by is always the tag

            # Pallet tag dates
            harvest_date = (date - timedelta(days=random.randint(1, 5))).strftime("%Y-%m-%d")
            defrost_dt = (date - timedelta(days=random.randint(0, 2))).strftime("%Y-%m-%d") if prod.product_type == "defrost" else None
            intake_raw = (date - timedelta(days=random.randint(0, 1))).strftime("%Y-%m-%d")

            # RSPCA raw material sometimes used for GG runs (10% chance)
            # This is the margin loss scenario — premium fish at standard price
            rm_certification = prod.certification
            if prod.certification == "GG" and prod.species == "Salmon" and random.random() < 0.10:
                rm_certification = "RSPCA"

            # SI-style fields
            run_counter += 1
            run_number = str(run_counter)
            age_days = day_offset  # Days since production
            life_days = max(0, prod.shelf_life_days - day_offset)  # Remaining shelf life
            trace_id = f"{batch_code}:{jd}"
            batch_no_long = f"{date.strftime('%Y%m%d')}{prod.code}{batch_id:05d}"

            # Stock location and status based on age
            if day_offset <= 2:
                stock_loc = random.choice(["Coldstore 1", "Coldstore 2", "Blast Freezer"])
                stock_status = "In Stock"
                process_status = "In Active"
                stock_remaining = round(output_kg * random.uniform(0.3, 1.0), 1)
                stock_units = random.randint(5, 40)
                alert = life_days <= 3
            elif day_offset <= 5:
                stock_loc = random.choice(["Coldstore 1", "Despatch Bay", "Coldstore 2"])
                stock_status = random.choice(["In Stock", "In Stock", "Despatched"])
                process_status = "In Active" if stock_status == "In Stock" else "Complete"
                stock_remaining = round(output_kg * random.uniform(0, 0.5), 1) if stock_status == "In Stock" else 0
                stock_units = random.randint(0, 20) if stock_status == "In Stock" else 0
                alert = life_days <= 3 and stock_status == "In Stock"
            else:
                stock_loc = "Despatched"
                stock_status = "Despatched"
                process_status = "Complete"
                stock_remaining = 0
                stock_units = 0
                alert = False

            batch = Batch(
                id=batch_id, batch_code=batch_code,
                batch_no=batch_no_long, run_number=run_number,
                product_id=prod.id,
                intake_date=date_str, production_date=date_str,
                pack_date=date_str, tag_use_by=tag_use_by, plan_use_by=plan_use_by, use_by_date=use_by,
                age_days=age_days, life_days=life_days,
                raw_material_batch=f"{prefix}{jd}{sub_batches[random.randint(0, 4)]}",
                trace_id=trace_id,
                harvest_date=harvest_date,
                defrost_date=defrost_dt,
                intake_date_raw=intake_raw,
                rm_certification=rm_certification,
                supplier=random.choice(suppliers),
                raw_input_kg=raw_kg, finished_output_kg=output_kg,
                waste_kg=waste_kg, yield_pct=yield_pct,
                line_number=random.randint(1, 3),
                shift=random.choice(["Day", "Night"]),
                operator=random.choice(operators),
                stock_location=stock_loc,
                stock_kg=stock_remaining,
                stock_units=stock_units,
                status=stock_status,
                process_status=process_status,
                alert_flag=alert,
                concession_required=concession, concession_reason=conc_reason,
                concession_approved_by=random.choice(["Quality Manager", "Site Manager"]) if concession else None,
                concession_approved_date=date_str if concession else None,
            )
            session.add(batch)
            day_batches.append(batch_code)

        # === ORDERS (3-6 per day) ===
        for _ in range(random.randint(3, 6)):
            order_id += 1
            prod = random.choice(products)
            order = Order(
                id=order_id,
                customer=random.choices(customers, weights=[60, 12, 10, 5, 13])[0],
                product_id=prod.id,
                production_batch=random.choice(day_batches) if day_batches else None,
                quantity_kg=round(random.uniform(50, 400), 1),
                order_date=date_str,
                delivery_date=(date + timedelta(days=random.randint(1, 3))).strftime("%Y-%m-%d"),
                status=random.choice(["Delivered", "Delivered", "Delivered", "Pending", "In Transit"]),
            )
            session.add(order)

        # === TEMPERATURE LOGS (hourly per location) ===
        for loc in locations:
            limits = config["temperature"]["locations"][loc]
            mid = (limits["min"] + limits["max"]) / 2
            spread = (limits["max"] - limits["min"]) / 2

            for hour in range(24):
                temp_id += 1
                ts = date.replace(hour=hour, minute=random.randint(0, 59))

                # 3% chance of excursion
                if random.random() < 0.03:
                    temp = round(mid + spread * random.choice([-3, 3, 4]), 1)
                    is_exc = True
                else:
                    temp = round(mid + random.uniform(-spread * 0.5, spread * 0.5), 1)
                    is_exc = temp < limits["min"] or temp > limits["max"]

                tlog = TemperatureLog(
                    id=temp_id, location=loc, temperature=temp,
                    timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),
                    recorded_by=random.choice(["Auto-Sensor", "Auto-Sensor", "J. Smith", "P. Kapkoti"]),
                    is_excursion=is_exc,
                )
                session.add(tlog)

    session.commit()
    session.close()
    engine.dispose()

    print(f"Database seeded: {os.path.basename(__file__)}")
    print(f"  Products: {len(products)}")
    print(f"  Batches: {batch_id}")
    print(f"  Orders: {order_id}")
    print(f"  Temperature logs: {temp_id}")


if __name__ == "__main__":
    seed()
