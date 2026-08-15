# Home Automation Intelligence

A personal home-automation news intelligence system that discovers relevant news, filters out noise, sends a daily digest, and can generate publishable blog articles.

The initial focus is:

- Home Assistant
- Matter
- Thread
- ESPHome
- Zigbee / Zigbee2MQTT
- new smart-home devices
- new integrations
- interesting automation ideas
- developer / enthusiast hardware
- meaningful ecosystem changes

The system should optimize for **signal, novelty, and relevance**, not volume.

---

## Goals

### Phase 1 — Daily intelligence brief

Build an autonomous pipeline that:

1. discovers candidate stories from trusted and exploratory sources
2. normalizes and stores them
3. deduplicates repeated coverage
4. scores each item for relevance and importance
5. logs what was accepted and rejected, including why
6. produces one concise daily digest
7. delivers the digest once per day

The digest should answer:

- What happened?
- Why is it interesting?
- Why do I care?
- Is it actually new?
- What is the primary source?
- Is this worth reading in full?

### Phase 2 — Article generation

For sufficiently important stories, generate a draft article suitable for an existing blog.

Articles should:

- be based on primary sources whenever possible
- cite or link to source material
- add useful context rather than merely paraphrase
- explain why the development matters
- distinguish fact from inference
- avoid publishing duplicate stories
- be generated as drafts by default

### Phase 3 — Publication

Add a blog adapter that can:

- create a draft
- update a draft
- publish an approved article
- store the resulting URL / post ID

Keep the publishing integration isolated from the core pipeline so the CMS can be swapped later.

---

## Non-goals

Initially, do **not** optimize for:

- maximum article volume
- fully autonomous public publishing
- social-media posting
- SEO tricks
- broad consumer-tech coverage
- replacing the source material with AI summaries

The first milestone is a daily brief that is consistently worth reading.

---

## Architecture

```text
                         DISCOVERY
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
        RSS             Web Search          APIs
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            ▼
                    Candidate Items
                            │
                            ▼
                      Normalize
                            │
                            ▼
                      Deduplicate
                            │
                            ▼
                       Enrich
                            │
                            ▼
                     Score / Rank
                            │
                ┌───────────┴───────────┐
                │                       │
             Reject                   Keep
                │                       │
                ▼                       ▼
          Rejection Log          Story Database
                                        │
                         ┌──────────────┴──────────────┐
                         │                             │
                         ▼                             ▼
                   Daily Digest                  Article Draft
                         │                             │
                         ▼                             ▼
                      Delivery                    Blog Adapter
```

---

## Design principles

### Discovery and authority are separate

A low-authority source may be excellent for discovering a story.

Example:

- Reddit discovers an unreleased device.
- The manufacturer documentation confirms it.
- The CSA certification database confirms Matter support.
- The final story cites the authoritative sources, not the Reddit post.

### Prefer primary sources

When available, prefer:

1. manufacturer / project announcement
2. official documentation
3. certification records
4. GitHub releases / PRs
5. reputable reporting
6. community discussion
7. aggregators

### Log every decision

Every candidate should have a machine-readable record showing why it was kept or discarded.

Example:

```json
{
  "url": "https://example.com/story",
  "decision": "reject",
  "reason": "duplicate",
  "duplicate_of": "story_123",
  "relevance_score": 42,
  "novelty_score": 10
}
```

This is critical for debugging autonomous runs.

### Keep deterministic code around the model

Use normal code for:

- fetching
- parsing
- scheduling
- hashing
- canonical URLs
- duplicate detection
- storage
- retries
- publishing

Use models for:

- semantic relevance
- classification
- novelty judgment
- story importance
- summarization
- synthesis
- article drafting

---

## Initial sources

Start with a curated source registry.

### Primary ecosystem sources

- Home Assistant blog
- Home Assistant Core GitHub releases
- Home Assistant frontend / supervisor / OS releases where useful
- ESPHome releases and blog
- Zigbee2MQTT releases / supported-device changes
- Thread Group
- Connectivity Standards Alliance / Matter
- relevant GitHub repositories

### Manufacturers

Track product announcements, release notes, product catalogs, and support/documentation pages from companies such as:

