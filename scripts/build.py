#!/usr/bin/env python3
import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BASE = "https://udeudeude.github.io/Living-Patterns-Podcast"

def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)

def rfc2822(value):
    return format_datetime(dt(value), usegmt=True)

def x(value):
    return html.escape(str(value), quote=True)

def text_escape(value):
    return html.escape(str(value), quote=False)

def pretty_date(value):
    d = dt(value)
    return f"{d.day} {d.strftime('%B %Y')}"

def ambience_text(amb):
    if not amb:
        return ""
    text = f"Ambience: {amb['label']} by {amb['creator']}"
    if amb.get("source_url"):
        text += f" ({amb['source_url']})"
    if amb.get("license"):
        text += f", {amb['license']}"
    if amb.get("license_url"):
        text += f" ({amb['license_url']})"
    return text + "."

def ambience_html(amb):
    if not amb:
        return ""
    label = x(amb["label"])
    creator = x(amb["creator"])
    if amb.get("source_url"):
        label = f'<a href="{x(amb["source_url"])}">{label}</a>'
    license_text = x(amb.get("license", ""))
    if amb.get("license_url"):
        license_text = f'<a href="{x(amb["license_url"])}">{license_text}</a>'
    suffix = f", {license_text}" if license_text else ""
    return f'<p class="audio-credit">Ambience: {label} by {creator}{suffix}.</p>'

def validate(show, episodes, preview):
    errors = []
    published = [e for e in episodes if e.get("status") == "published"]
    nums = [e["number"] for e in published]
    guids = [e["guid"] for e in published]
    if len(nums) != len(set(nums)):
        errors.append("duplicate published episode number")
    if len(guids) != len(set(guids)):
        errors.append("duplicate published GUID")
    if nums and sorted(nums) != list(range(min(nums), max(nums) + 1)):
        errors.append("published episode numbers are not contiguous")
    known = set(nums)
    for e in published + preview:
        if not re.fullmatch(r"\d+:\d{2}", e["duration"]):
            errors.append(f"episode {e.get('number')} has malformed duration")
        if not e.get("tags") or not 2 <= len(e["tags"]) <= 4:
            errors.append(f"episode {e.get('number')} must have 2–4 tags")
        if "Garden ambience:" in "\n".join(e.get("reflection", [])):
            errors.append(f"episode {e.get('number')} has ambience credit inside reflection text")
        if "Ambience:" in "\n".join(e.get("reflection", [])):
            errors.append(f"episode {e.get('number')} has ambience credit inside reflection text")
        audio = ROOT / e["audio"]
        if not audio.exists():
            errors.append(f"missing audio: {e['audio']}")
        elif audio.stat().st_size < 1000:
            errors.append(f"audio file implausibly small: {e['audio']}")
        if e in published:
            for rel in e.get("related", []):
                if rel == e["number"] or rel not in known:
                    errors.append(f"episode {e['number']} has invalid related episode {rel}")
        if not e.get("concept_note"):
            errors.append(f"episode {e.get('number')} missing concept note")
    if not show.get("lineage"):
        errors.append("show lineage is empty")
    if errors:
        raise SystemExit("\n".join("ERROR: " + err for err in errors))

def feed_item(e):
    body = "\n\n".join(e["reflection"])
    body += f"\n\n{e['ending_label']}\n{e['ending']}"
    if e.get("concept_note"):
        body += f"\n\nConcept note: {e['concept_note']}"
    credit = ambience_text(e.get("ambience"))
    if credit:
        body += "\n\n" + credit
    if "]]>" in body:
        raise ValueError("CDATA terminator in episode content")
    audio_path = ROOT / e["audio"]
    size = audio_path.stat().st_size
    return f"""  <item>
    <title>{text_escape(e['title'])}</title>
    <description>{text_escape(e['description'])}</description>
    <content:encoded><![CDATA[{body}]]></content:encoded>
    <link>{BASE}/</link>
    <guid isPermaLink="false">{x(e['guid'])}</guid>
    <pubDate>{rfc2822(e['published_at'])}</pubDate>
    <enclosure url="{BASE}/{x(e['audio'])}" length="{size}" type="audio/mpeg"/>
    <itunes:title>{text_escape(e['title'])}</itunes:title>
    <itunes:author>Daily Living Patterns</itunes:author>
    <itunes:summary>{text_escape(e['description'])}</itunes:summary>
    <itunes:duration>{x(e['duration'])}</itunes:duration>
    <itunes:episode>{e['number']}</itunes:episode>
    <itunes:episodeType>full</itunes:episodeType>
    <itunes:explicit>false</itunes:explicit>
  </item>"""

