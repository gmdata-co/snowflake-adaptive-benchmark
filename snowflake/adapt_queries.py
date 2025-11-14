#!/usr/bin/env python3
"""
Adapt TPC-H queries for Snowflake.
- Remove qgen metadata lines (:x, :o, :n)
- Replace parameter placeholders with actual values
- Update table references to use SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000
"""

import logging
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

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
    15: {":1": "1996-01-01", ":s": "0"},  # :s is view name suffix, just use 0
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
    19: {
        ":1": "Brand#12",
        ":2": "Brand#23",
        ":3": "Brand#34",
        ":4": "1",
        ":5": "10",
        ":6": "20",
    },
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
    "lineitem": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.LINEITEM",
    "orders": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.ORDERS",
    "customer": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.CUSTOMER",
    "part": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.PART",
    "partsupp": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.PARTSUPP",
    "supplier": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.SUPPLIER",
    "nation": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.NATION",
    "region": "SNOWFLAKE_SAMPLE_DATA.TPCH_SF1000.REGION",
}


def convert_q15_view_to_cte(query: str) -> str:
    """
    Convert Query 15's CREATE VIEW / SELECT / DROP VIEW pattern to a CTE.

    Pattern:
        CREATE VIEW revenue0 (...) AS <view_query>;
        <main_query> ... FROM ... revenue0 ...;
        DROP VIEW revenue0;

    Converts to:
        WITH revenue0 AS (<view_query>)
        <main_query> ... FROM ... revenue0 ...;
    """
    # Extract the view definition with column names
    create_match = re.search(
        r"create\s+view\s+(\w+)\s*\(([^)]+)\)\s+as\s+(.*?);\s*select",
        query,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not create_match:
        return query

    view_name = create_match.group(1)
    column_names = create_match.group(2).strip()
    view_query = create_match.group(3).strip()

    # Extract the main SELECT query (everything between view creation and DROP)
    main_match = re.search(
        r";\s*(select.*?);?\s*drop\s+view", query, flags=re.IGNORECASE | re.DOTALL
    )

    if not main_match:
        return query

    main_query = main_match.group(1).strip()

    # Construct CTE version with column names
    cte_query = f"WITH {view_name} ({column_names}) AS (\n{view_query}\n)\n{main_query}"

    return cte_query


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
    # Sort by placeholder length (longest first) to avoid partial replacements
    if query_num in QUERY_PARAMS:
        sorted_params = sorted(
            QUERY_PARAMS[query_num].items(), key=lambda x: len(x[0]), reverse=True
        )
        for placeholder, value in sorted_params:
            # Handle different placeholder patterns
            query = query.replace(f"'{placeholder}'", f"'{value}'")
            query = query.replace(
                "':1' day (3)", f"'{value}' day"
            )  # Special case for Q1
            query = query.replace(placeholder, value)

    # Fix interval syntax for Snowflake
    # Pattern 1: interval '90' day (3) -> INTERVAL '90 DAYS'
    query = re.sub(
        r"interval\s+'(\d+)'\s+day\s+\(\d+\)",
        r"INTERVAL '\1 DAYS'",
        query,
        flags=re.IGNORECASE,
    )

    # Pattern 2: interval '3' month -> INTERVAL '3 MONTH'
    query = re.sub(
        r"interval\s+'(\d+)'\s+(month|year|day)s?\b",
        r"INTERVAL '\1 \2'",
        query,
        flags=re.IGNORECASE,
    )

    # Fix substring syntax: substring(col from start for len) -> SUBSTR(col, start, len)
    query = re.sub(
        r"substring\s*\(\s*(\w+)\s+from\s+(\d+)\s+for\s+(\d+)\s*\)",
        r"SUBSTR(\1, \2, \3)",
        query,
        flags=re.IGNORECASE,
    )

    # Special handling for Query 15 - convert view to CTE
    if query_num == 15:
        query = convert_q15_view_to_cte(query)

    # Replace table names with fully qualified Snowflake references
    # Only replace in FROM clauses and JOINs, not in aliases or other contexts
    for table, qualified_name in TABLE_MAPPINGS.items():
        # Pattern 1: FROM/JOIN table_name (optionally followed by alias or comma)
        query = re.sub(
            r"\b(from|join)\s+" + table + r"\b(?!\s*\.)",
            r"\1 " + qualified_name,
            query,
            flags=re.IGNORECASE,
        )
        # Pattern 2: FROM/JOIN ... , table_name (comma-separated tables in FROM)
        query = re.sub(
            r",(\s*)" + table + r"\b(?!\s*\.)",
            r",\1" + qualified_name,
            query,
            flags=re.IGNORECASE,
        )

    return query.strip()


def process_queries():
    """Process all TPC-H queries and save adapted versions."""
    queries_dir = Path("snowflake/queries")
    original_dir = queries_dir / "original_queries"
    adapted_dir = queries_dir / "adapted_queries"

    logger.info("Adapting TPC-H queries for Snowflake...")

    for i in range(1, 23):
        input_file = original_dir / f"{i}.sql"
        output_file = adapted_dir / f"q{i:02d}.sql"

        if not input_file.exists():
            logger.warning(f"Warning: {input_file} not found, skipping...")
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

        logger.info(f"  ✓ Query {i:2d} -> q{i:02d}.sql")

    logger.info("\nSuccessfully adapted 22 TPC-H queries!")


if __name__ == "__main__":
    process_queries()
