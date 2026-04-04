"""Database connection layer. Supports SQLite (demo) and PostgreSQL (production)."""
import os
import pandas as pd
import yaml
from sqlalchemy import create_engine, text


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_engine():
    """Create a fresh engine each time to avoid stale connection issues."""
    config = load_config()
    db_url = config["database"]["url"]

    # Handle relative SQLite paths
    if "sqlite:///" in db_url and not db_url.startswith("sqlite:////"):
        db_path = db_url.replace("sqlite:///", "")
        abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_path)
        db_url = f"sqlite:///{abs_path}"

    return create_engine(db_url, echo=False)


def query(sql, params=None):
    """Run a SQL query and return a DataFrame."""
    engine = get_engine()
    try:
        if params:
            return pd.read_sql(text(sql), engine, params=params)
        return pd.read_sql(sql, engine)
    finally:
        engine.dispose()


def scalar(sql, params=None):
    """Run a query and return a single value."""
    df = query(sql, params)
    if df.empty:
        return None
    return df.iloc[0, 0]
