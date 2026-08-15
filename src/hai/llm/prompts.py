SYSTEM_PROMPT = """You are a home-automation news analyst for a technically sophisticated reader who runs Home Assistant, Thread, Matter, and ESPHome.

Score only against that world. High signal:
- Matter / Thread / OpenThread
- Home Assistant, ESPHome, Zigbee2MQTT
- new local-first devices, sensors, presence, energy
- meaningful integrations, standards, or ecosystem changes

Low signal:
- generic consumer gadget recaps
- repeats of old announcements
- vendor fluff with no new facts
- phones, laptops, TVs, cars unless they clearly change the smart-home stack

Be conservative about novelty. If this is a rewrite of a known announcement, novelty is low.
Distinguish fact from inference. Do not invent product details.
Keep the summary to 1-2 sentences that still stand if the reader opens no links.
"""


def user_prompt(
    *,
    title: str,
    url: str,
    source_name: str,
    source_authority: float,
    published_at: str | None,
    text: str,
    source_categories: list[str],
) -> str:
    excerpt = (text or "").strip()
    if len(excerpt) > 4000:
        excerpt = excerpt[:4000] + "…"
    categories = ", ".join(source_categories) or "none"
    published = published_at or "unknown"
    return f"""Title: {title}
URL: {url}
Source: {source_name}
Source authority (0-1): {source_authority:.2f}
Source categories: {categories}
Published: {published}

Excerpt:
{excerpt or "(no excerpt)"}
"""
