# Deploy and Host TrendRadar with Railway

TrendRadar is an open-source trend monitor. On a schedule it collects trending lists from Chinese platforms such as Weibo, Zhihu, Douyin and Baidu plus any RSS feeds you add, keeps what matches your keywords, writes an HTML report, optionally adds an AI summary, and pushes the result to your chat or phone.

## About Hosting TrendRadar

This community template runs TrendRadar 6.11.0 the way upstream's Docker setup intends: one long-running container whose built-in scheduler crawls every 30 minutes, plus once at boot. Config and reports live on a volume, the daily SQLite history in a Railway Bucket. A private newsnow service supplies the hot lists, so you do not depend on the shared public API. The report pages sit behind a generated login, and the optional MCP server lets AI assistants search your collected news with a bearer token. No API key is needed to start.

## Common Use Cases

- Keyword alerts: follow companies, products, people or topics across Chinese hot lists and global RSS feeds, and receive only the matches
- Daily or timed briefings with an optional AI summary and translation of what moved
- China market and media watch for teams outside China, with titles translated by your LLM
- Trend history you own: dated HTML reports and per-day SQLite files
- A news source for AI agents through the MCP server (search, trends, sentiment, summaries)

## Dependencies for TrendRadar Hosting

- Nothing to sign up for: the template includes newsnow (hot-list API), a Railway Bucket and a volume
- Optional: an LLM API key for AI analysis and translation (any LiteLLM provider or OpenAI-compatible endpoint)
- Optional: one or more notification channels (Telegram, Slack, ntfy, Discord or other webhooks, Bark, Feishu, DingTalk, WeCom, email)

### Deployment Dependencies

- [TrendRadar on GitHub](https://github.com/sansan0/TrendRadar) (GPL-3.0), tag [v6.11.0](https://github.com/sansan0/TrendRadar/tree/v6.11.0)
- [TrendRadar visual config editor](https://sansan0.github.io/TrendRadar/)
- [newsnow](https://github.com/ourongxing/newsnow) (MIT), the hot-list aggregation API
- [LiteLLM provider list](https://docs.litellm.ai/docs/providers) for `AI_MODEL` values

### Implementation Details

| Service | What it does | Public |
|---|---|---|
| gateway | Caddy: login for the report pages, token-protected `/mcp` route | yes |
| trendradar | Crawler and scheduler (supercronic), report server, volume at `/data` | no |
| trendradar-mcp | Upstream's MCP server with a bearer token; mirrors the history from the Bucket | no |
| newsnow | Scrapes the hot lists for the crawler (10-minute cache per source) | no |
| Bucket | Railway Bucket with the daily SQLite history | no |

**First login**

1. Wait for the three builds. The first crawl starts when trendradar boots and takes a few minutes.
2. Copy `REPORTS_PASSWORD` from the gateway's variables (user `admin`) and open `https://{your-domain}`. You land on the latest report; older ones are under `/html/`.
3. Add your keywords: paste a `frequency_words.txt` into `FREQUENCY_WORDS` on the trendradar service (start from upstream's English example or the visual editor), then deploy.
4. Add a channel, for example `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, `NTFY_TOPIC`, `SLACK_WEBHOOK_URL` or `GENERIC_WEBHOOK_URL`. The next crawl pushes the matches.
5. Optional AI: set `AI_API_KEY` and `AI_MODEL` (for example `deepseek/deepseek-v4-flash`, `openai/gpt-4o` or `gemini/gemini-2.5-flash`). Analysis and translation switch on automatically.

**Good to know**

- Hot lists come from newsnow, which scrapes each platform. This template runs it privately; to use the public instance instead set `PLATFORMS_API_URL=https://newsnow.busiyi.world/api/s`. The default lists are Chinese platforms; English content comes from RSS feeds and newsnow sources such as Hacker News, GitHub Trending or Product Hunt that you add in `CONFIG_YAML`.
- Report and push labels are in Chinese (upstream design). Keyword group names, the AI summary and translations follow your config, which starts in English (`CONFIG_LANGUAGE=en`).
- Email needs outbound SMTP, which Railway allows only on the Pro plan. Prefer a webhook channel.
- Each crawl with AI enabled calls your LLM; the schedule (`CRON_SCHEDULE`, default every 30 minutes) controls the cost.

**MCP for AI assistants:** send `Authorization: Bearer {MCP_TOKEN}` (from the trendradar-mcp variables) to `https://{your-domain}/mcp` (streamable HTTP), for example `claude mcp add --transport http trendradar https://{your-domain}/mcp --header "Authorization: Bearer {MCP_TOKEN}"`. Don't need it? Delete the trendradar-mcp service; `/mcp` then answers 404.

**Scaling:** keep trendradar at one replica (scheduler and volume). Raise its memory if you add many feeds or the AI filter. A shorter schedule than 10 minutes gains nothing because newsnow caches each source.

**Versions:** trendradar and trendradar-mcp build `FROM wantcat/trendradar:6.11.0` and `wantcat/trendradar-mcp:4.1.1`; their default config is downloaded from the same upstream commit and checked by SHA-256 (`services/*/defaults.json`). To upgrade, change both tags and the manifest, redeploy, and set `CONFIG_RESEED=true` once if the config format changed. newsnow is pinned to `v0.0.41`, Caddy to `2.11.7`.

### Why Deploy TrendRadar on Railway?

Railway runs the crawler, its scheduler, the hot-list API, the MCP server and storage from one template, with private networking, a volume and a Bucket already wired. You get HTTPS, logs and per-service metrics without maintaining a server, and you pay only for the small amount of memory and CPU the monitor uses.

This is a community template. It is not made, endorsed or supported by the TrendRadar or newsnow authors.