def build_feed(show, episodes, preview=False):
    items = sorted(episodes, key=lambda e: e["number"], reverse=True)
    updates = [dt(e.get("updated_at", e["published_at"])) for e in items]
    if not updates:
        updates = [dt(e.get("updated_at", e["published_at"])) for e in load_json("episodes.json")]
    last = format_datetime(max(updates), usegmt=True)
    title = show["title"] + (" Preview" if preview else "")
    description = (
        "Private/unlisted pilot feed for evaluating Living Patterns production choices."
        if preview else show["description"]
    )
    atom = show["preview_feed_url"] if preview else show["feed_url"]
    items_xml = "\n".join(feed_item(e) for e in items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>{text_escape(title)}</title>
  <link>{x(show['link'])}</link>
  <description>{text_escape(description)}</description>
  <language>{x(show['language'])}</language>
  <copyright>{text_escape(show['copyright'])}</copyright>
  <lastBuildDate>{last}</lastBuildDate>
  <atom:link href="{x(atom)}" rel="self" type="application/rss+xml"/>
  <image><url>{BASE}/{x(show['cover'])}</url><title>{text_escape(title)}</title><link>{x(show['link'])}</link></image>
  <itunes:author>{text_escape(show['author'])}</itunes:author>
  <itunes:summary>{text_escape(show['summary'])}</itunes:summary>
  <itunes:type>episodic</itunes:type>
  <itunes:explicit>false</itunes:explicit>
  <itunes:image href="{BASE}/{x(show['cover'])}"/>
  <itunes:category text="{x(show['category'][0])}"><itunes:category text="{x(show['category'][1])}"/></itunes:category>
{items_xml}
</channel>
</rss>
"""

def episode_card(e, episode_by_number, latest=False):
    h = "h2" if latest else "h3"
    heading_id = "latest-heading" if latest else f"episode-{e['number']}-heading"
    classes = "episode-card featured-episode" if latest else "episode-card"
    tags_value = "|".join(e["tags"])
    tags = "".join(f'<span class="tag">{x(t)}</span>' for t in e["tags"])
    paragraphs = "".join(f"<p>{text_escape(p)}</p>" for p in e["reflection"])
    concept = f'<p class="concept-note"><strong>Concept note.</strong> {text_escape(e["concept_note"])}</p>'
    related = ""
    rels = [episode_by_number[n] for n in e.get("related", []) if n in episode_by_number]
    if rels:
        links = " · ".join(f'<a href="#episode-{r["number"]}">{x(r["title"])}</a>' for r in rels)
        related = f'<p class="related"><strong>Related reflections:</strong> {links}</p>'
    credit = ambience_html(e.get("ambience"))
    return f"""<article class="{classes}" id="episode-{e['number']}" data-tags="{x(tags_value)}" aria-labelledby="{heading_id}">
  <div class="episode-heading"><div><p class="date">{pretty_date(e['published_at'])} · {x(e['duration'])}</p><{h} id="{heading_id}">{text_escape(e['title'])}</{h}></div><span class="episode-number" aria-label="Episode {e['number']}">{e['number']:02d}</span></div>
  <audio controls preload="metadata" src="{BASE}/{x(e['audio'])}"><a href="{BASE}/{x(e['audio'])}">Download the episode audio</a></audio>
  <p class="summary">{text_escape(e['description'])}</p>
  <div class="tags" aria-label="Concepts">{tags}</div>
  <details><summary>Read the reflection</summary><div class="transcript">{paragraphs}<h4>{text_escape(e['ending_label'])}</h4><p>{text_escape(e['ending'])}</p>{concept}{related}{credit}</div></details>
</article>"""

def build_index(show, episodes):
    published = sorted([e for e in episodes if e.get("status") == "published"], key=lambda e: e["number"], reverse=True)
    latest = published[0]
    episode_by_number = {e["number"]: e for e in published}
    cards = "\n".join(episode_card(e, episode_by_number) for e in published[1:])
    latest_card = episode_card(latest, episode_by_number, latest=True)
    counts = Counter(tag for e in published for tag in e["tags"])
    buttons = ['<button class="concept-button active" type="button" data-filter="">All</button>']
    for tag, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        buttons.append(f'<button class="concept-button" type="button" data-filter="{x(tag)}">{x(tag)} <span>{count}</span></button>')
    concept_buttons = "".join(buttons)
    lineage = "".join(f"<p>{text_escape(p)}</p>" for p in show["lineage"])
    reading = "".join(f"<li><cite>{text_escape(t)}</cite></li>" for t in show["further_reading"])
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{text_escape(show['title'])} — Daily two-minute reflections</title>
<meta name="description" content="{x(show['summary'])}">
<link rel="canonical" href="{x(show['link'])}"><link rel="alternate" type="application/rss+xml" title="{x(show['title'])}" href="{x(show['feed_url'])}">
<meta property="og:title" content="{x(show['title'])}"><meta property="og:description" content="{x(show['summary'])}"><meta property="og:image" content="{BASE}/{x(show['og_image'])}">
<style>
:root{{--ink:#142b3d;--paper:#f4eddd;--cream:#fffaf0;--terra:#b85c35;--moss:#5a6641;--line:#142b3d33}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Arial,sans-serif}}a{{color:inherit}}.hero{{padding:28px clamp(22px,6vw,80px) 90px;background:linear-gradient(155deg,var(--cream),#efe4cf)}}nav{{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:24px}}.wordmark,h1,h2,h3,h4,.intro,.summary,.transcript,.about p{{font-family:Georgia,serif}}.wordmark{{text-decoration:none;font-size:1.25rem}}.feed{{font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em}}.grid{{max-width:1200px;margin:auto;padding-top:70px;display:grid;grid-template-columns:1.1fr .7fr;gap:8vw;align-items:center}}.eyebrow{{color:var(--terra);font-size:.72rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}}h1{{font-size:clamp(3.4rem,7vw,6.5rem);line-height:1.02;letter-spacing:-.055em;font-weight:400;margin:18px 0}}.intro{{font-size:1.3rem;line-height:1.55}}.cover{{display:block;width:100%;height:auto;aspect-ratio:1/1;object-fit:cover;box-shadow:0 28px 70px #142b3d2e}}.listen{{display:inline-block;margin-top:20px;padding:15px 22px;border-radius:999px;background:var(--ink);color:var(--cream);text-decoration:none;font-weight:700}}.latest,.archive,.concepts,.about{{padding:90px clamp(22px,8vw,120px)}}.latest{{padding-bottom:45px}}.archive{{padding-top:45px}}.archive-heading,.concepts-inner,.about-inner{{max-width:1000px;margin:0 auto 34px}}.archive-heading h2,.concepts h2,.about h2{{margin-bottom:0;font-size:clamp(2.2rem,4vw,4rem);font-weight:400}}.episode-list{{display:grid;gap:28px}}.episode-card{{max-width:1000px;margin:auto;background:var(--cream);padding:clamp(28px,5vw,65px);border:1px solid var(--line);scroll-margin-top:24px}}.episode-heading{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start}}.episode-heading h2,.episode-heading h3{{font-size:clamp(2.1rem,4.6vw,4.5rem);line-height:1.05;font-weight:400;margin:8px 0 28px}}.episode-number{{color:#142b3d3d;font-family:Georgia,serif;font-size:2.2rem}}.archive .episode-card{{width:100%}}.archive .episode-heading h3{{font-size:clamp(1.9rem,3.7vw,3.3rem)}}audio{{width:100%}}.summary,.transcript{{font-size:1.13rem;line-height:1.7}}.date{{color:var(--terra);font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.14em}}.tags{{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}}.tag{{border:1px solid #142b3d44;border-radius:999px;padding:6px 10px;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}}details{{margin-top:28px;border-top:1px solid var(--line);padding-top:22px}}summary{{cursor:pointer;font-weight:700;text-transform:uppercase;letter-spacing:.1em;font-size:.78rem}}.transcript{{max-width:740px;padding-top:20px}}.transcript h4{{font-size:1.35rem;font-weight:400;margin:30px 0 10px}}.audio-credit,.concept-note,.related{{margin-top:28px;color:#142b3daa;font-family:Arial,sans-serif;font-size:.82rem;line-height:1.55}}.related a{{text-decoration-thickness:1px;text-underline-offset:3px}}.concepts{{padding-top:45px;padding-bottom:45px;background:#e8dec8}}.concept-buttons{{display:flex;flex-wrap:wrap;gap:10px;margin-top:28px}}.concept-button{{appearance:none;border:1px solid #142b3d55;background:transparent;color:var(--ink);border-radius:999px;padding:9px 13px;cursor:pointer;font:inherit;font-size:.82rem}}.concept-button span{{opacity:.55}}.concept-button.active{{background:var(--ink);color:var(--cream)}}.about{{background:#efe4cf}}.about-inner{{display:grid;grid-template-columns:1.2fr .8fr;gap:7vw}}.about p{{font-size:1.08rem;line-height:1.65}}.reading-list{{line-height:1.8}}.subscribe{{padding:80px clamp(22px,8vw,120px);background:#dce0cb;display:grid;grid-template-columns:1fr 1fr;gap:8vw}}.subscribe h2{{margin:0}}.address{{word-break:break-all}}footer{{padding:26px clamp(22px,6vw,80px);background:var(--ink);color:#fffaf0bb;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}}[hidden]{{display:none!important}}@media(max-width:800px){{.grid,.subscribe,.about-inner{{grid-template-columns:1fr}}.cover{{max-width:480px}}.episode-heading{{align-items:flex-end}}.episode-number{{font-size:1.6rem}}}}
</style></head><body>
<header class="hero"><nav><a class="wordmark" href="{x(show['link'])}">{text_escape(show['title'])}</a><a class="feed" href="{x(show['feed_url'])}">RSS feed</a></nav><div class="grid"><div><p class="eyebrow">{text_escape(show['eyebrow'])}</p><h1>{text_escape(show['hero_title'])}</h1><p class="intro">{text_escape(show['hero_intro'])}</p><a class="listen" href="#latest">Listen to the latest</a></div><img class="cover" src="{BASE}/{x(show['cover'])}" alt="Living Patterns podcast cover, with abstract arches, paths, and garden forms" width="3000" height="3000"></div></header>
<main>
<section class="latest" id="latest" aria-label="Latest episode">{latest_card}</section>
<section class="concepts" aria-labelledby="concept-heading"><div class="concepts-inner"><p class="eyebrow">Browse by idea</p><h2 id="concept-heading">Concepts recur, deepen, and argue with one another.</h2><div class="concept-buttons" aria-label="Filter episodes by concept">{concept_buttons}</div></div></section>
<section class="archive" aria-labelledby="archive-heading"><div class="archive-heading"><p class="eyebrow">Previous episodes</p><h2 id="archive-heading">Earlier reflections</h2></div><div class="episode-list">{cards}</div></section>
<section class="about" id="about"><div class="about-inner"><div><p class="eyebrow">Source lineage</p><h2>Inspired by Alexander, not a substitute for Alexander.</h2>{lineage}</div><div><p class="eyebrow">Useful starting points</p><ul class="reading-list">{reading}</ul></div></div></section>
<section class="subscribe"><div><p class="eyebrow">Subscribe by URL</p><h2>A quiet practice, each day.</h2></div><div><p>In Apple Podcasts, choose <strong>Library</strong>, then <strong>Follow a Show by URL</strong>, and paste:</p><a class="address" href="{x(show['feed_url'])}">{text_escape(show['feed_url'])}</a></div></section>
</main><footer>© 2026 Daily Living Patterns · Original reflections, published daily</footer>
<script>
const buttons=[...document.querySelectorAll('.concept-button')];
const cards=[...document.querySelectorAll('.episode-card')];
buttons.forEach(button=>button.addEventListener('click',()=>{{
  buttons.forEach(b=>b.classList.remove('active'));button.classList.add('active');
  const filter=button.dataset.filter;
  cards.forEach(card=>{{const tags=(card.dataset.tags||'').split('|');card.hidden=Boolean(filter)&&!tags.includes(filter);}});
}}));
</script>
</body></html>
"""

def outputs(show, episodes, preview):
    return {
        ROOT / "feed.xml": build_feed(show, [e for e in episodes if e.get("status") == "published"]),
        ROOT / "preview-feed.xml": build_feed(show, preview, preview=True),
        ROOT / "index.html": build_index(show, episodes),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    show = load_json("show.json")
    episodes = load_json("episodes.json")
    preview = load_json("preview.json")
    validate(show, episodes, preview)
    generated = outputs(show, episodes, preview)

    # Validate generated XML before writing or comparing.
    ET.fromstring(generated[ROOT / "feed.xml"])
    ET.fromstring(generated[ROOT / "preview-feed.xml"])

    if args.check:
        stale = []
        for path, expected in generated.items():
            actual = path.read_text(encoding="utf-8") if path.exists() else ""
            if actual != expected:
                stale.append(str(path.relative_to(ROOT)))
        if stale:
            raise SystemExit("Generated files are stale: " + ", ".join(stale) + ". Run python3 scripts/build.py")
        print("Living Patterns canonical data and generated files are consistent.")
        return

    for path, content in generated.items():
        path.write_text(content, encoding="utf-8")
        print("wrote", path.relative_to(ROOT))

if __name__ == "__main__":
    main()
