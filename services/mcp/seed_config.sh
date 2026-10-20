#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
#
# Seeds TrendRadar's config directory from the defaults baked into the image
# (pinned upstream release, see defaults.json), then applies the optional
# whole-file overrides from Railway variables.
#
# Usage: seed_config.sh <config-dir> <keep|overwrite>
#   keep       copy only files that are missing (edits on a volume survive)
#   overwrite  always copy the defaults (services without a volume)
#
# Variables read:
#   CONFIG_LANGUAGE  en (default) or zh: which upstream config.yaml,
#                    frequency_words.txt and timeline.yaml to start from
#   CONFIG_RESEED    true: back up the directory and copy the defaults again
#                    (use once after changing CONFIG_LANGUAGE or upgrading)
#   CONFIG_YAML, FREQUENCY_WORDS, AI_INTERESTS, TIMELINE_YAML
#                    full file contents; when set they replace config.yaml,
#                    frequency_words.txt, ai_interests.txt, timeline.yaml
set -eu

dst=${1:?usage: seed_config.sh <config-dir> <keep|overwrite>}
mode=${2:-keep}
defaults=${DEFAULTS_DIR:-/opt/railway/defaults}

log() { printf '[config] %s\n' "$*"; }

lang=${CONFIG_LANGUAGE:-en}
case "$lang" in
  en|zh) ;;
  *) log "CONFIG_LANGUAGE must be en or zh (got '$lang'); using en" >&2; lang=en ;;
esac

mkdir -p "$dst"

if [ "$mode" = keep ] && [ "${CONFIG_RESEED:-false}" = true ] && [ -f "$dst/config.yaml" ]; then
  backup="$dst.bak-$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "$dst" "$backup"
  log "CONFIG_RESEED=true: previous config saved to $backup, copying the defaults again"
  log "set CONFIG_RESEED back to false, or every restart will reset files edited on the volume"
  mode=overwrite
fi

copy_tree() {
  src=$1
  (cd "$src" && find . -type f) | while IFS= read -r rel; do
    rel=${rel#./}
    target="$dst/$rel"
    if [ "$mode" = overwrite ] || [ ! -e "$target" ]; then
      mkdir -p "$(dirname "$target")"
      cp "$src/$rel" "$target.tmp.$$"
      mv "$target.tmp.$$" "$target"
      log "seeded $rel ($(basename "$src") defaults)"
    fi
  done
}

copy_tree "$defaults/common"
copy_tree "$defaults/$lang"
mkdir -p "$dst/custom/ai" "$dst/custom/keyword"

# Whole-file overrides. The variable names are fixed strings, so eval is safe.
write_var() {
  name=$1
  file=$2
  eval "value=\${$name:-}"
  case "$value" in
    '${{'*) log "WARNING: $name looks like an unresolved Railway reference; ignored" >&2; return 0 ;;
  esac
  if [ -n "$value" ]; then
    printf '%s\n' "$value" > "$dst/$file.tmp.$$"
    mv "$dst/$file.tmp.$$" "$dst/$file"
    log "$file written from the $name variable"
  fi
}

write_var CONFIG_YAML config.yaml
write_var FREQUENCY_WORDS frequency_words.txt
write_var AI_INTERESTS ai_interests.txt
write_var TIMELINE_YAML timeline.yaml

for file in config.yaml timeline.yaml; do
  if ! python -c 'import sys, yaml; yaml.safe_load(open(sys.argv[1], encoding="utf-8"))' "$dst/$file" 2>/dev/null; then
    log "WARNING: $dst/$file is not valid YAML; TrendRadar will fail to load it" >&2
  fi
done

log "config ready in $dst (defaults: $(cat "$defaults/VERSION" 2>/dev/null || echo unknown), language $lang)"
