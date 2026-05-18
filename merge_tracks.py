#!/usr/bin/env python3
"""
Merge the 3 concurrent benchmark track DuckDBs into the canonical DB.

The 3-track run (adaptive / gen1 wait-for-suspend / gen1 immediate-drop) runs
concurrently, each writing its OWN duckdb file (DuckDB is single-writer, and
its lock handler prompts interactively — so one shared file would deadlock
three background processes). run_id is namespaced per track via
BENCHMARK_RUN_ID_BASE (adaptive=1000s, gen1-tail=2000s, gen1-notail=3000s) so
rows never collide and "highest run_id" stays globally meaningful.

This script rebuilds the canonical PROJECT_ROOT/benchmark_results.duckdb from
the 3 track DBs (raw rows only — enrichment + dbt + viz run afterwards on the
canonical DB). The canonical filename is preserved so the dbt catalog name
("benchmark_results") still resolves.

Usage:
    uv run merge_tracks.py .tracks/adaptive/benchmark_results.duckdb \
                           .tracks/gen1_tail/benchmark_results.duckdb \
                           .tracks/gen1_notail/benchmark_results.duckdb
"""

import sys
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from common.logging_config import get_logger  # noqa: E402
from common.storage import BenchmarkStorage  # noqa: E402
import duckdb  # noqa: E402

logger = get_logger(__name__)

CANONICAL = project_root / "benchmark_results.duckdb"
TABLES = ("snowflake_results", "run_metadata")


def merge(track_paths):
    track_paths = [Path(p).resolve() for p in track_paths]
    for p in track_paths:
        if not p.exists():
            logger.error(f"Track DB missing: {p}")
            sys.exit(1)

    # The canonical DB is fully reconstructable from the track DBs. If one
    # exists (e.g. a re-merge), move it aside with a timestamp rather than
    # silently overwriting.
    if CANONICAL.exists():
        backup = CANONICAL.with_name(
            f"benchmark_results.duckdb.premerge-{datetime.now():%Y%m%d-%H%M%S}"
        )
        CANONICAL.rename(backup)
        logger.info(f"Existing canonical DB moved aside -> {backup.name}")

    # Create the canonical schema (CREATE TABLE IF NOT EXISTS, with the new
    # idle_policy column + PK).
    BenchmarkStorage(CANONICAL)

    conn = duckdb.connect(str(CANONICAL))
    try:
        totals = {t: 0 for t in TABLES}
        for i, tp in enumerate(track_paths):
            alias = f"trk{i}"
            conn.execute(f"ATTACH '{tp}' AS {alias} (READ_ONLY)")
            existing = {
                r[0]
                for r in conn.execute(
                    f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_catalog = '{alias}'"
                ).fetchall()
            }
            for t in TABLES:
                if t not in existing:
                    continue
                before = conn.execute(
                    f"SELECT COUNT(*) FROM {alias}.{t}"
                ).fetchone()[0]
                if before == 0:
                    continue
                # Column-name-aligned insert (BY NAME) so a schema drift in
                # one track can't shift columns silently.
                conn.execute(
                    f"INSERT INTO {t} BY NAME SELECT * FROM {alias}.{t}"
                )
                totals[t] += before
                logger.info(f"  {tp.parent.name}.{t}: +{before} rows")
            conn.execute(f"DETACH {alias}")
        conn.commit()

        logger.info("Merge complete. Canonical row counts:")
        for t in TABLES:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            logger.info(f"  {t}: {n}")
        # Sanity: surface the idle_policy / warehouse_type spread so a
        # misconfigured track is obvious before the 3h enrich wait.
        spread = conn.execute(
            "SELECT warehouse_type, idle_policy, COUNT(*) "
            "FROM snowflake_results GROUP BY 1,2 ORDER BY 1,2"
        ).fetchall()
        logger.info(f"warehouse_type x idle_policy: {spread}")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: merge_tracks.py <track1.duckdb> [track2 ...]")
        sys.exit(1)
    merge(sys.argv[1:])
