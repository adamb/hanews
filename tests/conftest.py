from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hai.config import Settings, clear_settings_cache
from hai.db import connect
from hai.models import Source


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Settings:
    clear_settings_cache()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "sources.yaml").write_text(
        yaml.safe_dump(
            {
                "sources": [
                    {
                        "id": "ha_blog",
                        "name": "HA Blog",
                        "type": "rss",
                        "url": "https://example.test/atom.xml",
                        "authority": 1.0,
                        "categories": ["home_assistant"],
                        "enabled": True,
                    },
                    {
                        "id": "noise",
                        "name": "Noise Pub",
                        "type": "rss",
                        "url": "https://example.test/noise.xml",
                        "authority": 0.4,
                        "categories": ["industry"],
                        "enabled": True,
                    },
                    {
                        "id": "ha_core",
                        "name": "HA Core",
                        "type": "github_releases",
                        "repo": "home-assistant/core",
                        "authority": 1.0,
                        "categories": ["home_assistant"],
                        "enabled": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (config_dir / "topics.yaml").write_text(
        yaml.safe_dump({"topics": ["home_assistant", "matter", "thread", "esphome"]}),
        encoding="utf-8",
    )
    (config_dir / "scoring.yaml").write_text(
        yaml.safe_dump(
            {
                "weights": {
                    "relevance": 0.25,
                    "novelty": 0.20,
                    "importance": 0.20,
                    "authority": 0.15,
                    "personal_interest": 0.20,
                },
                "keep_threshold": 50,
                "digest": {
                    "max_stories": 8,
                    "min_overall_score": 55,
                    "recency_days": 14,
                },
                "classify": {"recency_days": 14, "max_per_run": 40},
                "keyword_gate": {
                    "enabled": True,
                    "min_authority_to_skip": 0.85,
                    "keywords": ["home assistant", "matter", "thread", "esphome"],
                },
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        xai_api_key="test-key",
        xai_model="grok-4.5",
        hai_data_dir=tmp_path / "data",
        hai_cache_dir=tmp_path / "cache",
        hai_output_dir=tmp_path / "output",
        config_dir=config_dir,
        hai_timezone="America/Puerto_Rico",
        hai_max_classify_per_run=40,
    )
    settings.hai_data_dir.mkdir(parents=True, exist_ok=True)
    settings.digest_dir.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.fixture
def db(tmp_settings: Settings):
    conn = connect(tmp_settings)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def ha_source() -> Source:
    return Source(
        id="ha_blog",
        name="HA Blog",
        type="rss",
        url="https://example.test/atom.xml",
        authority=1.0,
        categories=["home_assistant"],
    )