- Aqara
- Eve
- Shelly
- Inovelli
- IKEA
- Philips Hue / Signify
- Sonoff / Itead
- SwitchBot
- Nanoleaf
- Govee
- ThirdReality
- Zooz
- Lutron
- Yale
- Nuki
- Ecobee
- Reolink
- Ubiquiti / UniFi
- Apollo Automation
- Everything Presence

### Publications

Examples:

- The Verge / Smart Home
- Ars Technica
- 9to5Mac
- 9to5Google
- HomeKit-focused publications
- CNX Software
- Hackster
- Hackaday

### Community / discovery

- Reddit
- Home Assistant Community
- Hacker News where relevant
- YouTube channels / transcripts
- X / social search

### Interesting upstream sources

Later, add:

- CSA certification listings
- Thread certification/product listings
- FCC filings
- manufacturer documentation indexes
- retailer product catalogs
- app release notes
- GitHub PRs
- trademark / regulatory filings

---

## Source registry

Represent sources as configuration instead of hard-coding them.

Example:

```yaml
sources:
  - id: home_assistant_blog
    name: Home Assistant Blog
    type: rss
    url: https://www.home-assistant.io/atom.xml
    authority: 1.0
    categories:
      - home_assistant

  - id: home_assistant_core
    name: Home Assistant Core Releases
    type: github_releases
    repo: home-assistant/core
    authority: 1.0
    categories:
      - home_assistant
      - integrations
```

A source may have:

- `id`
- `name`
- `type`
- `url`
- `repo`
- `authority`
- `categories`
- `poll_interval`
- `enabled`

---

## Data model

SQLite is sufficient for the initial version.

### `items`

Raw discovered items.

Suggested fields:

```text
id
source_id
source_item_id
url
canonical_url
title
author
published_at
discovered_at
raw_text
raw_metadata_json
content_hash
```

### `stories`

Normalized / enriched story records.

```text
id
primary_item_id
topic
summary
relevance_score
novelty_score
importance_score
authority_score
personal_interest_score
overall_score
decision
decision_reason
created_at
updated_at
```

### `story_items`

Many-to-many mapping between one story and multiple source items.

```text
story_id
item_id
relationship
```

Relationships might include:

- primary
- corroboration
- duplicate
- commentary
- community

### `runs`

Track every autonomous run.

```text
id
job_name
started_at
finished_at
status
metrics_json
error
```

### `decisions`

Detailed model / rules-engine decisions.

```text
id
story_id
run_id
decision_type
input_json
output_json
model
created_at
```

### `articles`

```text
id
story_id
title
slug
status
body_markdown
sources_json
cms_post_id
cms_url
created_at
updated_at
published_at
```

---

## Classification taxonomy

Initial topics:

```text
matter
thread
home_assistant
esphome
zigbee
zwave
wifi
bluetooth
devices
sensors
switches
lighting
locks
cameras
energy
presence
voice
automation_ideas
integrations
developer_tools
privacy
security
standards
industry
```

Items may have multiple topics.

---

## Scoring

Score each story from 0–100.

Suggested inputs:

### Relevance

How closely does this fit the subject matter?

Examples of high relevance:

- new Matter-over-Thread device
- significant Home Assistant release
- new ESPHome capability
- important Thread change
- useful new integration

### Novelty

Is this actually new?

Penalize:

- repeated press coverage
- articles summarizing older announcements
- rewritten vendor press releases
- stories already covered recently

### Importance

How consequential is the development?

### Source authority

How trustworthy and close to the primary source is the evidence?

### Personal interest

Initially weight these especially highly:

- Thread
- Matter
- Home Assistant
- ESPHome
- novel sensors
- presence detection
- energy monitoring
- local-first devices
- useful hacks
- unusual automation techniques

### Overall score

Start simple:

```text
overall =
    relevance        * 0.25 +
    novelty          * 0.20 +
    importance       * 0.20 +
    authority        * 0.15 +
    personal_interest * 0.20
```

Store component scores so the algorithm can be tuned later.

---

## Model output contract

Do not accept free-form classification output.

Require structured JSON.

Example:

