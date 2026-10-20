#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Delete dated HTML/TXT report folders older than REPORT_RETENTION_DAYS.

TrendRadar writes a snapshot per run to output/html/YYYY-MM-DD/. With the
remote (Bucket) storage backend upstream's retention only prunes the Bucket,
so the volume would fill up over time. This job (run daily by supercronic)
keeps the last N days. 0 or an empty value keeps everything. The undated
folders (html/latest) and index.html are never touched.
"""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import re
import shutil
import sys

OUTPUT_DIR = pathlib.Path(os.environ.get("REPORT_DIR", "/data/output"))
DATED = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def retention_days() -> int:
    raw = os.environ.get("REPORT_RETENTION_DAYS", "30").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        print(f"[prune] REPORT_RETENTION_DAYS={raw!r} is not a number; keeping everything", file=sys.stderr)
        return 0


def main() -> int:
    days = retention_days()
    if days == 0:
        print("[prune] retention disabled (REPORT_RETENTION_DAYS=0)")
        return 0
    cutoff = dt.date.today() - dt.timedelta(days=days)
    removed = 0
    for kind in ("html", "txt"):
        base = OUTPUT_DIR / kind
        if not base.is_dir():
            continue
        for folder in base.iterdir():
            match = DATED.match(folder.name)
            if not folder.is_dir() or not match:
                continue
            try:
                folder_date = dt.date(*(int(part) for part in match.groups()))
            except ValueError:
                continue
            if folder_date < cutoff:
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
                print(f"[prune] removed {kind}/{folder.name}")
    print(f"[prune] kept the last {days} days of reports, removed {removed} folder(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
