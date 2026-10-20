#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Serve TrendRadar's HTML reports on the private network.

Replaces upstream's `manage.py start_webserver` (python -m http.server bound to
0.0.0.0 only) with the same static file serving, plus:
  - one dual-stack socket on [::]:$PORT (IPv4 for Railway's healthcheck, IPv6
    for the gateway on legacy private networks),
  - GET /healthz -> 200 "ok" without touching the disk,
  - Cache-Control: no-cache, so the latest report is never served stale,
  - quiet access logs (healthchecks are not logged).
There is no login here on purpose: the service has no public domain and the
gateway in front of it requires basic auth.
"""
from __future__ import annotations

import functools
import http.server
import os
import socket
import sys

REPORT_DIR = os.environ.get("REPORT_DIR", "/data/output")


class ReportHandler(http.server.SimpleHTTPRequestHandler):
    server_version = "TrendRadarReports"
    sys_version = ""

    def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
        if self.path.split("?", 1)[0] == "/healthz":
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 (stdlib signature)
        if self.path.startswith("/healthz"):
            return
        sys.stderr.write("[reports] %s %s\n" % (self.address_string(), format % args))


class DualStackServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def server_bind(self) -> None:
        if self.address_family == socket.AF_INET6:
            # Accept IPv4 too (IPv4-mapped addresses) on the same socket.
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def make_server(port: int) -> http.server.ThreadingHTTPServer:
    handler = functools.partial(ReportHandler, directory=REPORT_DIR)
    if socket.has_ipv6:
        try:
            DualStackServer.address_family = socket.AF_INET6
            return DualStackServer(("::", port), handler)
        except OSError as error:
            sys.stderr.write(f"[reports] IPv6 unavailable ({error}); falling back to 0.0.0.0\n")
    DualStackServer.address_family = socket.AF_INET
    return DualStackServer(("0.0.0.0", port), handler)


def main() -> int:
    port = int(os.environ.get("PORT", "8080"))
    os.makedirs(REPORT_DIR, exist_ok=True)
    server = make_server(port)
    host = "[::]" if server.address_family == socket.AF_INET6 else "0.0.0.0"
    sys.stderr.write(f"[reports] serving {REPORT_DIR} on {host}:{port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
