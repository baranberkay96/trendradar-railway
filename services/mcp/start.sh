#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
#
# TrendRadar MCP service for Railway (community template).
#   1. config: same pinned defaults and variable overrides as the crawler
#      (no volume here, so the defaults are copied on every boot),
#   2. data: initial copy of the crawler's SQLite history from the Bucket,
#      then a background loop keeps it current (sync_bucket.py),
#   3. server: upstream's FastMCP app behind a bearer token (serve.py).
set -eu

log() { printf '[railway] %s\n' "$*"; }

cd /app
/opt/railway/seed_config.sh /app/config overwrite
mkdir -p /app/output/news /app/output/rss

if [ -z "${MCP_TOKEN:-}" ]; then
  log "ERROR: MCP_TOKEN is empty; the MCP server never starts without a token" >&2
  exit 1
fi

if [ -n "${S3_BUCKET_NAME:-}" ] && [ -n "${S3_ENDPOINT_URL:-}" ]; then
  timeout "${MCP_INITIAL_SYNC_TIMEOUT:-180}" python /opt/railway/sync_bucket.py --once \
    || log "WARNING: initial bucket sync failed or timed out; the background loop retries" >&2
  (
    while :; do
      python /opt/railway/sync_bucket.py --loop || true
      log "bucket sync loop exited; restarting in 30 s" >&2
      sleep 30
    done
  ) &
else
  log "WARNING: no bucket configured; MCP tools only see data saved by trigger_crawl(save_to_local=true)" >&2
fi

exec python /opt/railway/serve.py
