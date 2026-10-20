#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
#
# TrendRadar crawler service for Railway (community template).
#
# Same run model as upstream's docker/entrypoint.sh in RUN_MODE=cron (one
# crawl at boot when IMMEDIATE_RUN=true, then supercronic runs
# `python -m trendradar` on CRON_SCHEDULE), with these Railway additions:
#   - config and reports live on the /data volume (seeded from the pinned
#     upstream defaults on first boot, see seed_config.sh),
#   - a dual-stack report server with /healthz replaces upstream's viewer,
#   - AI analysis/translation switch on only when AI_API_KEY is set,
#   - the boot crawl waits for the private newsnow service,
#   - a daily job prunes old HTML snapshots from the volume.
set -eu

log() { printf '[railway] %s\n' "$*"; }

DATA_DIR=${DATA_DIR:-/data}
export REPORT_DIR="$DATA_DIR/output"
mkdir -p "$DATA_DIR/config" "$REPORT_DIR"
# /app/config and /app/output are symlinks to these folders (see Dockerfile).

/opt/railway/seed_config.sh "$DATA_DIR/config" keep

# --- storage ---------------------------------------------------------------
if [ "${STORAGE_BACKEND:-}" = remote ]; then
  missing=""
  for var in S3_ENDPOINT_URL S3_BUCKET_NAME S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY; do
    eval "val=\${$var:-}"
    [ -n "$val" ] || missing="$missing $var"
  done
  if [ -n "$missing" ]; then
    log "WARNING: STORAGE_BACKEND=remote but$missing empty; using local SQLite on the volume instead" >&2
    export STORAGE_BACKEND=local
  else
    log "storage: SQLite history in bucket $S3_BUCKET_NAME, HTML reports on $REPORT_DIR"
  fi
fi

# --- AI switches -----------------------------------------------------------
# Upstream's English config enables AI analysis and translation; without a key
# every run would print an error block. Empty variable = follow AI_API_KEY.
if [ -n "${AI_API_KEY:-}" ]; then ai_default=true; else ai_default=false; fi
[ -n "${AI_ANALYSIS_ENABLED:-}" ] || export AI_ANALYSIS_ENABLED=$ai_default
[ -n "${AI_TRANSLATION_ENABLED:-}" ] || export AI_TRANSLATION_ENABLED=$ai_default
log "AI analysis=$AI_ANALYSIS_ENABLED translation=$AI_TRANSLATION_ENABLED model=${AI_MODEL:-config default}"
if [ "$ai_default" = false ] && [ "${AI_FILTER_ENABLED:-false}" = true ]; then
  log "WARNING: AI_FILTER_ENABLED=true without AI_API_KEY; the AI filter cannot run" >&2
fi

# --- report server ---------------------------------------------------------
if [ ! -f "$REPORT_DIR/index.html" ]; then
  cat > "$REPORT_DIR/index.html" <<'HTML'
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60"><title>TrendRadar</title></head>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;line-height:1.5">
<h1>TrendRadar is collecting its first report</h1>
<p>The first crawl starts when the service boots and usually finishes within a few minutes.
This page reloads every minute. If it stays here, check the TrendRadar service logs.</p>
<p>Older reports: <a href="/html/">/html/</a></p>
</body></html>
HTML
fi

(
  while :; do
    python /opt/railway/report_server.py || true
    log "report server exited; restarting in 2 s" >&2
    sleep 2
  done
) &

# --- schedule --------------------------------------------------------------
CRON_EXPR=${CRON_SCHEDULE:-*/30 * * * *}
PRUNE_EXPR=${REPORT_PRUNE_SCHEDULE:-17 3 * * *}
for expr in "$CRON_EXPR" "$PRUNE_EXPR"; do
  # Same character check as upstream's entrypoint.
  if ! printf '%s\n' "$expr" | grep -qE '^[0-9*/,[:space:]-]+$'; then
    log "ERROR: invalid cron expression: '$expr' (five fields; digits, * / , - and spaces only)" >&2
    exit 1
  fi
done
cat > /tmp/crontab <<EOF
$CRON_EXPR cd /app && python -m trendradar
$PRUNE_EXPR python /opt/railway/prune_reports.py
EOF
log "crontab:"
cat /tmp/crontab
/usr/local/bin/supercronic -test /tmp/crontab

# --- first crawl -----------------------------------------------------------
wait_for_newsnow() {
  api=${PLATFORMS_API_URL:-}
  case "$api" in
    */api/s) ;;
    *) return 0 ;;
  esac
  probe="${api%/s}/latest"
  timeout=${NEWSNOW_WAIT_SECONDS:-300}
  python - "$probe" "$timeout" <<'PY' || log "WARNING: newsnow did not answer in time; crawling anyway" >&2
import sys, time, urllib.request
url, timeout = sys.argv[1], int(sys.argv[2])
deadline = time.time() + timeout
last = None
while True:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                print(f"[railway] newsnow ready: {url}", flush=True)
                sys.exit(0)
    except Exception as error:
        last = error
    if time.time() > deadline:
        print(f"[railway] newsnow not ready after {timeout}s ({url}): {last}", flush=True)
        sys.exit(1)
    time.sleep(5)
PY
}

if [ "${IMMEDIATE_RUN:-true}" = true ]; then
  wait_for_newsnow
  log "first crawl (IMMEDIATE_RUN=true)"
  (cd /app && python -m trendradar) || log "WARNING: first crawl failed; the schedule keeps running" >&2
fi

log "starting supercronic: $CRON_EXPR"
exec /usr/local/bin/supercronic -passthrough-logs /tmp/crontab
