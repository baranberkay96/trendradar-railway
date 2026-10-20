#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Run upstream's TrendRadar MCP server (streamable HTTP) for Railway.

Upstream starts it with `python -m mcp_server.server --transport http`, which
binds 0.0.0.0 without authentication. This runner serves the same FastMCP app
(`mcp_server.server.mcp`, tools initialised exactly like run_server()) and adds:
  - a required bearer token (MCP_TOKEN) on every request except /healthz,
  - GET /healthz -> 200 for Railway's healthcheck,
  - one dual-stack socket on [::]:$PORT (IPv4 healthcheck, IPv6/IPv4 private
    network). A plain uvicorn bind to "::" would be IPv6-only.
"""
from __future__ import annotations

import hmac
import os
import socket
import sys
from typing import Any, Awaitable, Callable

import uvicorn
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from mcp_server import server as upstream

MIN_TOKEN_LENGTH = 24
OPEN_PATHS = frozenset({"/healthz"})

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class BearerTokenMiddleware:
    """Reject HTTP requests without `Authorization: Bearer <MCP_TOKEN>`."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]], token: str) -> None:
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in OPEN_PATHS:
            await self.app(scope, receive, send)
            return
        supplied = b""
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                supplied = value
                break
        if not hmac.compare_digest(supplied, self.expected):
            response = PlainTextResponse(
                "missing or wrong bearer token\n",
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="trendradar-mcp"'},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


@upstream.mcp.custom_route("/healthz", methods=["GET"], include_in_schema=False)
async def healthz(_request: Request) -> Response:
    return PlainTextResponse("ok\n")


def dual_stack_socket(port: int) -> socket.socket:
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        address: tuple[Any, ...] = ("::", port)
    except OSError as error:
        print(f"[mcp] IPv6 unavailable ({error}); binding 0.0.0.0", file=sys.stderr, flush=True)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = ("0.0.0.0", port)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.set_inheritable(True)
    return sock


def main() -> int:
    token = os.environ.get("MCP_TOKEN", "").strip()
    if len(token) < MIN_TOKEN_LENGTH:
        print(f"[mcp] ERROR: MCP_TOKEN must be set (at least {MIN_TOKEN_LENGTH} characters); refusing to start without auth",
              file=sys.stderr, flush=True)
        return 1
    port = int(os.environ.get("PORT", "3333"))

    # Same initialisation as upstream's run_server(); project root = /app.
    upstream._get_tools(None)

    app = upstream.mcp.http_app(
        path="/mcp",
        middleware=[Middleware(BearerTokenMiddleware, token=token)],
    )
    config = uvicorn.Config(
        app,
        lifespan="on",
        log_level=os.environ.get("MCP_LOG_LEVEL", "info").lower(),
        timeout_graceful_shutdown=5,
        server_header=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    sock = dual_stack_socket(port)
    print(f"[mcp] TrendRadar MCP on port {port}: POST/GET /mcp (bearer token), GET /healthz", flush=True)
    uvicorn.Server(config).run(sockets=[sock])
    return 0


if __name__ == "__main__":
    sys.exit(main())
