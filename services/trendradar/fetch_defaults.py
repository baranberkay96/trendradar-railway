#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build-time helper: download TrendRadar's default config files.

Reads defaults.json (repo, commit, file list with SHA-256), downloads every file
from raw.githubusercontent.com at the pinned commit, verifies its hash and writes
it below the target directory. Any mismatch or download failure fails the image
build, so a deploy never boots with unknown config files.

Usage: python fetch_defaults.py <defaults.json> <target-dir>
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time
import urllib.request

RETRIES = 4
TIMEOUT_SECONDS = 30


def download(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "trendradar-railway-build"})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except Exception as error:  # network errors are retried, then reported
            last_error = error
            print(f"[defaults] {url}: attempt {attempt}/{RETRIES} failed: {error}", flush=True)
            time.sleep(2 * attempt)
    raise SystemExit(f"[defaults] giving up on {url}: {last_error}")


def main(manifest_path: str, target_dir: str) -> int:
    manifest = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    base = f"https://raw.githubusercontent.com/{manifest['repo']}/{manifest['commit']}/"
    target = pathlib.Path(target_dir)
    for entry in manifest["files"]:
        data = download(base + entry["src"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"]:
            raise SystemExit(f"[defaults] SHA-256 mismatch for {entry['src']}: got {digest}, want {entry['sha256']}")
        destination = target / entry["dst"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        print(f"[defaults] {entry['src']} -> {destination} ({len(data)} bytes, sha256 ok)", flush=True)
    (target / "VERSION").write_text(f"{manifest['repo']}@{manifest['tag']} ({manifest['commit']})\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: fetch_defaults.py <defaults.json> <target-dir>")
    sys.exit(main(sys.argv[1], sys.argv[2]))
