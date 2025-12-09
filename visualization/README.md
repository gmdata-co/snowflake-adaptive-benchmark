# Benchmark Visualization

React dashboard for visualizing Snowflake vs Databricks benchmark results.

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

The app is deployed to Cloud Run in the `select-dev` project.

**Live URL:** https://benchmark-viz-63679396994.us-central1.run.app/

### Prerequisites

1. Switch to the correct Google account and project:
   ```bash
   gcloud auth login
   gcloud config set project select-dev
   ```

2. Verify you're in the right project:
   ```bash
   gcloud config get-value project
   ```

### Deploy

From the `visualization/` directory:

```bash
gcloud run deploy benchmark-viz \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

This builds the Docker image and deploys it in one step.
