"""Database connection layer. Supports SQLite (demo) and PostgreSQL (production)."""
import pandas as pd
import yaml
from sqlalchemy import create_engine, text


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        config = load_config()
        _engine = create_engine(config["database"]["url"], echo=False)
    return _engine


def query(sql, params=None):
    engine = get_engine()
    if params:
        return pd.read_sql(text(sql), engine, params=params)
    return pd.read_sql(sql, engine)


def scalar(sql):
    df = query(sql)
    if df.empty:
        return None
    return df.iloc[0, 0]
