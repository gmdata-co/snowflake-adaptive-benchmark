# Databricks Setup Guide

## Quick Start (Recommended)

Run the automated setup script from the **project root**:

```bash
uv run setup_config.py
```

This script will:
1. ✓ Prompt for your Snowflake connection name
2. ✓ Prompt for Databricks credentials
3. ✓ Discover available catalogs and schemas
4. ✓ Generate a configured `.env` file

**Note:** SQL Warehouses are created and destroyed automatically during benchmark runs. No manual warehouse configuration needed.

---

## Manual Setup (if needed)

### Step 1: Get Your Databricks Credentials

#### Find Your Workspace URL
1. Log into your Databricks account
2. Your workspace URL is in the browser address bar, something like:
   - AWS: `https://dbc-12345678-abcd.cloud.databricks.com`
   - Azure: `https://adb-12345678.12.azuredatabricks.net`
   - GCP: `https://12345678.9.gcp.databricks.com`

#### Create a Personal Access Token
1. In your Databricks workspace, click your profile icon (top right)
2. Go to **Settings** → **Developer** → **Access tokens**
3. Click **Generate new token**
4. Give it a name like "benchmark-tool"
5. Set expiration (recommend 90 days for testing)
6. Click **Generate**
7. **IMPORTANT:** Copy the token immediately - you won't be able to see it again!

### Step 2: Configure Authentication

Choose **ONE** of these methods:

#### Option A: Environment Variables (Quick Testing)
```bash
export DATABRICKS_HOST='https://your-workspace.cloud.databricks.com'
export DATABRICKS_TOKEN='dapi1234567890abcdef...'
```

Add these to your `~/.zshrc` or `~/.bashrc` to make them permanent.

#### Option B: Config File (Recommended)
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

### Step 3: Test Connection

Run the test script:
```bash
uv run databricks/test_connection.py
```

You should see:
- ✓ Connected to Databricks!
- Your user info
- List of available SQL warehouses

### Step 4: Update Configuration

Edit `.env` file in the project root and add your Databricks configuration:

```bash
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=dapi1234567890abcdef...
export DATABRICKS_CATALOG=your_catalog
export DATABRICKS_SCHEMA=your_schema
```

**Note:** SQL Warehouses are created and destroyed automatically during benchmark runs. The benchmark creates Serverless SQL warehouses with the following sizes:

| Size | Cluster Size | Purpose |
|------|--------------|---------|
| X-Small | 2X-Small | Budget comparison (equivalent to Snowflake Small) |
| Small | Small | Primary baseline (equivalent to Snowflake Medium) |
| Large | Large | Performance ceiling (equivalent to Snowflake X-Large) |

### Step 5: Next Steps

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
