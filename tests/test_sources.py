from hai.config import load_scoring, load_sources, load_topics


def test_fixture_sources_load(tmp_settings) -> None:
    sources = load_sources(tmp_settings)
    assert [s.id for s in sources] == ["ha_blog", "noise", "ha_core"]
    assert sources[0].type == "rss"
    assert sources[2].repo == "home-assistant/core"


def test_repo_sources_are_enabled() -> None:
    from hai.config import Settings
    from hai.config import REPO_ROOT

    settings = Settings(config_dir=REPO_ROOT / "config")
    sources = [s for s in load_sources(settings) if s.enabled]
    assert any(s.id == "home_assistant_blog" for s in sources)
    assert any(s.type == "github_releases" for s in sources)
    topics = load_topics(settings)
    assert "thread" in topics
    scoring = load_scoring(settings)
    assert abs(sum(scoring["weights"].values()) - 1.0) < 1e-6
