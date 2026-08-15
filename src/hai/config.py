"""Load YAML config and environment settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from hai.models import Source

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKUP_ROOT = Path("/mnt/backup/hanews")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    xai_api_key: str = ""
    xai_model: str = "grok-4.5"
    xai_base_url: str = "https://api.x.ai/v1"
    llm_provider: str = "xai"
    openrouter_api_key: str = ""
    openrouter_model: str = "x-ai/grok-4.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    github_token: str = ""
    hai_data_dir: Path = DEFAULT_BACKUP_ROOT / "data"
    hai_cache_dir: Path = DEFAULT_BACKUP_ROOT / "cache"
    hai_output_dir: Path | None = None
    hai_timezone: str = "America/Puerto_Rico"
    hai_max_classify_per_run: int = 40
    database_url: str = ""

    config_dir: Path = Field(default=REPO_ROOT / "config")

    @property
    def db_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url.removeprefix("sqlite:///")
            path = Path(raw)
            if not path.is_absolute():
                return REPO_ROOT / path
            return path
        return self.hai_data_dir / "hai.db"

    @property
    def output_dir(self) -> Path:
        if self.hai_output_dir:
            return self.hai_output_dir
        return REPO_ROOT / "output"

    @property
    def digest_dir(self) -> Path:
        return self.output_dir / "digests"

    @property
    def active_model(self) -> str:
        if self.llm_provider == "openrouter":
            return self.openrouter_model
        return self.xai_model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env", override=False)
    settings = Settings()
    settings.hai_data_dir.mkdir(parents=True, exist_ok=True)
    settings.hai_cache_dir.mkdir(parents=True, exist_ok=True)
    settings.digest_dir.mkdir(parents=True, exist_ok=True)
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def load_sources(settings: Settings | None = None) -> list[Source]:
    settings = settings or get_settings()
    payload = _load_yaml(settings.config_dir / "sources.yaml")
    sources: list[Source] = []
    for raw in payload.get("sources", []):
        sources.append(
            Source(
                id=raw["id"],
                name=raw["name"],
                type=raw["type"],
                authority=float(raw.get("authority", 0.5)),
                categories=list(raw.get("categories") or []),
                url=raw.get("url"),
                repo=raw.get("repo"),
                poll_interval=raw.get("poll_interval"),
                enabled=bool(raw.get("enabled", True)),
            )
        )
    return sources


def load_topics(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    payload = _load_yaml(settings.config_dir / "topics.yaml")
    return list(payload.get("topics") or [])


def load_scoring(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    return _load_yaml(settings.config_dir / "scoring.yaml")


def github_token(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.github_token:
        return settings.github_token
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env:
        return env
    return ""
