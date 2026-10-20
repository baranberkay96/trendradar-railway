# TrendRadar gateway for Railway (community template): Caddy with a basic-auth
# login in front of the report pages and a pass-through route for the MCP
# server. Routing is in the Caddyfile; the login and MCP blocks are written at
# start by entrypoint.sh.
FROM caddy:2.11.7-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /opt/railway/entrypoint.sh
RUN chmod 0755 /opt/railway/entrypoint.sh && sh -n /opt/railway/entrypoint.sh

ENV PORT=8080
EXPOSE 8080

CMD ["/opt/railway/entrypoint.sh"]
