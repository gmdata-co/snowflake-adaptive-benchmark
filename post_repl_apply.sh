#!/bin/bash
#
# QUEUED post-replication change (Option 1 for the USE_CACHED_RESULT clutter).
#
# Waits for the concurrent replication to fully finish, THEN:
#   1. ALTER USER <current_user> SET USE_CACHED_RESULT = FALSE   (account-side
#      default; every future benchmark session inherits FALSE).
#   2. Remove the now-redundant per-connection
#      `ALTER SESSION SET USE_CACHED_RESULT = FALSE` in
#      common/connections/snowflake_connection.py (the source of the
#      "ungodly" per-connection statement count in concurrent runs).
#
# Both are applied TOGETHER and ONLY after the replication is done, so the
# in-flight reps keep an identical, consistent cache-disable mechanism (never
# mixed mid-run, never a window where caching is silently re-enabled).

cd "$(dirname "$0")"
ROOT="$(pwd)"
LOG="$ROOT/post_repl_apply.log"
: > "$LOG"
log() { echo "==== $* $(date '+%Y-%m-%d %H:%M:%S') ====" | tee -a "$LOG"; }

log "WAITING for replicate_concurrent.DONE / .FAILED"
until [ -f "$ROOT/replicate_concurrent.DONE" ] || [ -f "$ROOT/replicate_concurrent.FAILED" ]; do
  sleep 60
done
log "Replication sentinel present ($(ls replicate_concurrent.DONE replicate_concurrent.FAILED 2>/dev/null)). Applying Option 1."

# 1. Account-side default.
uv run python - >> "$LOG" 2>&1 <<'PY'
from common.connections.snowflake_connection import SnowflakeConnection
from snowflake.config import (SNOWFLAKE_CONNECTION, SNOWFLAKE_ROLE,
                              SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA)
sc = SnowflakeConnection(connection_name=SNOWFLAKE_CONNECTION, role=SNOWFLAKE_ROLE,
                         database=SNOWFLAKE_DATABASE, schema=SNOWFLAKE_SCHEMA)
sc.connect()
cur = sc.connection.cursor()
user = cur.execute("SELECT CURRENT_USER()").fetchone()[0]
cur.execute(f'ALTER USER "{user}" SET USE_CACHED_RESULT = FALSE')
val = cur.execute(
    f"SHOW PARAMETERS LIKE 'USE_CACHED_RESULT' FOR USER \"{user}\""
).fetchall()
print(f"ALTER USER {user} SET USE_CACHED_RESULT=FALSE applied; SHOW -> {val}")
sc.disconnect()
PY

# 2. Idempotently drop the per-connection ALTER SESSION line.
uv run python - >> "$LOG" 2>&1 <<'PY'
from pathlib import Path
p = Path("common/connections/snowflake_connection.py")
src = p.read_text()
old = '''        # Disable result caching to ensure accurate benchmarking
        cursor = self.connection.cursor()
        cursor.execute("ALTER SESSION SET USE_CACHED_RESULT = FALSE")
        cursor.close()
'''
new = '''        # Result caching is disabled at the USER level
        # (ALTER USER ... SET USE_CACHED_RESULT = FALSE), so every session
        # inherits FALSE without a per-connection ALTER SESSION. This removed
        # the per-connection statement flood in the concurrent scenario
        # (one connection per query).
'''
if old in src:
    p.write_text(src.replace(old, new))
    print("snowflake_connection.py: per-connection ALTER SESSION removed.")
elif new.strip() in src:
    print("snowflake_connection.py: already updated (idempotent no-op).")
else:
    print("WARN: expected block not found verbatim; left file unchanged "
          "for manual review.")
PY

log "OPTION 1 APPLIED"
touch "$ROOT/post_repl_apply.DONE"
