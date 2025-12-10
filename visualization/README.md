# Benchmark Visualization

React dashboard for visualizing Snowflake vs Databricks benchmark results.

## Update Data

After running benchmarks, update the visualization data by exporting from DuckDB:

```bash
uv run visualization/update_data.py
```

This queries the `run_summary` view and exports to `src/data/benchmarkData.json`.

## Local Development

```bash
cd visualization
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Build for Production

```bash
npm run build
```

Output is in the `dist/` folder.

## Deploy to Google Cloud Run

### Prerequisites

1. Set your GCP project:
   ```bash
   export GCP_PROJECT=your-project-id
   ```

2. Authenticate and configure gcloud:
   ```bash
   gcloud auth login
   gcloud config set project $GCP_PROJECT
   ```

3. Verify you're in the right project:
   ```bash
   gcloud config get-value project
   ```

### Deploy

From the `visualization/` directory:

```bash
gcloud run deploy benchmark-viz \
  --project $GCP_PROJECT \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

This builds the Docker image and deploys it in one step.
