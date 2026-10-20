# Notice

## Upstream software

| Component | Source | License |
|---|---|---|
| TrendRadar crawler and MCP server | [sansan0/TrendRadar](https://github.com/sansan0/TrendRadar), tags `v6.11.0` and `mcp-v4.1.1`, commit `ceabb027fe9bbdafec59dbbfa12cb46c2ba256ce`; images `wantcat/trendradar:6.11.0` and `wantcat/trendradar-mcp:4.1.1` (Docker Hub) used unmodified as base images | GNU General Public License v3.0 (GPL-3.0) |
| TrendRadar default config files (`config/*.yaml`, `config/*.txt`, `config/ai_filter/*.txt`) | Same commit, downloaded at image build time and checked against the SHA-256 values in `services/*/defaults.json` | GPL-3.0 (part of the TrendRadar repository) |
| newsnow | [ourongxing/newsnow](https://github.com/ourongxing/newsnow), image `ghcr.io/ourongxing/newsnow:v0.0.41`, used unmodified | MIT |
| Caddy | `caddy:2.11.7-alpine` (Docker official image) | Apache-2.0 |
| supercronic | Bundled in the TrendRadar image (v0.2.39) | MIT |
| Python libraries used by the template scripts | Bundled in the TrendRadar images via upstream's `uv.lock`: FastMCP 2.12.5 (Apache-2.0), MCP SDK 1.16.0 (MIT), Uvicorn 0.37.0 (BSD-3-Clause), Starlette 0.48.0 (BSD-3-Clause), boto3 1.42.76 (Apache-2.0), PyYAML 6.0.3 (MIT) | as listed |

This repository does not contain TrendRadar's source code or its config files; the images and files are fetched from the sources above when Railway builds the services.

## Verified against

Checked on 2026-10-20 against the current stable tag, **v6.11.0** (tagged 2026-10-13; `master` was one commit ahead with README and image changes only):

- `docker/docker-compose.yml`, `docker/docker-compose-build.yml`, `docker/.env`, `docker/Dockerfile`, `docker/Dockerfile.mcp`, `docker/entrypoint.sh`, `docker/manage.py`
- `config/config.en.yaml`, `config/config.yaml`, `config/frequency_words*.txt`, `config/timeline*.yaml`, `config/ai_*.txt`, `config/ai_filter/*.txt`, `version`, `version_mcp`, `version_configs`
- `trendradar/core/loader.py` (environment overrides), `trendradar/storage/{manager,remote,local}.py`, `trendradar/report/generator.py`, `trendradar/crawler/fetcher.py`, `trendradar/ai/*.py`
- `mcp_server/server.py`, `mcp_server/tools/{storage_sync,system,article_reader}.py`, `mcp_server/services/{parser_service,data_service,cache_service}.py`
- `README-EN.md` (Docker deployment and MCP sections), `README-MCP-FAQ-EN.md`, `.github/workflows/docker.yml` (both images built from the same tag)
- newsnow v0.0.41: `Dockerfile`, `docker-compose.yml`, `example.env.server`, `nitro.config.ts`, `server/api/s/index.ts`, `server/api/latest.ts`, `server/middleware/auth.ts`, `server/database/cache.ts`, `shared/consts.ts`
- FastMCP v2.12.5 `server/server.py` and `server/http.py` (`custom_route`, `http_app`), Uvicorn 0.37.0 `server.py` (`run(sockets=...)`)

Tags and commits came from the GitHub API; the local reference copy matched the tag's blob SHAs for the files compared, and raw.githubusercontent.com served the same SHA-256 for the config files.

## GPL-3.0 notes

TrendRadar is licensed under the GPL-3.0. This template uses the official images unchanged and adds files next to them:

- `services/mcp/serve.py` imports and runs TrendRadar's `mcp_server` package, and the other scripts in `services/trendradar/` and `services/mcp/` start, configure or feed the GPL program. These files are offered under the **GPL-3.0** (`SPDX-License-Identifier: GPL-3.0-only`) so the whole build recipe is available under the same terms as the program. The gateway entrypoint carries the same identifier for consistency.
- No TrendRadar file is modified. The deployed program is upstream's release; the corresponding source is the upstream tag above plus this repository.

What this means for operators (practical guidance, not legal advice; get professional advice for your situation):

- Running the template for yourself or your team does not by itself create obligations to publish anything. The GPL-3.0 (unlike the AGPL) does not require offering source to network users.
- If you distribute images or modified versions of TrendRadar or of these scripts, you must do so under the GPL-3.0 and provide the corresponding source.
- Keep upstream's license and attribution intact; the HTML reports keep TrendRadar's own project link.

## Written for this template

Everything in `services/` and the documents (`TEMPLATE.md`, `template.json`, `README.md`, this file) were written for this template, using upstream's documentation and source as reference:

- `services/trendradar/start.sh`: follows the run model of upstream's `docker/entrypoint.sh` (cron character check, `supercronic -test`, boot crawl, `exec supercronic -passthrough-logs`); no code was copied.
- `services/trendradar/report_server.py`: replaces `manage.py start_webserver` with an equivalent static server plus health endpoint.
- `services/mcp/sync_bucket.py`: mirrors upstream's remote storage layout (`news/` and `rss/` keys, virtual-hosted S3 addressing) for the MCP server's local layout.
- `services/mcp/serve.py`, `services/*/seed_config.sh`, `services/*/fetch_defaults.py`, `services/*/defaults.json`, `services/trendradar/prune_reports.py`, `services/gateway/*`, all Dockerfiles.

## Reference only (not copied)

- Railway marketplace template "TrendRadar — Automated News Monitoring & Daily Intelligence" (`trendradar-automated-news-monitoring-and`) and the Caddy gateway repository it uses: read for ideas (Bucket as shared storage, MCP image). No license; nothing copied.
- Railway marketplace template "TrendRadar Zero Config News Monitor" (`trendradar-zero-config-news-monitor`): read for ideas (seeded English defaults, private report server, basic-auth gateway). No license; nothing copied.
