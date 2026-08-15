# Home Automation Intelligence (hai)

A local Python CLI that discovers home-automation news, filters for signal, and writes a daily Markdown digest.

This file is binding for anyone (human or agent) working in this repo.

## Server safety

This machine is a shared server. Treat everything outside this repo and `/mnt/backup/hanews` as production for other projects.

**Never**

- `apt`, `apt-get`, `snap`, or system `pip` / `pip3`
- install or upgrade global packages
- use Docker, pull images, or start containers
- change network, firewall, DNS, Samba, NFS, or Tailscale settings
- edit `/etc`, systemd system units, or system crontab
- touch `~/.venv/esphome` or any other project venv
- edit Hermes, Telegram, Home Assistant, Frigate, or other repos
- bind a new listening port
- write large files to `/` or `/home`

**Always**

- put the venv, uv cache, SQLite DB, and fetch cache on `/mnt/backup/hanews`
- keep only source and small digest Markdown on the main disk
- isolate Python via this project's venv
- keep secrets in the gitignored `.env`
- prefer user-local tools that already exist (`uv`, `gh`, system Python 3.12)

`PATH` on this host currently puts `~/.venv/esphome/bin` first. Never run bare `python` / `pip`. Use `uv run` with the env vars below, or the venv at `/mnt/backup/hanews/.venv/bin/python`.

## Disk layout

```text
/home/adam/code/hanews/          # git repo (small)
/mnt/backup/hanews/.venv/        # project virtualenv
/mnt/backup/hanews/.cache/uv/    # uv cache
/mnt/backup/hanews/data/hai.db   # SQLite
/mnt/backup/hanews/cache/        # HTTP / feed cache
```

## How to run commands

```bash
export UV_PROJECT_ENVIRONMENT=/mnt/backup/hanews/.venv
export UV_CACHE_DIR=/mnt/backup/hanews/.cache/uv
export PATH="/home/adam/.local/bin:/usr/bin:$PATH"

uv sync --extra dev
uv run pytest
uv run hai pipeline run
uv run hai pipeline run --push
```

Or: `scripts/setup.sh` then `scripts/hai.sh pipeline run`.

## Product rules

- Optimize for signal, novelty, and relevance. Not volume.
- Deterministic code for fetch, parse, schedule, hash, URLs, dedupe, storage, retries.
- Models only for relevance, classification, novelty judgment, importance, summarization.
- Validate every model response against the Pydantic schema. One bad response must not abort the run.
- One broken source must not abort discovery.
- Every keep/reject is a row in `decisions`. "Why did this appear?" and "Why did that not appear?" are requirements.
- Digests are written to `output/digests/YYYY-MM-DD.md` and may be committed. Never commit `.env`, the SQLite DB, or raw caches.
- No autonomous publishing. Phase 1 is the daily brief only.
- Intended LLM is Grok. Prefer `LLM_PROVIDER=xai` with a console key that can call chat/responses.
- On this host the existing Hermes `XAI_API_KEY` is denied for chat, so the working default is `LLM_PROVIDER=openrouter` and model `x-ai/grok-4.5`. Switch back to `api.x.ai` when a chat-capable xAI key is available. Never commit either key.

## Scope lock (MVP)

In: RSS + GitHub releases → SQLite → dedupe → xAI classify/score → Markdown digest → optional git push.

Out: articles, CMS, Telegram, email, cron, Hermes jobs, Reddit/X/YouTube, certification scrapers, web UI, Docker.

## Tests

Prioritize deterministic tests. Do not call the live xAI or GitHub APIs in unit tests. Use fixtures and mocks.
