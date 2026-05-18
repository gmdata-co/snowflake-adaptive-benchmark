# Benchmark Visualization

React dashboard for the Snowflake Adaptive vs Gen1 benchmark report.

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

Output is written to `dist/`.

## Deploy

The site is hosted as static files on a Google Cloud Storage bucket and
served directly over HTTPS.

**Live URL:** https://storage.googleapis.com/adaptive-benchmark/index.html

From the `visualization/` directory, after a production build:

```bash
gcloud storage rsync dist gs://adaptive-benchmark \
  --recursive \
  --delete-unmatched-destination-objects
```

`--delete-unmatched-destination-objects` clears old hashed JS/CSS bundles so
the bucket only ever holds the current build. The bucket already has
`allUsers` granted `roles/storage.objectViewer`, so no per-deploy ACL changes
are needed.

> Deploying requires write access to the `adaptive-benchmark` bucket via your
> own authenticated `gcloud` account and its project. Run `gcloud auth login`
> and set the project before your first deploy.
