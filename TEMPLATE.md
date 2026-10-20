# TrendRadar v6 AI News and Trend Monitor — Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **TrendRadar v6 AI News and Trend Monitor** (`v6` = TrendRadar major version; upstream publishes git tags but no GitHub releases, the pinned tag is `v6.11.0`) |
| Description | Track trends on Chinese and global platforms with AI summaries and alerts. (74 chars) |
| Category | Automation |
| Tags | trendradar, news, trends, monitoring, rss, alerts, ai, mcp, newsnow |
| Icon | `https://cdn.jsdelivr.net/gh/sansan0/TrendRadar@v6.11.0/_image/banner.webp` (upstream's own banner; HTTP 200, image/webp, checked 2026-10-20). TrendRadar has no square logo, so this is a wide wordmark. |
| User input at deploy | **None.** Passwords and the MCP token are generated. LLM key and notification webhooks are optional. |
| Repo for built services | `baranberkay96/trendradar-railway` (`/services/gateway`, `/services/trendradar`, `/services/mcp`) |

**Listing wording check.** The given description was "Track trending topics across platforms and get AI summaries and alerts." It was changed because the default hot lists are 11 Chinese platforms (Toutiao, Baidu, WallStreetCN, The Paper, Bilibili, CLS, iFeng, Tieba, Weibo, Douyin, Zhihu), while the "global" part comes from RSS feeds (Hacker News and Yahoo Finance by default, any feed can be added) and optional newsnow sources such as Hacker News, GitHub Trending and Product Hunt. "AI summaries" need an LLM key (optional input); "alerts" are delivered through the user's own webhook channels. The new wording says this without overpromising.

## Base market templates

| Code | Name | Stats (2026-10-20) | Verdict |
|---|---|---|---|
| `trendradar-automated-news-monitoring-and` | "TrendRadar — Automated News Monitoring & Daily Intelligence" | 10 projects, 3 active | Ideas only. Its 3 active projects suggest the remote (Bucket) storage path works on Railway; it also includes the MCP image. Problems: `wantcat/trendradar:5.0` and `trendradar-mcp:3.1` (old), config downloaded from `master` at every boot, MCP service starts with an empty `output/` and only gets data when an agent calls upstream's `sync_from_remote` tool, which copies news (not RSS) and never refreshes a date it already has, so today's data goes stale, no healthchecks, report web server disabled, S3 browser and two gateways from a third-party repo, `secret(12)` passwords, env vars that 6.11 does not read (`ENABLE_CRAWLER`, `REPORT_MODE`, `DISPLAY_MODE`). |
| `trendradar-zero-config-news-monitor` | "TrendRadar Zero Config News Monitor" | 2 projects, 0 active | **Structural base** for the crawler: one cron container with config and output on a volume, seeded English defaults, a private report server and a Caddy basic-auth gateway. Kept those ideas. Fixed: image 6.10.0 → 6.11.0, config pinned by commit but downloaded at every first boot (now baked into the image with SHA-256 checks), upstream's 0.0.0.0-only viewer left running on a second port, AI flags off even after a key is added, no MCP, no history outside the volume, report snapshots never pruned, all logic in base64 start commands. |

No file or text was copied from either market template (both have no license). Everything under `services/` was written for this template (see NOTICE.md).

## Pinned versions

| Component | Source | Version | Date | Checked |
|---|---|---|---|---|
| TrendRadar crawler | `wantcat/trendradar:6.11.0` (index `sha256:3effcb5c…df80b`, amd64 `sha256:da2e26b6…2f536`) | 6.11.0 | 2026-10-13 | 2026-10-20 (Docker Hub; same digest as `6.11` and `latest`) |
| TrendRadar MCP server | `wantcat/trendradar-mcp:4.1.1` (index `sha256:12cdc3dc…bdabf`, amd64 `sha256:ecf041f5…5b369e`) | 4.1.1 | 2026-10-13 | 2026-10-20 |
| Upstream source / default config | `sansan0/TrendRadar` tags `v6.11.0` and `mcp-v4.1.1` → commit `ceabb027fe9bbdafec59dbbfa12cb46c2ba256ce` | config schema 2.4.0 | 2026-10-13 | 2026-10-20 (`master` is 1 commit ahead: README and an image only) |
| newsnow (hot-list API) | `ghcr.io/ourongxing/newsnow:v0.0.41` (index `sha256:98b62bd9…f55a`, amd64 + arm64) | 0.0.41 | 2026-06-26 | 2026-10-20. Releases v0.0.42/v0.0.43 exist but their images were never pushed (GHCR `latest` = v0.0.41). The later changes touch sources TrendRadar does not use by default. |
| Gateway | `caddy:2.11.7-alpine` | 2.11.7 | image 2026-10-06 | 2026-10-20 |
| Python deps (inside the images) | upstream `uv.lock`: fastmcp 2.12.5, mcp 1.16.0, uvicorn 0.37.0, starlette 0.48.0, boto3 1.42.76, litellm 1.82.6 | — | — | 2026-10-20 |

**Upgrade path.** Change the `FROM` tags in `services/trendradar/Dockerfile` and `services/mcp/Dockerfile` (they must come from the same upstream commit), then update `tag`, `commit` and every `sha256` in `services/*/defaults.json` (both copies are identical) to that commit; the build fails if a hash does not match. Existing installs keep their config on the volume: set `CONFIG_RESEED=true` once if the new release changed the config schema (upstream logs a config version warning), then set it back to `false`. Rename the listing if the major version changes.

## Architecture

```
Internet --HTTPS--> gateway (Caddy, only public domain, :8080)
                     |- /gateway-health     -> 200
                     |- /mcp, /mcp/*        -> trendradar-mcp:3333 (bearer token checked there)
                     '- everything else     -> basic auth -> trendradar:8080 (report server)

trendradar (volume /data)                          newsnow (private :4444)
  supercronic: */30 crawl  ---- /api/s?id=... ---->  scrapes Weibo, Zhihu, Douyin, ...
               03:17 prune old HTML                  (10-minute cache per source)
  report server [::]:8080 -> /data/output
  writes: /data/output/html/... (reports)
          Bucket news/YYYY-MM-DD.db, rss/YYYY-MM-DD.db (SQLite history, upstream remote backend)
  pushes: Telegram / Slack / ntfy / webhooks / ... (user inputs)
                 |
             Bucket (Railway, S3) ---- every 5 min, changed files only ----> trendradar-mcp
                                                                   /app/output/{news,rss}/ -> MCP tools
```

### Deviations from upstream `docker/docker-compose.yml` (v6.11.0) and why

| Upstream | Here | Why |
|---|---|---|
| `trendradar` and `trendradar-mcp` share `../config` and `../output` bind mounts | Crawler stores SQLite history in a Railway Bucket (upstream's `STORAGE_BACKEND=remote`); MCP mirrors it with `sync_bucket.py`; config is seeded identically in both | Railway volumes cannot be shared between services. Upstream's own split deployment (crawler in the cloud, MCP elsewhere) uses remote storage too. |
| Config files bind-mounted from the host | Defaults of the same commit baked into each image (SHA-256 checked) and copied to `/data/config` on first boot; whole-file overrides through `CONFIG_YAML`, `FREQUENCY_WORDS`, `AI_INTERESTS` | The image ships no config and its entrypoint exits without one. Railway has no host files. |
| `python manage.py start_webserver` (`http.server` on 0.0.0.0) | `report_server.py`: same static serving, dual-stack `[::]`, `/healthz`, no-cache headers | Healthcheck, IPv6 private network (legacy environments), fresh reports |
| Hot lists from the public `newsnow.busiyi.world` | Private `newsnow` service, `PLATFORMS_API_URL` points at it | See "Data sources". One variable switches back to the public instance. |
| MCP on `0.0.0.0:3333` without auth (compose binds it to 127.0.0.1) | `serve.py` runs the same FastMCP app with a required bearer token, `/healthz` and a dual-stack socket; public only through the gateway | Upstream's README tells remote users to add a reverse proxy and auth themselves. |
| `TZ=Asia/Shanghai` | `TZ=UTC`, `TIMEZONE=${{TZ}}` | Neutral default for a global audience; one variable to change |
| Entrypoint runs the boot crawl, then supercronic | Same order, plus a wait (≤ 300 s) for newsnow before the boot crawl and a daily prune job | Services start in parallel (Rule 8.5); remote storage leaves HTML snapshots unpruned |
| AI analysis and translation `enabled: true` in the English config | Empty `AI_*_ENABLED` = on only when `AI_API_KEY` is set | Without a key every run printed an "API key not configured" block |

### Template code around upstream (no upstream file is modified)

| File | Purpose |
|---|---|
| `services/trendradar/start.sh` | Seeds config, checks storage settings, AI switches, placeholder page, report server loop, crontab (upstream's cron character check + `supercronic -test`), newsnow wait, boot crawl, `exec supercronic` |
| `services/trendradar/report_server.py`, `prune_reports.py` | Report server and HTML retention (`REPORT_RETENTION_DAYS`, default 30) |
| `services/*/seed_config.sh`, `fetch_defaults.py`, `defaults.json` | Build-time download + verification of the default config; boot-time seeding and overrides (identical copies in both services) |
| `services/mcp/serve.py` | Bearer-token middleware, `/healthz`, dual-stack uvicorn socket around `mcp_server.server.mcp` |
| `services/mcp/sync_bucket.py` | ETag-based mirror of `news/` and `rss/` databases from the Bucket, atomic replace, window of `MCP_SYNC_DAYS` |
| `services/mcp/start.sh` | Seeds config, initial sync (≤ 180 s), background sync loop, `exec serve.py` |
| `services/gateway/*` | Caddy routes, bcrypt login, MCP pass-through or 404 when the MCP service is removed |

## Security model

- **One public domain** (gateway). trendradar, trendradar-mcp and newsnow have no public domain.
- **Report pages** need HTTP basic auth: `REPORTS_USERNAME` (admin) and `REPORTS_PASSWORD` (24 random characters from `secret()`, bcrypt-hashed in the container, minimum 12 characters enforced). `REPORTS_PUBLIC=true` removes the login on purpose only.
- **MCP** needs `Authorization: Bearer {MCP_TOKEN}` (48 random characters). The check runs inside the MCP service, so it also holds if someone adds a domain to that service directly. The server refuses to start without a token of at least 24 characters. MCP clients cannot answer a basic-auth prompt, which is why `/mcp` skips the gateway login.
- **No LLM-spending endpoint is exposed.** AI analysis, translation and the AI filter run only inside scheduled crawls on the trendradar service. The MCP server makes no LLM calls (it has no `AI_API_KEY`); its `read_article` tool calls `r.jina.ai`, and `send_notification` can post to the channels you configured (it receives them by reference so the agent can push summaries).
- Webhook URLs and tokens are optional user inputs. The report server serves only `/data/output` (path traversal returns 404, tested).
- newsnow runs with login disabled (no `JWT_SECRET`/`G_CLIENT_*`), so only `/api/s`, `/api/proxy` and `/api/latest` answer. It is reachable only on the private network.

## Services

### gateway
- Repo build `/services/gateway` (`caddy:2.11.7-alpine`), public domain on 8080, healthcheck `/gateway-health` (120 s), ON_FAILURE × 10.
- Variables: `PORT`, `REPORTS_USERNAME`, `REPORTS_PASSWORD`, `REPORTS_PUBLIC`, `REPORTS_UPSTREAM` (`${{trendradar.RAILWAY_PRIVATE_DOMAIN}}:${{trendradar.PORT}}`), `MCP_UPSTREAM` (same for trendradar-mcp; empty or `:` → `/mcp` 404), `MCP_URL` (informational).

### trendradar
- Repo build `/services/trendradar` (`FROM wantcat/trendradar:6.11.0`), volume `/data` (`config/`, `output/`), healthcheck `/healthz` (300 s), restart ALWAYS (no max retries).
- Runs the boot crawl, then supercronic: `CRON_SCHEDULE` (default `*/30 * * * *`) and the 03:17 prune job.
- Storage: `STORAGE_BACKEND=remote` + `S3_*` from the Bucket. If any `S3_*` is empty the script falls back to local SQLite on the volume and says so.
- Key variables: `TZ`/`TIMEZONE`, `CRON_SCHEDULE`, `IMMEDIATE_RUN`, `REPORT_RETENTION_DAYS`, `CONFIG_LANGUAGE` (en/zh), `CONFIG_RESEED`, `CONFIG_YAML`, `FREQUENCY_WORDS`, `AI_INTERESTS`, `PLATFORMS_API_URL`, `AI_API_KEY`, `AI_MODEL`, `AI_API_BASE`, `AI_ANALYSIS_ENABLED`, `AI_TRANSLATION_ENABLED`, `AI_TRANSLATION_LANGUAGE`, `AI_FILTER_ENABLED`, `SCHEDULE_ENABLED`, `SCHEDULE_PRESET`, and the 18 channel variables (Telegram, Slack, generic webhook, ntfy, Bark, Feishu, DingTalk, WeCom, email).

### trendradar-mcp (optional)
- Repo build `/services/mcp` (`FROM wantcat/trendradar-mcp:4.1.1`), port 3333, healthcheck `/healthz` (300 s), restart ALWAYS, no volume (its data is a cache of the Bucket, rebuilt at boot).
- 27 upstream tools and 4 resources (news/RSS queries, search, trend and sentiment analysis, summaries, storage status, `trigger_crawl`, `read_article`, `send_notification`).
- Config, keywords, timezone, hot-list API and channels are references to the trendradar service, so both see the same setup. Edits made directly to files on the trendradar volume (e.g. over `railway ssh`) are not seen by MCP; use the variables.
- **To deploy without MCP:** delete the service in the composer before deploying (or later). The gateway then answers `/mcp` with 404; the Bucket stays useful as durable history.

### newsnow
- Image `ghcr.io/ourongxing/newsnow:v0.0.41`, private port 4444, `HOST=::` (Node dual stack), healthcheck `/api/latest` (120 s), ON_FAILURE × 10, no volume (its SQLite cache in `.data/` is rebuilt on restart).

### Bucket
- Railway Bucket `Bucket`: `news/YYYY-MM-DD.db` and `rss/YYYY-MM-DD.db`, a few MB per day. Upstream's `REMOTE_RETENTION_DAYS` (not set; 0 = keep forever) can be added to the trendradar service to prune it.

## Data sources and third-party services

- **Hot lists depend on newsnow** (MIT, `ourongxing/newsnow`), an aggregation API that scrapes each platform. TrendRadar calls `{PLATFORMS_API_URL}?id={platform}&latest`. Upstream's default is the public, donation-funded instance `newsnow.busiyi.world` behind Cloudflare; upstream issues report 403s from Cloudflare, rate limits and 500s for some sources, and anonymous calls there get cached data. This template runs newsnow privately instead: fresh data within newsnow's 10-minute source cache, no shared rate limit, no third-party API in the path. Trade-off: the scrapers now run from Railway's IP ranges; a Chinese site that blocks datacenter IPs would show as a failed platform in the report. Fallback: set `PLATFORMS_API_URL=https://newsnow.busiyi.world/api/s` on trendradar (and delete newsnow if you like).
- **RSS** feeds are fetched directly by the crawler (default: Hacker News via hnrss.org, Yahoo Finance).
- **AI**: any LiteLLM provider (`AI_MODEL` like `deepseek/deepseek-v4-flash`, the config default, `openai/gpt-4o`, `gemini/gemini-2.5-flash`) or an OpenAI-compatible endpoint via `AI_API_BASE` with an `openai/` model prefix.
- **Notifications**: Telegram, Slack, ntfy, Bark, generic webhook (Discord, Matrix, n8n, ...), Feishu, DingTalk, WeCom, email. Email needs outbound SMTP, which Railway allows only on Pro (Rule 8.11); the README steers users to webhook channels.
- **Version check**: each run reads three small version files from raw.githubusercontent.com (upstream default, `advanced.version_check_url`); failures only log a warning.

## Improvements over market templates

1. **Current release, pinned:** 6.11.0 + MCP 4.1.1 from the same commit; config defaults of that commit verified by SHA-256 at build time (market: 5.0/3.1 with `master` config, or 6.10.0 with a boot-time download).
2. **MCP actually has data:** ETag-based Bucket mirror refreshes today's database every 5 minutes (market: MCP container whose data depends on manual `sync_from_remote` calls and never refreshes today).
3. **MCP secured and reachable:** bearer token generated at deploy, `/mcp` on the same public domain as the reports (market: separate third-party gateway with a 12-character password, or no MCP).
4. **Private newsnow** instead of the rate-limited public instance, with one-variable fallback.
5. **Healthchecks with `PORT` on every listening service** (`/gateway-health`, `/healthz` ×2, `/api/latest`); dual-stack listeners for the report server, MCP and newsnow.
6. **AI that follows the key:** add `AI_API_KEY` and AI analysis/translation turn on; remove it and they stop (no error blocks in reports).
7. **Boot crawl waits for newsnow** so the first report is complete; services can start in any order.
8. **Reports don't fill the volume:** daily pruning of dated snapshots (`REPORT_RETENTION_DAYS`).
9. **Durable history** in the Bucket, independent of the volume.
10. **Readable scripts in a repo** instead of base64 start commands; every script is syntax-checked during the image build.
11. **Config workflow:** language switch (en/zh), whole-file overrides, `CONFIG_RESEED` with backups, YAML validity warning, unresolved-reference guard.
12. **No useless services:** the market S3 browser and a second gateway are dropped; the Railway dashboard has a bucket file browser.

## Scaling

- trendradar: keep **one** replica (cron + volume). More platforms or feeds only lengthen each run; give it more memory if you add many feeds or the AI filter.
- trendradar-mcp: stateless apart from its Bucket cache; one replica is enough for personal and team use. Replicas would each mirror the Bucket.
- newsnow: one replica; its cache is per instance.
- Crawl frequency: `CRON_SCHEDULE`. Going below 10 minutes gains nothing because newsnow caches each source for its refresh interval.

## Resource estimate

Prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month, Bucket $0.015/GB-month, egress $0.05/GB. **Not measured** (no container was run); based on the processes involved (Python with litellm imported during crawls, FastMCP/uvicorn, Node, Caddy).

| Service | Idle RAM | Typical RAM | Idle vCPU | Typical vCPU | Storage |
|---|---|---|---|---|---|
| gateway | 20 MB | 30 MB | 0.002 | 0.01 | — |
| trendradar (time-averaged; ~250 MB for 1–3 min per crawl) | 60 MB | 150 MB | 0.01 | 0.05 | volume 0.2–0.5 GB |
| trendradar-mcp (server + sync loop) | 150 MB | 220 MB | 0.005 | 0.03 | — |
| newsnow | 90 MB | 130 MB | 0.005 | 0.02 | — |
| Bucket | — | — | — | — | ~0.1 GB/month growth |
| **Total** | **≈ 0.32 GB** | **≈ 0.53 GB** | **≈ 0.02** | **≈ 0.11** | |

- **Idle** (default schedule, no AI): 0.32 × $10 + 0.02 × $20 + volume ≈ **$4/month**.
- **Typical** (AI analysis on, several channels, MCP in use): 0.53 × $10 + 0.11 × $20 + volume/Bucket/egress ≈ **$8/month**. Uploading the day's databases after each crawl is service egress (a few GB per month, well under $1).
- LLM usage is billed by your provider (one analysis per crawl when enabled, plus translation batches).
- **Minimum plan:** Trial runs it (each service < 1 GB, volume < 0.5 GB), but its credit won't cover a month; **Hobby** recommended. No Pro features needed unless you want email delivery.

## Static verification (2026-10-20, no Docker)

- Upstream copy in `_upstream/sansan0__TrendRadar` matches tag v6.11.0 (git blob SHAs of `docker/*`, `config/*`, `mcp_server/server.py`, `mcp_server/tools/storage_sync.py`, `trendradar/storage/remote.py`, `trendradar/crawler/fetcher.py`, `version` compared with `gh api …?ref=v6.11.0`); both tags point to commit `ceabb02`.
- Image configs read from the registry API: `wantcat/trendradar:6.11.0` (ENTRYPOINT `/entrypoint.sh`, WORKDIR `/app`, Python 3.12.15, supercronic v0.2.39, root), `wantcat/trendradar-mcp:4.1.1` (CMD `python -m mcp_server.server --transport http --host 0.0.0.0`, port 3333). Tags confirmed for caddy 2.11.7-alpine and newsnow v0.0.41 (amd64 present).
- `dash -n` and `bash -n` on every shell script; `py_compile` on every Python file; template.json parses, converts with `_tools/to_serialized.py` (4 services, 1 bucket, 1 volume), every reference resolves, every variable has a description; `ship.py review` reports no problems.
- **Executed locally** (scratch venv with upstream's locked versions: fastmcp 2.12.5, mcp 1.16.0, uvicorn 0.37.0, starlette 0.48.0, boto3 1.42.76):
  - `fetch_defaults.py` against GitHub: 12 files, all SHA-256 ok.
  - `seed_config.sh` under dash and bash --posix: first boot, edits kept, overrides, unresolved `${{...}}` ignored, invalid YAML warned, `CONFIG_RESEED` backup, bad language fallback.
  - `start.sh` with fake supercronic and a stub crawler: storage fallback, AI switches, crontab, invalid cron rejected (exit 1), newsnow wait success and timeout.
  - `report_server.py`: `/healthz` over IPv4 and IPv6 on one socket, listing, no-cache headers, traversal 404. `prune_reports.py`: retention 30/0/invalid.
  - `sync_bucket.py` against a stub S3 client: window, ETag skip, refresh of a changed file, atomic replace, local pruning, no-bucket exit.
  - `serve.py` with real FastMCP and a stub `mcp_server.server`: refuses a short token, `/healthz` 200 on IPv4 and IPv6, 401 without/with wrong token, MCP `initialize` + `tools/call` 200 with the token.
  - Gateway with the official Caddy 2.11.7 binary (checksum-verified): health 200, reports 401 → 200 with login, `/mcp` 401 without token and with basic-auth only, 200 with bearer, 404 when the MCP upstream is empty, public mode.

## Verification checklist (first deploy)

1. All three builds succeed (each Dockerfile downloads 12 config files and runs import checks).
2. Healthy: gateway `/gateway-health`, trendradar `/healthz`, trendradar-mcp `/healthz`, newsnow `/api/latest`.
3. trendradar logs: `newsnow ready`, `storage: SQLite history in bucket …`, the crawl lists `获取 weibo 成功（最新数据）`-style lines for the 11 platforms (count the failures), then `starting supercronic`.
4. Open `https://{gateway-domain}`, log in with `admin` + `REPORTS_PASSWORD`: the placeholder page is replaced by the first report within a few minutes; `/html/` lists dated folders.
5. Bucket file browser shows `news/{today}.db` and `rss/{today}.db`.
6. trendradar-mcp logs: `downloaded 2` on the initial sync, later refreshes after each crawl.
7. MCP: `POST https://{gateway-domain}/mcp` with `Authorization: Bearer {MCP_TOKEN}` (e.g. `npx @modelcontextprotocol/inspector`, or `claude mcp add --transport http trendradar https://{gateway-domain}/mcp --header "Authorization: Bearer {MCP_TOKEN}"`); `get_latest_news` returns today's items. Without the header: 401.
8. Add `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (or `NTFY_TOPIC`), redeploy trendradar: next crawl pushes matches.
9. Add `AI_API_KEY` (+ `AI_MODEL`): logs show `AI analysis=true`, the report gets an AI section.
10. Redeploy trendradar: config edits and old reports persist (volume), history persists (Bucket).
11. Next day after 03:17 (TZ): `[prune]` line in logs.

## Open questions

- Whether all 11 default Chinese platforms scrape successfully from Railway's IP ranges through the self-hosted newsnow (tested from a European network only: Zhihu, Bilibili, Tieba, Baidu, Toutiao endpoints answered 200; Weibo needs newsnow's cookie). If several fail, switch `PLATFORMS_API_URL` to the public instance.
- Supercronic evaluates `CRON_SCHEDULE` in `TZ`; this relies on tzdata in the python slim base (expected, not checked inside the image).
- Railway Bucket compatibility of upstream's remote backend (virtual-hosted addressing, `put_object` with `ContentLength`) is inferred from the older market template that uses the same path with 3 active projects, not tested here.
- Whether optional variables left empty on trendradar resolve to empty strings on trendradar-mcp references (expected; `seed_config.sh` ignores an unresolved `${{…}}` literal anyway).
- Exact memory of each service on Railway (estimates above are not measured).
- The listing icon is a wide wordmark; check how the marketplace card crops it.
