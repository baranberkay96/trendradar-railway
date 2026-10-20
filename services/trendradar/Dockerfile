# TrendRadar crawler for Railway (community template).
#
# Base: the official image, unmodified (Python 3.12, TrendRadar 6.11.0,
# supercronic). This layer only adds the Railway start scripts and the
# upstream default config files of the same release, downloaded at build time
# from the pinned commit and checked against SHA-256 (defaults.json).
FROM wantcat/trendradar:6.11.0

COPY defaults.json fetch_defaults.py seed_config.sh start.sh report_server.py prune_reports.py /opt/railway/

RUN set -eux; \
    chmod 0755 /opt/railway/*.sh /opt/railway/*.py; \
    sh -n /opt/railway/start.sh; \
    sh -n /opt/railway/seed_config.sh; \
    python -m py_compile /opt/railway/report_server.py /opt/railway/prune_reports.py /opt/railway/fetch_defaults.py; \
    python /opt/railway/fetch_defaults.py /opt/railway/defaults.json /opt/railway/defaults; \
    test -x /usr/local/bin/supercronic; \
    python -c "import trendradar, yaml, boto3"; \
    rm -rf /app/config /app/output; \
    ln -s /data/config /app/config; \
    ln -s /data/output /app/output

# DOCKER_CONTAINER: upstream then logs report paths instead of opening a browser.
ENV PORT=8080 \
    DATA_DIR=/data \
    DOCKER_CONTAINER=true

EXPOSE 8080

ENTRYPOINT ["/opt/railway/start.sh"]
CMD []
