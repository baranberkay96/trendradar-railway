# TrendRadar MCP server for Railway (community template).
#
# Base: the official MCP image, unmodified (Python 3.12, MCP server 4.1.1,
# built from the same upstream commit as wantcat/trendradar:6.11.0). This
# layer adds the Railway runner (bearer token, /healthz, dual-stack socket),
# the Bucket sync job and the default config files of the same release,
# downloaded at build time and checked against SHA-256 (defaults.json).
FROM wantcat/trendradar-mcp:4.1.1

COPY defaults.json fetch_defaults.py seed_config.sh start.sh sync_bucket.py serve.py /opt/railway/

RUN set -eux; \
    chmod 0755 /opt/railway/*.sh /opt/railway/*.py; \
    sh -n /opt/railway/start.sh; \
    sh -n /opt/railway/seed_config.sh; \
    python -m py_compile /opt/railway/serve.py /opt/railway/sync_bucket.py /opt/railway/fetch_defaults.py; \
    python /opt/railway/fetch_defaults.py /opt/railway/defaults.json /opt/railway/defaults; \
    command -v timeout; \
    cd /app && python -c "import boto3, uvicorn, starlette.middleware; from fastmcp import FastMCP; assert hasattr(FastMCP, 'custom_route') and hasattr(FastMCP, 'http_app'); import mcp_server.server"

ENV PORT=3333 \
    PYTHONPATH=/app \
    MCP_DATA_DIR=/app/output \
    DOCKER_CONTAINER=true

EXPOSE 3333

CMD ["/opt/railway/start.sh"]
