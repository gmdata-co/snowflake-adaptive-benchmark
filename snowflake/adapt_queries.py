#!/usr/bin/env python3
"""
Adapt TPC-H queries for Snowflake.
- Remove qgen metadata lines (:x, :o, :n)
- Replace parameter placeholders with actual values
- Update table references to use SNOWFLAKE_SAMPLE_DATA.TPCH_SF100
"""

import re
from pathlib import Path

# Parameter substitutions based on TPC-H specification defaults
# These are standard substitution values used in TPC-H benchmarking
QUERY_PARAMS = {
    1: {":1": "90"},
    2: {":1": "15", ":2": "BRASS", ":3": "EUROPE"},
    3: {":1": "BUILDING", ":2": "1995-03-15"},
    4: {":1": "1993-07-01"},
    5: {":1": "ASIA", ":2": "1994-01-01"},
    6: {":1": "1994-01-01", ":2": "0.06", ":3": "24"},
    7: {":1": "FRANCE", ":2": "GERMANY", ":3": "1995-01-01", ":4": "1996-12-31"},
    8: {":1": "BRAZIL", ":2": "AMERICA", ":3": "ECONOMY ANODIZED STEEL"},
    9: {":1": "green"},
    10: {":1": "1993-10-01"},
    11: {":1": "GERMANY", ":2": "0.0001"},
    12: {":1": "MAIL", ":2": "SHIP", ":3": "1994-01-01"},
    13: {":1": "special", ":2": "requests"},
    14: {":1": "1995-09-01"},
    15: {":1": "1996-01-01"},
    16: {
        ":1": "Brand#45",
        ":2": "MEDIUM POLISHED",
        ":3": "49",
        ":4": "14",
        ":5": "23",
        ":6": "45",
        ":7": "19",
        ":8": "3",
        ":9": "36",
        ":10": "9",
    },
    17: {":1": "Brand#23", ":2": "MED BOX"},
    18: {":1": "300"},
    19: {":1": "Brand#12", ":2": "Brand#23", ":3": "Brand#34"},
    20: {":1": "forest", ":2": "1994-01-01", ":3": "CANADA"},
    21: {":1": "SAUDI ARABIA"},
    22: {
        ":1": "13",
        ":2": "31",
        ":3": "23",
        ":4": "29",
        ":5": "30",
        ":6": "18",
        ":7": "17",
    },
}

# Table name mappings
TABLE_MAPPINGS = {
    "lineitem": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.LINEITEM",
    "orders": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.ORDERS",
    "customer": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.CUSTOMER",
    "part": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PART",
    "partsupp": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.PARTSUPP",
    "supplier": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.SUPPLIER",
    "nation": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.NATION",
    "region": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF100.REGION",
}


def clean_query(query_text: str, query_num: int) -> str:
    """
    Clean and adapt a TPC-H query for Snowflake.

    Args:
        query_text: Raw query text from qgen
        query_num: Query number (1-22)

    Returns:
        Cleaned and adapted query
    """
    lines = query_text.split("\n")
    cleaned_lines = []

    for line in lines:
        # Skip metadata lines
        if line.strip() in [":x", ":o"] or line.strip().startswith(":n"):
            continue
        cleaned_lines.append(line)

    query = "\n".join(cleaned_lines)

    # Replace parameter placeholders with actual values
    if query_num in QUERY_PARAMS:
        for placeholder, value in QUERY_PARAMS[query_num].items():
            # Handle different placeholder patterns
            query = query.replace(f"'{placeholder}'", f"'{value}'")
            query = query.replace(
                "':1' day (3)", f"'{value}' day"
            )  # Special case for Q1
            query = query.replace(placeholder, value)

    # Fix interval syntax for Snowflake (remove precision specifier)
    query = re.sub(
        r"interval\s+'(\d+)'\s+day\s+\(\d+\)",
        r"interval '\1 days'",
        query,
        flags=re.IGNORECASE,
    )

    # Replace table names with fully qualified Snowflake references
    for table, qualified_name in TABLE_MAPPINGS.items():
        # Use word boundaries to avoid partial matches
        query = re.sub(
            r"\b" + table + r"\b", qualified_name, query, flags=re.IGNORECASE
        )

    return query.strip()


def process_queries():
    """Process all TPC-H queries and save adapted versions."""
    queries_dir = Path("snowflake/queries")

    print("Adapting TPC-H queries for Snowflake...")

    for i in range(1, 23):
        input_file = queries_dir / f"{i}.sql"
        output_file = queries_dir / f"q{i:02d}.sql"

        if not input_file.exists():
            print(f"Warning: {input_file} not found, skipping...")
            continue

        # Read original query
        with open(input_file, "r") as f:
            original = f.read()

        # Clean and adapt
        adapted = clean_query(original, i)

        # Write adapted query
        with open(output_file, "w") as f:
            f.write(adapted)
            f.write("\n")

        print(f"  ✓ Query {i:2d} -> q{i:02d}.sql")

    print("\nSuccessfully adapted 22 TPC-H queries!")


if __name__ == "__main__":
    process_queries()