```json
{
  "topics": ["thread", "matter", "devices"],
  "relevance_score": 96,
  "novelty_score": 88,
  "importance_score": 71,
  "personal_interest_score": 97,
  "decision": "keep",
  "reason": "New Matter-over-Thread presence sensor from a major vendor.",
  "why_it_matters": "Adds a local low-power presence sensor option for Thread-based Home Assistant installations.",
  "claims_to_verify": [
    "Matter certification",
    "Thread support",
    "shipping date"
  ]
}
```

Validate model output against a schema.

---

## Deduplication

Use several layers:

1. exact canonical URL
2. normalized title similarity
3. content hash
4. semantic similarity
5. LLM story-equivalence judgment only when needed

Multiple articles covering the same announcement should become **one story with multiple sources**, not multiple stories.

---

## Daily digest

Generate one digest per day from the highest-ranked uncaught stories.

A useful format:

```text
HOME AUTOMATION DAILY BRIEF

1. Aqara announces ...
   Score: 94
   Topics: Thread, Matter, Presence

   What happened:
   ...

   Why it matters:
   ...

   Why you care:
   ...

   Sources:
   ...

2. Home Assistant 2026.x ships ...
   ...
```

Keep the first version short.

Target:

- 5–10 stories
- one paragraph of summary each
- primary-source link
- optional "read this" recommendation

The digest should be useful even if no links are opened.

---

## Delivery

Define delivery behind an adapter.

```python
class DigestSink:
    def send(self, digest: Digest) -> None:
        ...
```

Possible implementations later:

- email
- Telegram
- Slack
- Discord
- Markdown file
- web page

For development, always support writing the digest to:

```text
output/digests/YYYY-MM-DD.md
```

---

## Article generation

Only generate an article when a story crosses a configurable threshold.

Example:

```text
overall_score >= 85
importance_score >= 65
authority_score >= 70
```

Article pipeline:

```text
Story
  ↓
collect best sources
  ↓
extract factual claims
  ↓
identify missing verification
  ↓
research / corroborate
  ↓
outline
  ↓
draft
  ↓
fact-check against sources
  ↓
save as draft
```

The article should contain original synthesis.

Avoid:

- padded summaries
- fake quotes
- unsupported claims
- invented product details
- copying source phrasing
- writing from a single secondary article when primary sources exist

---

## Blog integration

Implement a CMS interface:

```python
class BlogPublisher:
    def create_draft(self, article: Article) -> PublishedPost:
        ...

    def update_draft(self, post_id: str, article: Article) -> PublishedPost:
        ...

    def publish(self, post_id: str) -> PublishedPost:
        ...
```

The initial implementation can target the existing blog.

Keep credentials in environment variables.

Do not put CMS-specific logic in the discovery or writing layers.

---

## Hermes

Hermes should act as the **orchestrator**, not as the database or application architecture.

Good uses for Hermes:

- run discovery jobs
- invoke specialized agents
- run scheduled workflows
- retry failed stages
- inspect logs
- trigger the daily digest
- trigger article generation
- perform exploratory web research

The underlying Python code should still be runnable directly without Hermes.

Example conceptual jobs:

```text
discover_rss
discover_github
discover_web
normalize_items
deduplicate
score_stories
build_daily_digest
deliver_daily_digest
generate_article_candidates
```

This lets us debug a failed task independently of the agent framework.

---

## Repository layout

Suggested starting point:

```text
.
├── README.md
├── pyproject.toml
├── .env.example
├── config/
│   ├── sources.yaml
│   ├── topics.yaml
│   └── scoring.yaml
├── src/
│   └── hai/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── db.py
│       ├── models.py
│       ├── discovery/
│       │   ├── base.py
│       │   ├── rss.py
│       │   ├── github.py
│       │   └── web.py
│       ├── pipeline/
│       │   ├── normalize.py
│       │   ├── dedupe.py
│       │   ├── classify.py
│       │   ├── score.py
│       │   └── enrich.py
│       ├── digest/
│       │   ├── generate.py
│       │   └── sinks.py
│       ├── articles/
│       │   ├── research.py
│       │   ├── generate.py
│       │   └── verify.py
│       ├── publishing/
│       │   ├── base.py
│       │   └── blog.py
│       └── llm/
│           ├── client.py
│           ├── prompts.py
│           └── schemas.py
├── tests/
├── data/
│   └── .gitkeep
└── output/
    ├── digests/
    └── articles/
```

