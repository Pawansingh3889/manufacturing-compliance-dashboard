"""Allergen matrix generation and management."""
import pandas as pd

from modules.database import query


def get_allergen_matrix():
    """Generate a product x allergen cross-reference matrix."""
    try:
        products = query("SELECT id, name, species, category, allergens FROM products ORDER BY name")
    except Exception as e:
        import logging
        logging.error(f"Failed to query products for allergen matrix: {e}")
        return pd.DataFrame()

    if products.empty:
        return pd.DataFrame()

    # Get all unique allergens
    all_allergens = set()
    for _, row in products.iterrows():
        if row["allergens"]:
            for a in str(row["allergens"]).split(","):
                all_allergens.add(a.strip())

    all_allergens = sorted(all_allergens)

    # Build matrix
    matrix_data = []
    for _, row in products.iterrows():
        entry = {
            "Product": row["name"],
            "Species": row["species"],
            "Category": row["category"],
        }
        product_allergens = [a.strip() for a in str(row["allergens"]).split(",")] if row["allergens"] else []
        for allergen in all_allergens:
            entry[allergen] = "Y" if allergen in product_allergens else ""

        entry["Total Allergens"] = len(product_allergens)
        matrix_data.append(entry)

    return pd.DataFrame(matrix_data)


def get_products_with_allergen(allergen_name):
    """Find all products containing a specific allergen."""
    products = query("SELECT name, species, category, allergens FROM products")
    matches = products[products["allergens"].str.contains(allergen_name, case=False, na=False)]
    return matches


def get_allergen_summary():
    """Count how many products contain each allergen."""
    matrix = get_allergen_matrix()
    if matrix.empty:
        return {}

    allergen_cols = [c for c in matrix.columns if c not in ["Product", "Species", "Category", "Total Allergens"]]
    summary = {}
    for col in allergen_cols:
        count = (matrix[col] == "Y").sum()
        summary[col] = count

    return dict(sorted(summary.items(), key=lambda x: -x[1]))
