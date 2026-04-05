"""Database engine with proper SQLAlchemy ORM tables."""
import os
import pandas as pd
import yaml
from sqlalchemy import create_engine, text, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

# Database URL — supports SQLite (demo) or SQL Server (production)
# Set COMPLIANCE_DB env var to connect to SQL Server/SSRS:
#   COMPLIANCE_DB=mssql+pyodbc://user:pass@server/database?driver=ODBC+Driver+17+for+SQL+Server
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_DB_ENV = os.getenv("COMPLIANCE_DB")
if _DB_ENV:
    DB_PATH = None
    DB_URL = _DB_ENV
else:
    _LOCAL_DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
    # Streamlit Cloud mounts the repo read-only. Detect by checking if the
    # data directory is writable; if not, fall back to a temp directory that
    # survives for the lifetime of the container.
    if os.access(_LOCAL_DATA_DIR, os.W_OK):
        DB_PATH = os.path.join(_LOCAL_DATA_DIR, "factory_compliance.db")
    else:
        import tempfile
        _TMP_DATA = os.path.join(tempfile.gettempdir(), "compliance_dashboard")
        os.makedirs(_TMP_DATA, exist_ok=True)
        DB_PATH = os.path.join(_TMP_DATA, "factory_compliance.db")
    DB_URL = f"sqlite:///{DB_PATH}"


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    species = Column(String)
    category = Column(String)
    product_type = Column(String)  # fresh or defrost
    shelf_life_type = Column(String)  # superchilled (+11/+12d) or standard (+7d)
    shelf_life_days = Column(Integer)
    storage_zone = Column(String)
    certification = Column(String)  # RSPCA, MSC, Standard
    allergens = Column(String)
    customer = Column(String, default="Retail")


class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True)
    batch_code = Column(String, nullable=False)  # Short trace code: F6036C
    batch_no = Column(String)  # Long SI batch number
    run_number = Column(String)  # SI Run Number
    product_id = Column(Integer, ForeignKey("products.id"))
    intake_date = Column(String)
    production_date = Column(String)  # Post Date in SI
    pack_date = Column(String)
    use_by_date = Column(String)  # Post Expiry Date in SI
    age_days = Column(Integer)  # Days since production (SI: Age)
    life_days = Column(Integer)  # Days of shelf life remaining (SI: Life)
    raw_material_batch = Column(String)
    trace_id = Column(String)  # SI Trace ID
    harvest_date = Column(String)  # Date fish was harvested/caught
    defrost_date = Column(String)  # Date product was defrosted (defrost only)
    intake_date_raw = Column(String)  # Raw material intake date
    supplier = Column(String)
    raw_input_kg = Column(Float)
    finished_output_kg = Column(Float)
    waste_kg = Column(Float)
    yield_pct = Column(Float)
    line_number = Column(Integer)  # Production Line in SI
    shift = Column(String)
    operator = Column(String)
    stock_location = Column(String)  # Coldstore, Blast Freezer, Despatch Bay
    stock_kg = Column(Float, default=0)
    stock_units = Column(Integer, default=0)
    status = Column(String, default="Complete")  # In Active, Complete, Despatched
    process_status = Column(String)  # SI: Process Status
    alert_flag = Column(Boolean, default=False)  # SI: Stop/Alert
    concession_required = Column(Boolean, default=False)
    concession_reason = Column(String)
    concession_approved_by = Column(String)
    concession_approved_date = Column(String)


class TemperatureLog(Base):
    __tablename__ = "temperature_logs"
    id = Column(Integer, primary_key=True)
    location = Column(String, nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(String, nullable=False)
    recorded_by = Column(String)
    is_excursion = Column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
    production_batch = Column(String)
    quantity_kg = Column(Float)
    order_date = Column(String)
    delivery_date = Column(String)
    status = Column(String)


def load_config():
    config_path = os.path.join(_PROJECT_ROOT, "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_engine():
    return create_engine(DB_URL, echo=False)


def query(sql, params=None):
    engine = get_engine()
    try:
        if params:
            return pd.read_sql(text(sql), engine, params=params)
        return pd.read_sql(sql, engine)
    finally:
        engine.dispose()


def scalar(sql, params=None):
    df = query(sql, params)
    if df.empty:
        return None
    return df.iloc[0, 0]


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    engine.dispose()


def drop_all():
    """Drop all tables."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    engine.dispose()