---

## CLI

Everything important should be runnable from a CLI.

Examples:

```bash
hai discover
hai classify
hai digest
hai digest --date today
hai articles candidates
hai articles generate STORY_ID
hai publish STORY_ID --draft
hai pipeline run
```

This makes Hermes integration easy: Hermes can call stable CLI commands rather than being responsible for application logic.

---

## Observability

Every run should answer:

```text
How many items were fetched?
How many were new?
How many were duplicates?
How many became stories?
How many were rejected?
Why were they rejected?
How many exceeded the digest threshold?
How many exceeded the article threshold?
What failed?
```

Example:

```text
Discovery run 2026-08-15

Sources polled:       42
Items fetched:       318
New items:            67
Duplicates:          251
Stories created:      31

Rejected:
  irrelevant:         14
  stale:               6
  low authority:       2

Kept:                  9
Digest stories:        6
Article candidates:    2
```

Logs should be both human-readable and machine-queryable.

---

## Reliability

Assume every external dependency will eventually fail.

Every network operation should have:

- timeout
- retries with backoff
- failure logging
- source-level isolation

One broken RSS feed must not abort the discovery run.

One bad model response must not abort the scoring run.

One failed article must not prevent the daily digest.

---

## Configuration

Example `.env.example`:

```bash
DATABASE_URL=sqlite:///data/hai.db

OPENAI_API_KEY=

# Optional search providers
SEARCH_API_KEY=

# Optional CMS
BLOG_BASE_URL=
BLOG_API_KEY=

# Delivery
DIGEST_EMAIL_TO=
```

Never commit secrets.

---

## Testing strategy

Prioritize tests for deterministic behavior:

- URL canonicalization
- feed parsing
- duplicate detection
- source configuration
- score calculation
- schema validation
- database operations
- CMS adapter
- failure / retry behavior

Record representative model inputs/outputs so most tests do not require live API calls.

---

## MVP

The first working version should do only this:

```text
RSS + GitHub sources
        ↓
SQLite
        ↓
deduplicate
        ↓
LLM classify + score
        ↓
top stories
        ↓
daily Markdown digest
```

Do **not** start with autonomous publishing.

Once the daily digest is good enough that it is genuinely useful every day, add:

1. broader web discovery
2. Reddit / community discovery
3. certification databases
4. article drafting
5. CMS draft creation
6. SEO / GEO research and optimization
7. automated publication

---

## First implementation milestone

Success means this command works:

```bash
hai pipeline run
```

And produces:

```text
output/digests/YYYY-MM-DD.md
```

containing a useful, deduplicated, ranked summary of the day's most important home-automation developments.

The pipeline should also leave enough logs and database state to answer:

> Why did this story appear?

and:

> Why did that story not appear?

Those two questions are requirements, not nice-to-haves.

---

## Future directions

After the core intelligence pipeline is reliable:

- personalized relevance model based on previous feedback
- "never miss a new Thread device" dedicated watcher
- Matter certification watcher
- product database
- automatic comparison pages
- weekly trend reports
- evergreen explainers

---

## Running (this machine)

Do not use the system Python or the ESPHome venv. Data and the project venv live on the backup disk.

```bash
scripts/setup.sh
scripts/hai.sh pipeline run
scripts/hai.sh pipeline run --push   # commit + push the digest
scripts/hai.sh explain URL_OR_STORY_ID
```

Config is in `config/`. Secrets are in `.env` (never committed). Digests are written to `output/digests/YYYY-MM-DD.md` and can be pushed to GitHub.
- SEO topic clustering
- GEO / answer-engine optimization
- newsletter generation
- public site
- social distribution
- story follow-ups when products actually ship
- price / availability tracking
- Home Assistant compatibility tracking
- automatic discovery of new sources

---

## Philosophy

The valuable asset is not the blog.

The valuable asset is the **intelligence pipeline**:

```text
discover → verify → understand → rank → synthesize
```

The daily brief, blog articles, newsletter, website, alerts, and search-optimized pages are all outputs of that same system.

Build the intelligence layer first.
