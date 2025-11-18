#!/usr/bin/env python3
"""
Automated setup script to generate .env configuration file.

This script will:
1. Prompt for Snowflake configuration
2. Discover Databricks SQL warehouses and catalogs
3. Generate a configured .env file
"""

import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def check_env_exists():
    """Check if .env file already exists."""
    env_path = Path(".env")
    if env_path.exists():
        print("⚠️  .env file already exists!")
        response = input("Overwrite existing .env? (y/N): ").strip().lower()
        if response != "y":
            print("Cancelled. Keeping existing .env file.")
            return False
    return True


def get_snowflake_connections():
    """Get list of available Snowflake CLI connections."""
    try:
        # Try JSON format first (more reliable parsing)
        result = subprocess.run(
            ["snow", "connection", "list", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # Parse JSON output
            import json
            try:
                data = json.loads(result.stdout)
                connections = [conn.get("connection_name") for conn in data if conn.get("connection_name")]
                return connections if connections else None
            except json.JSONDecodeError:
                pass

        # Fall back to text parsing if JSON fails
        result = subprocess.run(
            ["snow", "connection", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        # Parse table output - skip header and table formatting
        connections = []
        for line in result.stdout.strip().split("\n"):
            # Skip empty lines and table formatting
            if not line.strip() or line.startswith("+"):
                continue

            # If it's a pipe-delimited table row
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                # parts[0] is empty (before first |), parts[1] is connection name
                if len(parts) > 1:
                    name = parts[1]
                    # Skip header row and empty parts
                    if name and name.lower() not in ("connection_name", ""):
                        connections.append(name)

        return connections if connections else None
    except FileNotFoundError:
        print("❌ Snowflake CLI not found. Install it with: uv sync")
        return None
    except subprocess.TimeoutExpired:
        print("❌ Snowflake connection list timed out")
        return None
    except Exception as e:
        print(f"❌ Error listing connections: {e}")
        return None


def test_snowflake_connection(connection_name):
    """Test if a Snowflake CLI connection is valid."""
    try:
        result = subprocess.run(
            ["snow", "connection", "test", "--connection", connection_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_snowflake_config():
    """Prompt for Snowflake configuration."""
    print_header("SNOWFLAKE CONFIGURATION")

    # Try to get list of available connections
    print("🔍 Checking for Snowflake CLI connections...\n")
    connections = get_snowflake_connections()

    if not connections:
        print("⚠️  No Snowflake connections found.")
        print("Please set up a connection first:")
        print("  snow connection add")
        print()
        sys.exit(1)

    # Show available connections
    print("📋 Available Snowflake connections:")
    for i, conn in enumerate(connections, 1):
        print(f"  {i}. {conn}")
    print()

    # Let user choose from list
    while True:
        choice = input("Select a connection (number): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(connections):
                connection = connections[idx]
                break
            else:
                print(f"❌ Please enter a number between 1 and {len(connections)}")
        except ValueError:
            print("❌ Please enter a valid number")

    # Test the selected connection
    print(f"\n🔍 Testing connection '{connection}'...")
    if test_snowflake_connection(connection):
        print("✅ Successfully connected to Snowflake!\n")
    else:
        print("⚠️  Connection test failed. Proceeding anyway (may fail at runtime).\n")

    role = input("Enter Snowflake role (default: BENCHMARK): ").strip() or "BENCHMARK"
    database = (
        input("Enter Snowflake database (default: BENCHMARK): ").strip()
        or "BENCHMARK"
    )
    schema = input("Enter Snowflake schema (default: BENCHMARK): ").strip() or "BENCHMARK"
    warehouse_prefix = (
        input("Enter warehouse prefix (default: BENCHMARK_WH): ").strip()
        or "BENCHMARK_WH"
    )

    return {
        "connection": connection,
        "role": role,
        "database": database,
        "schema": schema,
        "warehouse_prefix": warehouse_prefix,
    }


def get_databricks_config():
    """Prompt for Databricks credentials and discover warehouses."""
    print_header("DATABRICKS CONFIGURATION")

    host = input(
        "Enter Databricks workspace URL (e.g., https://dbc-xxx.cloud.databricks.com): "
    ).strip()
    if not host:
        print("❌ Databricks host is required!")
        return None

    token = input("Enter Databricks personal access token (dapi_...): ").strip()
    if not token:
        print("❌ Databricks token is required!")
        return None

    # Test connection and discover resources
    print("\n🔍 Connecting to Databricks and discovering resources...")
    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.core import Config

        config = Config(host=host, token=token)
        client = WorkspaceClient(config=config)

        # Test connection
        user = client.current_user.me()
        print(f"✅ Connected as: {user.user_name}\n")

        # Get warehouses
        print("📋 Available SQL Warehouses:")
        warehouses = list(client.warehouses.list())
        if not warehouses:
            print("⚠️  No SQL warehouses found. You need to create at least 3.")
            print(
                "   Go to: Databricks UI → SQL Warehouses → Create SQL Warehouse"
            )
            return None

        warehouse_map = {}
        for i, wh in enumerate(warehouses, 1):
            print(f"  {i}. {wh.name} (ID: {wh.id}) - {wh.cluster_size}")
            warehouse_map[str(i)] = {"id": wh.id, "name": wh.name}

        # Select warehouses for each size
        print("\n🎯 Select warehouses for benchmark (choose 3 different ones):")
        selected = {}
        for size in ["xsmall", "small", "large"]:
            while True:
                choice = (
                    input(f"  Which warehouse for {size.upper()}? (number): ")
                    .strip()
                    .lower()
                )
                if choice in warehouse_map:
                    selected[size] = warehouse_map[choice]["id"]
                    print(f"  ✅ Selected: {warehouse_map[choice]['name']}")
                    break
                print(f"  ❌ Invalid choice. Pick a number from 1-{len(warehouses)}")

        # Get catalogs and schemas
        print("\n📚 Discovering catalogs...")
        catalogs = list(client.catalogs.list())
        if not catalogs:
            print("⚠️  No catalogs found. Using 'main'")
            catalog = "main"
        else:
            print("  Available catalogs:")
            catalog_map = {}
            for i, cat in enumerate(catalogs, 1):
                print(f"    {i}. {cat.name}")
                catalog_map[str(i)] = cat.name

            choice = (
                input("  Select catalog (number, default 1): ").strip().lower() or "1"
            )
            catalog = catalog_map.get(choice, catalogs[0].name)
            print(f"  ✅ Selected: {catalog}")

        # Get schemas for selected catalog
        print(f"\n📚 Discovering schemas in catalog '{catalog}'...")
        try:
            schemas = list(client.schemas.list(catalog_name=catalog))
            if schemas:
                print("  Available schemas:")
                schema_map = {}
                for i, sch in enumerate(schemas, 1):
                    print(f"    {i}. {sch.name}")
                    schema_map[str(i)] = sch.name

                choice = (
                    input("  Select schema (number, default 1): ").strip().lower()
                    or "1"
                )
                schema = schema_map.get(choice, schemas[0].name)
                print(f"  ✅ Selected: {schema}")
            else:
                schema = input("  Enter schema name (default: benchmark): ").strip()
                schema = schema or "benchmark"
        except Exception as e:
            print(f"  Could not list schemas: {e}")
            schema = input("  Enter schema name (default: benchmark): ").strip()
            schema = schema or "benchmark"

        return {
            "host": host,
            "token": token,
            "catalog": catalog,
            "schema": schema,
            "warehouses": selected,
        }

    except ImportError:
        print("❌ Databricks SDK not found. Run: uv add databricks-sdk")
        return None
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Check your host URL and token, then try again.")
        return None


def generate_env_file(snowflake_config, databricks_config):
    """Generate .env file from collected configuration."""
    env_content = f"""# ============================================
# SNOWFLAKE CONFIGURATION
# ============================================

export SNOWFLAKE_CONNECTION={snowflake_config['connection']}
export SNOWFLAKE_ROLE={snowflake_config['role']}
export SNOWFLAKE_DATABASE={snowflake_config['database']}
export SNOWFLAKE_SCHEMA={snowflake_config['schema']}
export SNOWFLAKE_WAREHOUSE_PREFIX={snowflake_config['warehouse_prefix']}

# ============================================
# DATABRICKS CONFIGURATION
# ============================================

export DATABRICKS_HOST={databricks_config['host']}
export DATABRICKS_TOKEN={databricks_config['token']}
export DATABRICKS_CATALOG={databricks_config['catalog']}
export DATABRICKS_SCHEMA={databricks_config['schema']}
export DATABRICKS_WAREHOUSE_XSMALL={databricks_config['warehouses']['xsmall']}
export DATABRICKS_WAREHOUSE_SMALL={databricks_config['warehouses']['small']}
export DATABRICKS_WAREHOUSE_LARGE={databricks_config['warehouses']['large']}
"""

    env_path = Path(".env")
    env_path.write_text(env_content)
    print("\n✅ Configuration saved to .env")

    # Show summary
    print_header("CONFIGURATION SUMMARY")
    print("Snowflake:")
    print(f"  Connection: {snowflake_config['connection']}")
    print(f"  Database: {snowflake_config['database']}")
    print(f"  Schema: {snowflake_config['schema']}")
    print(f"  Role: {snowflake_config['role']}")
    print(f"  Warehouse prefix: {snowflake_config['warehouse_prefix']}")
    print("\nDatabricks:")
    print(f"  Host: {databricks_config['host']}")
    print(f"  Catalog: {databricks_config['catalog']}")
    print(f"  Schema: {databricks_config['schema']}")
    print(f"  Warehouse X-Small: {databricks_config['warehouses']['xsmall']}")
    print(f"  Warehouse Small: {databricks_config['warehouses']['small']}")
    print(f"  Warehouse Large: {databricks_config['warehouses']['large']}")
    print()
    print("You're all set! Run: uv run python main.py")


def main():
    """Main setup flow."""
    print_header("SNOWFLAKE vs DATABRICKS BENCHMARK - SETUP")

    if not check_env_exists():
        return

    # Get Snowflake config
    snowflake_config = get_snowflake_config()
    if not snowflake_config:
        sys.exit(1)

    # Get Databricks config
    databricks_config = get_databricks_config()
    if not databricks_config:
        sys.exit(1)

    # Generate .env file
    generate_env_file(snowflake_config, databricks_config)


if __name__ == "__main__":
    main()
