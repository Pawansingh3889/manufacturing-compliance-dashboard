# Databricks notebook source
# MAGIC %md
# MAGIC # Manufacturing Compliance Analytics
# MAGIC
# MAGIC Batch analytics on production data using Databricks + PySpark.
# MAGIC Reads from factory compliance database, computes yield, temperature excursions,
# MAGIC shelf life risk, and daily OEE metrics.
# MAGIC
# MAGIC **Data sources:** SQLite (local) or Delta Lake (production)
# MAGIC
# MAGIC **Outputs:** Delta tables for downstream dashboards

# COMMAND ----------

from pyspark.sql import functions as F  # noqa: F401

# `spark` and `display` are provided by the Databricks runtime
# ruff: noqa: F821

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Data
# MAGIC In production, replace with Delta Lake tables:
# MAGIC ```python
# MAGIC batches = spark.read.table("compliance.batches")
# MAGIC temp_logs = spark.read.table("compliance.temperature_logs")
# MAGIC ```

# COMMAND ----------

# For demo: create sample data
batch_data = [
    (1, "B-20260315-A-01", "2026-03-15", "SKU-001", 1, "morning", "OP-001",
     100.0, 85.0, 15.0, 85.0, 3, 7, "released", False, False),
    (2, "B-20260315-A-02", "2026-03-15", "SKU-002", 1, "morning", "OP-002",
     120.0, 108.0, 12.0, 90.0, 5, 7, "released", False, False),
    (3, "B-20260315-B-01", "2026-03-15", "SKU-001", 2, "afternoon", "OP-003",
     95.0, 80.0, 15.0, 84.2, 6, 7, "hold", True, True),
    (4, "B-20260316-A-01", "2026-03-16", "SKU-003", 1, "morning", "OP-001",
     110.0, 99.0, 11.0, 90.0, 1, 14, "released", False, False),
    (5, "B-20260316-B-01", "2026-03-16", "SKU-002", 2, "night", "OP-004",
     130.0, 104.0, 26.0, 80.0, 2, 7, "released", True, False),
]

batch_cols = [
    "id", "batch_code", "production_date", "product_code", "line_number",
    "shift", "operator", "raw_input_kg", "finished_output_kg", "waste_kg",
    "yield_pct", "age_days", "life_days", "status", "alert_flag", "concession_required"
]

batches = spark.createDataFrame(batch_data, batch_cols)
batches.createOrReplaceTempView("batches")
display(batches)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Yield Analysis by Line and Shift

# COMMAND ----------

yield_analysis = (
    batches.filter(F.col("raw_input_kg") > 0)
    .groupBy("shift", "line_number")
    .agg(
        F.count("id").alias("batch_count"),
        F.sum("raw_input_kg").alias("total_input_kg"),
        F.sum("finished_output_kg").alias("total_output_kg"),
        F.sum("waste_kg").alias("total_waste_kg"),
        F.round(F.avg("yield_pct"), 2).alias("avg_yield_pct"),
    )
    .withColumn(
        "waste_pct",
        F.round(F.col("total_waste_kg") / F.col("total_input_kg") * 100, 2),
    )
    .orderBy("shift", "line_number")
)

display(yield_analysis)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Shelf Life Risk Scoring

# COMMAND ----------

shelf_life_risk = (
    batches.filter(F.col("life_days") > 0)
    .withColumn("remaining_days", F.col("life_days") - F.col("age_days"))
    .withColumn(
        "risk_level",
        F.when(F.col("remaining_days") <= 0, "EXPIRED")
        .when(F.col("remaining_days") <= 2, "CRITICAL")
        .when(F.col("remaining_days") <= 5, "WARNING")
        .otherwise("OK"),
    )
    .select(
        "batch_code", "production_date", "age_days", "life_days",
        "remaining_days", "risk_level", "status", "concession_required",
    )
    .orderBy("remaining_days")
)

display(shelf_life_risk)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Daily Production & OEE

# COMMAND ----------

daily_production = (
    batches.groupBy("production_date", "line_number")
    .agg(
        F.count("id").alias("batches_run"),
        F.sum("finished_output_kg").alias("total_output_kg"),
        F.sum("waste_kg").alias("total_waste_kg"),
        F.round(F.avg("yield_pct"), 2).alias("avg_yield_pct"),
        F.sum(F.col("alert_flag").cast("int")).alias("alert_count"),
    )
    .withColumn(
        "quality_rate",
        F.round(
            F.col("total_output_kg") /
            (F.col("total_output_kg") + F.col("total_waste_kg")),
            3,
        ),
    )
    .orderBy("production_date", "line_number")
)

display(daily_production)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Write to Delta Lake (Production)
# MAGIC
# MAGIC ```python
# MAGIC yield_analysis.write.format("delta").mode("overwrite").saveAsTable("compliance.yield_analysis")
# MAGIC shelf_life_risk.write.format("delta").mode("overwrite").saveAsTable("compliance.shelf_life_risk")
# MAGIC daily_production.write.format("delta").mode("overwrite").saveAsTable("compliance.daily_production")
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Temperature Anomaly Detection (SQL)

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Rolling average temperature with anomaly flag
# MAGIC -- In production, run against compliance.temperature_logs Delta table
# MAGIC
# MAGIC -- CREATE OR REPLACE VIEW compliance.temp_anomalies AS
# MAGIC -- SELECT
# MAGIC --   location,
# MAGIC --   timestamp,
# MAGIC --   temperature,
# MAGIC --   AVG(temperature) OVER (
# MAGIC --     PARTITION BY location
# MAGIC --     ORDER BY timestamp
# MAGIC --     ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
# MAGIC --   ) AS rolling_avg_24h,
# MAGIC --   CASE
# MAGIC --     WHEN ABS(temperature - AVG(temperature) OVER (
# MAGIC --       PARTITION BY location ORDER BY timestamp
# MAGIC --       ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
# MAGIC --     )) > 2 * STDDEV(temperature) OVER (
# MAGIC --       PARTITION BY location ORDER BY timestamp
# MAGIC --       ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
# MAGIC --     ) THEN TRUE
# MAGIC --     ELSE FALSE
# MAGIC --   END AS is_anomaly
# MAGIC -- FROM compliance.temperature_logs
