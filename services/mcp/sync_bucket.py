#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Mirror TrendRadar's SQLite history from the Railway Bucket to the MCP server.

Upstream runs the crawler and the MCP server on one shared folder. Railway
volumes cannot be shared, so the crawler stores its daily SQLite files in the
Bucket (upstream's remote storage backend: news/YYYY-MM-DD.db and
rss/YYYY-MM-DD.db) and this job copies them to /app/output/{news,rss}/, the
layout the MCP server reads.

Unlike upstream's sync_from_remote tool it also refreshes files that changed
(today's database changes after every crawl), compares ETags so unchanged
files are not downloaded again, replaces files atomically and drops local
files that fell out of the window.

Usage: sync_bucket.py --once | --loop
Env:   S3_ENDPOINT_URL S3_BUCKET_NAME S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY
       S3_REGION, MCP_SYNC_DAYS (default 30), MCP_SYNC_INTERVAL (s, default 300)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
from typing import Any

import boto3
from botocore.config import Config

OUTPUT_DIR = pathlib.Path(os.environ.get("MCP_DATA_DIR", "/app/output"))
STATE_FILE = OUTPUT_DIR / ".bucket-sync.json"
REMOTE_KEY = re.compile(r"^(news|rss)/(\d{4}-\d{2}-\d{2})\.db$")
LOCAL_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.db$")
KINDS = ("news", "rss")
CHUNK_BYTES = 1024 * 1024


def log(message: str) -> None:
    print(f"[bucket-sync] {message}", flush=True)


def env_int(name: str, default: int, minimum: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        log(f"{name}={raw!r} is not a number; using {default}")
        return default


def bucket_settings() -> dict[str, str] | None:
    settings = {
        "endpoint": os.environ.get("S3_ENDPOINT_URL", "").strip(),
        "bucket": os.environ.get("S3_BUCKET_NAME", "").strip(),
        "key_id": os.environ.get("S3_ACCESS_KEY_ID", "").strip(),
        "secret": os.environ.get("S3_SECRET_ACCESS_KEY", "").strip(),
        "region": os.environ.get("S3_REGION", "").strip(),
    }
    required = ("endpoint", "bucket", "key_id", "secret")
    return settings if all(settings[name] for name in required) else None


def make_client(settings: dict[str, str]) -> Any:
    # Same addressing as upstream's RemoteStorageBackend: Railway Buckets are
    # virtual-hosted style.
    kwargs: dict[str, Any] = {
        "endpoint_url": settings["endpoint"],
        "aws_access_key_id": settings["key_id"],
        "aws_secret_access_key": settings["secret"],
        "config": Config(
            s3={"addressing_style": "virtual"},
            signature_version="s3v4",
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10,
            read_timeout=60,
        ),
    }
    if settings["region"]:
        kwargs["region_name"] = settings["region"]
    return boto3.client("s3", **kwargs)


def load_state() -> dict[str, str]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict[str, str]) -> None:
    tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=0, sort_keys=True), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def list_remote(client: Any, bucket: str, cutoff: dt.date) -> dict[str, str]:
    """Return {key: etag} for news/rss databases on or after the cutoff date."""
    remote: dict[str, str] = {}
    paginator = client.get_paginator("list_objects_v2")
    for kind in KINDS:
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{kind}/"):
            for obj in page.get("Contents", []):
                match = REMOTE_KEY.match(obj["Key"])
                if match and dt.date.fromisoformat(match.group(2)) >= cutoff:
                    remote[obj["Key"]] = obj.get("ETag", "")
    return remote


def download(client: Any, bucket: str, key: str, target: pathlib.Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    response = client.get_object(Bucket=bucket, Key=key)
    with open(partial, "wb") as handle:
        for chunk in response["Body"].iter_chunks(chunk_size=CHUNK_BYTES):
            handle.write(chunk)
    # Atomic swap: open SQLite readers keep the old file until they close it.
    os.replace(partial, target)


def prune_local(cutoff: dt.date, state: dict[str, str]) -> int:
    removed = 0
    for kind in KINDS:
        folder = OUTPUT_DIR / kind
        if not folder.is_dir():
            continue
        for path in folder.glob("*.db"):
            match = LOCAL_NAME.match(path.name)
            if match and dt.date.fromisoformat(match.group(1)) < cutoff:
                path.unlink(missing_ok=True)
                state.pop(f"{kind}/{path.name}", None)
                removed += 1
    return removed


def sync_once(client: Any, bucket: str, days: int) -> None:
    # One extra day so a timezone difference never hides "today".
    cutoff = dt.date.today() - dt.timedelta(days=days)
    state = load_state()
    remote = list_remote(client, bucket, cutoff)
    fetched = 0
    for key, etag in sorted(remote.items()):
        target = OUTPUT_DIR / key
        if target.exists() and state.get(key) == etag:
            continue
        download(client, bucket, key, target)
        state[key] = etag
        fetched += 1
    removed = prune_local(cutoff, state)
    save_state(state)
    if fetched or removed:
        log(f"{len(remote)} database(s) in the last {days} days; downloaded {fetched}, removed {removed}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    settings = bucket_settings()
    if settings is None:
        log("S3_* variables are not set; nothing to sync (the MCP server only sees data saved by trigger_crawl)")
        return 0
    days = env_int("MCP_SYNC_DAYS", 30, 1)
    interval = env_int("MCP_SYNC_INTERVAL", 300, 30)
    for kind in KINDS:
        (OUTPUT_DIR / kind).mkdir(parents=True, exist_ok=True)
    client = make_client(settings)

    if args.once:
        sync_once(client, settings["bucket"], days)
        log(f"initial sync from bucket {settings['bucket']} done")
        return 0

    log(f"syncing bucket {settings['bucket']} every {interval}s (last {days} days)")
    while True:
        try:
            sync_once(client, settings["bucket"], days)
        except Exception as error:  # keep the loop alive; the next cycle retries
            log(f"sync failed: {error}")
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
