# Databricks Setup Guide

## Step 1: Get Your Databricks Credentials

### Find Your Workspace URL
1. Log into your Databricks account
2. Your workspace URL is in the browser address bar, something like:
   - AWS: `https://dbc-12345678-abcd.cloud.databricks.com`
   - Azure: `https://adb-12345678.12.azuredatabricks.net`
   - GCP: `https://12345678.9.gcp.databricks.com`

### Create a Personal Access Token
1. In your Databricks workspace, click your profile icon (top right)
2. Go to **Settings** → **Developer** → **Access tokens**
3. Click **Generate new token**
4. Give it a name like "benchmark-tool"
5. Set expiration (recommend 90 days for testing)
6. Click **Generate**
7. **IMPORTANT:** Copy the token immediately - you won't be able to see it again!

## Step 2: Configure Authentication

Choose **ONE** of these methods:

### Option A: Environment Variables (Quick Testing)
```bash
export DATABRICKS_HOST='https://your-workspace.cloud.databricks.com'
export DATABRICKS_TOKEN='dapi1234567890abcdef...'
```

Add these to your `~/.zshrc` or `~/.bashrc` to make them permanent.

### Option B: Config File (Recommended)
Create `~/.databrickscfg`:
```ini
[DEFAULT]
host = https://your-workspace.cloud.databricks.com
token = dapi1234567890abcdef...
```

Set permissions:
```bash
chmod 600 ~/.databrickscfg
```

## Step 3: Test Connection

Run the test script:
```bash
uv run databricks/test_connection.py
```

You should see:
- ✓ Connected to Databricks!
- Your user info
- List of available SQL warehouses

## Step 4: Create SQL Warehouses (if needed)

You need 3 SQL warehouses for the benchmark:

| Size | Purpose | Databricks Equivalent | Cluster Size |
|------|---------|----------------------|--------------|
| X-Small | Budget comparison | Snowflake Small | 2X-Small |
| Small | **Primary baseline** | Snowflake Medium | X-Small or Small |
| Large | Performance ceiling | Snowflake X-Large | Medium or Large |

### To Create a Warehouse:
1. In Databricks, go to **SQL Warehouses** in the sidebar
2. Click **Create SQL Warehouse**
3. Configure:
   - **Name**: `benchmark_wh_xsmall` (or small/large)
   - **Cluster size**: Choose appropriate size
   - **Type**: Choose "Pro" or "Serverless" (Serverless most comparable to Snowflake)
   - **Auto stop**: 10 minutes (to save costs)
4. Click **Create**
5. **Copy the warehouse ID** from the URL or warehouse details

### Test SQL Connection:
```bash
uv run databricks/test_connection.py <warehouse-id>
```

## Step 5: Update Configuration

Edit [databricks/config.py](config.py) and update the `WAREHOUSES` dictionary with your warehouse IDs:

```python
WAREHOUSES = {
    "xsmall": "abc123def456",  # Your X-Small warehouse ID
    "small": "ghi789jkl012",   # Your Small warehouse ID
    "large": "mno345pqr678",   # Your Large warehouse ID
}
```

Also update the catalog/schema settings if needed:
```python
CATALOG = "main"  # or your preferred catalog
SCHEMA = "tpch_sf100"  # we'll create this next
```

## Step 6: Next Steps

Once connectivity is working:
1. ✓ Generate TPC-H dataset in Databricks (coming next)
2. ✓ Create benchmark runner (similar to Snowflake version)
3. ✓ Run benchmarks and compare results!

## Troubleshooting

### "Cannot configure default credentials"
- Make sure you've set either environment variables OR created ~/.databrickscfg
- Check for typos in your host URL and token
- Ensure the token hasn't expired

### "SQL warehouse not found"
- Verify the warehouse ID is correct (copy from Databricks UI)
- Make sure the warehouse exists and you have permission to use it
- Try starting the warehouse manually in the UI first

### "Permission denied" errors
- Check that your user has permission to access the catalog/schema
- You may need workspace admin to grant permissions

## Cost Considerations

- **SQL Warehouses cost money when running** (billed per DBU)
- Set auto-stop to 10-20 minutes to avoid unnecessary costs
- Serverless warehouses bill per query (similar to Snowflake)
- Classic warehouses bill for the time they're running
- Monitor your usage in the Databricks billing console
