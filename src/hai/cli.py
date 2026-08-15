from __future__ import annotations

import logging
from typing import Optional

import typer

from hai.config import get_settings, github_token, load_scoring, load_sources
from hai.db import session
from hai.digest.generate import today_in_tz, write_digest
from hai.explain import format_explanation, resolve_story
from hai.gitutil import GitError, push_digest
from hai.pipeline.classify import classify_story, pending_stories
from hai.pipeline.run import format_run_summary, ingest_source, run_pipeline

app = typer.Typer(help="Home Automation Intelligence", no_args_is_help=True)
pipeline_app = typer.Typer(help="Run pipeline stages")
app.add_typer(pipeline_app, name="pipeline")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@app.command()
def discover() -> None:
    """Fetch sources and store new items / stories. No LLM calls."""
    _configure_logging()
    settings = get_settings()
    scoring = load_scoring(settings)
    recency_days = int((scoring.get("classify") or {}).get("recency_days", 14))
    token = github_token(settings)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    totals = {}
    with session(settings) as conn:
        from hai.db import start_run, finish_run

        run_id = start_run(conn, "discover")
        for source in [s for s in load_sources(settings) if s.enabled]:
            stats = ingest_source(
                conn,
                source,
                run_id=run_id,
                token=token,
                recency_days=recency_days,
                now=now,
            )
            typer.echo(f"{source.id}: {dict(stats)}")
            for key, value in stats.items():
                totals[key] = totals.get(key, 0) + value
        finish_run(conn, run_id, status="ok", metrics=totals)
    typer.echo(f"discover done: {totals}")


@app.command()
def classify() -> None:
    """Classify pending recent stories with xAI."""
    _configure_logging()
    settings = get_settings()
    scoring = load_scoring(settings)
    recency_days = int((scoring.get("classify") or {}).get("recency_days", 14))
    limit = min(
        settings.hai_max_classify_per_run,
        int((scoring.get("classify") or {}).get("max_per_run", 40)),
    )
    with session(settings) as conn:
        from hai.db import start_run, finish_run

        run_id = start_run(conn, "classify")
        results = []
        for story in pending_stories(conn, recency_days=recency_days, limit=limit):
            result = classify_story(conn, story, run_id=run_id, settings=settings)
            typer.echo(f"story {story['id']}: {result}")
            results.append(result)
        finish_run(conn, run_id, status="ok", metrics={"classified": len(results)})
    typer.echo(f"classified {len(results)} stories")


@app.command()
def digest(
    date: Optional[str] = typer.Option(None, help="YYYY-MM-DD or 'today'"),
    push: bool = typer.Option(False, help="Commit and push the digest"),
) -> None:
    """Write the daily Markdown digest from already-classified stories."""
    _configure_logging()
    settings = get_settings()
    if date in (None, "today"):
        date = today_in_tz(settings.hai_timezone)
    with session(settings) as conn:
        path, story_ids = write_digest(conn, digest_date=date, settings=settings)
    typer.echo(f"Wrote {path} ({len(story_ids)} stories)")
    if push:
        try:
            typer.echo(push_digest(path, date))
        except GitError as exc:
            raise typer.Exit(f"git push failed: {exc}") from exc


@app.command()
def explain(ref: str = typer.Argument(..., help="Story id, item id, or URL")) -> None:
    """Show why a story was kept or rejected."""
    settings = get_settings()
    with session(settings) as conn:
        story = resolve_story(conn, ref)
        if story is None:
            raise typer.Exit(f"No story found for {ref}")
        typer.echo(format_explanation(conn, story))


@pipeline_app.command("run")
def pipeline_run(
    push: bool = typer.Option(False, "--push", help="Commit and push the digest"),
    date: Optional[str] = typer.Option(None, help="Digest date YYYY-MM-DD"),
) -> None:
    """Discover, classify, and write today's digest."""
    _configure_logging()
    metrics = run_pipeline(push=push, date=date)
    typer.echo(format_run_summary(metrics))
    if metrics.get("push_error"):
        raise typer.Exit(f"pipeline succeeded but push failed: {metrics['push_error']}")
