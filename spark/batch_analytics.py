"""PySpark batch analytics for manufacturing compliance data.

Reads from the SQLite database and produces Parquet outputs:
- yield_analysis/       yield %, waste % by product, line, shift
- temperature_report/   excursion rates, avg temp by location
- shelf_life_risk/      batches approaching or exceeding shelf life
- daily_production/     daily throughput, defect rates, OEE proxy
"""

from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


DB_PATH = Path(__file__).parent.parent / "data" / "factory_compliance.db"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "spark_output"
JDBC_URL = f"jdbc:sqlite:{DB_PATH.resolve()}"


def read_table(spark: SparkSession, table: str):
    return spark.read.format("jdbc").options(
        url=JDBC_URL,
        dbtable=table,
        driver="org.sqlite.JDBC",
    ).load()


def compute_yield_analysis(batches):
    """Yield %, waste % grouped by product, line, shift."""
    return (
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


def compute_temperature_report(temp_logs):
    """Excursion rate and avg temperature by location."""
    return (
        temp_logs.groupBy("location")
        .agg(
            F.count("id").alias("total_readings"),
            F.sum(F.col("is_excursion").cast("int")).alias("excursion_count"),
            F.round(F.avg("temperature"), 2).alias("avg_temp_c"),
            F.round(F.min("temperature"), 2).alias("min_temp_c"),
            F.round(F.max("temperature"), 2).alias("max_temp_c"),
        )
        .withColumn(
            "excursion_rate_pct",
            F.round(F.col("excursion_count") / F.col("total_readings") * 100, 2),
        )
        .orderBy(F.desc("excursion_rate_pct"))
    )


def compute_shelf_life_risk(batches):
    """Flag batches where age_days is approaching or exceeding life_days."""
    return (
        batches.filter(F.col("life_days") > 0)
        .withColumn(
            "remaining_days",
            F.col("life_days") - F.col("age_days"),
        )
        .withColumn(
            "risk_level",
            F.when(F.col("remaining_days") <= 0, "EXPIRED")
            .when(F.col("remaining_days") <= 2, "CRITICAL")
            .when(F.col("remaining_days") <= 5, "WARNING")
            .otherwise("OK"),
        )
        .filter(F.col("risk_level") != "OK")
        .select(
            "batch_code", "production_date", "use_by_date",
            "age_days", "life_days", "remaining_days",
            "risk_level", "status", "concession_required",
        )
        .orderBy("remaining_days")
    )


def compute_daily_production(batches):
    """Daily throughput and OEE proxy per production line."""
    return (
        batches.filter(F.col("production_date").isNotNull())
        .groupBy("production_date", "line_number")
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
                (F.col("total_output_kg"))
                / (F.col("total_output_kg") + F.col("total_waste_kg")),
                3,
            ),
        )
        .orderBy("production_date", "line_number")
    )


def run_pipeline(spark: SparkSession) -> None:
    batches = read_table(spark, "batches")
    temp_logs = read_table(spark, "temperature_logs")

    batches.cache()
    temp_logs.cache()
    print(f"Loaded: {batches.count()} batches, {temp_logs.count()} temperature logs")

    yield_df = compute_yield_analysis(batches)
    yield_df.write.mode("overwrite").parquet(str(OUTPUT_DIR / "yield_analysis"))
    print(f"Yield analysis: {yield_df.count()} rows")
    yield_df.show(truncate=False)

    temp_df = compute_temperature_report(temp_logs)
    temp_df.write.mode("overwrite").parquet(str(OUTPUT_DIR / "temperature_report"))
    print(f"Temperature report: {temp_df.count()} rows")
    temp_df.show(truncate=False)

    risk_df = compute_shelf_life_risk(batches)
    risk_df.write.mode("overwrite").parquet(str(OUTPUT_DIR / "shelf_life_risk"))
    print(f"Shelf life risk: {risk_df.count()} rows")
    risk_df.show(truncate=False)

    daily_df = compute_daily_production(batches)
    daily_df.write.mode("overwrite").parquet(str(OUTPUT_DIR / "daily_production"))
    print(f"Daily production: {daily_df.count()} rows")
    daily_df.show(5, truncate=False)


if __name__ == "__main__":
    spark = (
        SparkSession.builder
        .appName("compliance-batch-analytics")
        .master("local[*]")
        .config("spark.jars.packages", "org.xerial:sqlite-jdbc:3.46.0.0")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    run_pipeline(spark)

    spark.stop()
    print("Pipeline complete.")
