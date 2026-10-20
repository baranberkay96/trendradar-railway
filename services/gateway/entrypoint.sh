#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
#
# Writes the login and MCP blocks imported by the Caddyfile, then starts Caddy.
set -eu

fail() { printf '[gateway] ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '[gateway] %s\n' "$*"; }

[ -n "${REPORTS_UPSTREAM:-}" ] || fail "REPORTS_UPSTREAM is not set (private host:port of the trendradar service)"
case "$REPORTS_UPSTREAM" in
  :*) fail "REPORTS_UPSTREAM has no host ('$REPORTS_UPSTREAM'); is the trendradar service missing?" ;;
esac

conf_dir=/tmp/gateway
mkdir -p "$conf_dir"

# --- login for the report pages ---------------------------------------------
if [ "${REPORTS_PUBLIC:-false}" = true ]; then
  log "REPORTS_PUBLIC=true: report pages are public (no login). /mcp still needs its token."
  printf 'vars reports_login off\n' > "$conf_dir/auth.caddy"
else
  user="${REPORTS_USERNAME:-}"
  pass="${REPORTS_PASSWORD:-}"
  [ -n "$user" ] || fail "REPORTS_USERNAME is empty (or set REPORTS_PUBLIC=true to drop the login)"
  [ -n "$pass" ] || fail "REPORTS_PASSWORD is empty (or set REPORTS_PUBLIC=true to drop the login)"
  case "$user" in
    *[!A-Za-z0-9._@-]*) fail "REPORTS_USERNAME may only contain letters, digits and . _ @ -" ;;
  esac
  [ "${#pass}" -ge 12 ] || fail "REPORTS_PASSWORD must be at least 12 characters"
  # Read from stdin so the password never appears in a process list.
  hash=$(printf '%s\n' "$pass" | caddy hash-password) || fail "could not hash REPORTS_PASSWORD"
  case "$hash" in
    '$2'*) ;;
    *) fail "unexpected output from caddy hash-password" ;;
  esac
  printf 'basic_auth bcrypt "TrendRadar" {\n\t%s %s\n}\n' "$user" "$hash" > "$conf_dir/auth.caddy"
  log "login enabled for user $user"
fi

# --- MCP route ----------------------------------------------------------------
mcp="${MCP_UPSTREAM:-}"
case "$mcp" in
  ""|:*)
    log "MCP_UPSTREAM is empty: /mcp answers 404 (the trendradar-mcp service is not deployed)"
    printf 'respond "TrendRadar MCP is not deployed in this project" 404\n' > "$conf_dir/mcp.caddy"
    ;;
  *[!A-Za-z0-9.:-]*)
    fail "MCP_UPSTREAM must be host:port (got '$mcp')"
    ;;
  *)
    printf 'reverse_proxy %s {\n\tflush_interval -1\n\tlb_try_duration 10s\n}\n' "$mcp" > "$conf_dir/mcp.caddy"
    log "/mcp -> $mcp (token checked by the MCP service)"
    ;;
esac

caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1 \
  || { caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile; fail "Caddyfile did not validate"; }

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
