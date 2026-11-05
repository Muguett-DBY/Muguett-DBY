"""Show only native achievements that GitHub currently displays on the profile."""
import base64
import binascii
from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import struct
import sys
import textwrap
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- earned-achievements:start -->"
END = "<!-- earned-achievements:end -->"
CARD_DIR = ROOT / "assets" / "profile" / "achievements"
MAX_PNG_BYTES = 1024 * 1024


class AchievementParser(HTMLParser):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.badges = {}

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag != "img" or attributes.get("data-hovercard-type") != "achievement":
            return
        detail = attributes.get("data-hovercard-url", "")
        match = re.fullmatch(
            rf"/users/{re.escape(self.owner)}/achievements/([a-z0-9-]+)/detail(?:\?hovercard=1)?",
            detail,
            re.I,
        )
        source = attributes.get("src", "")
        if not match or not re.fullmatch(r"https://github\.githubassets\.com/assets/[a-z0-9-]+\.png", source):
            return
        name = attributes.get("alt", "").removeprefix("Achievement: ").strip()
        if not name:
            return
        slug = match.group(1)
        tier = next((tier for tier in ("bronze", "silver", "gold") if f"-{tier}-" in source), "default")
        self.badges[slug] = {"name": name, "source": source, "tier": tier}


def render_section(owner, badges):
    if not badges:
        raise ValueError("No native achievements found; keeping the previous showcase")
    cards = []
    for slug, badge in badges.items():
        name = escape(badge["name"], quote=True)
        tier = f" ({badge['tier'].title()})" if badge["tier"] != "default" else ""
        cards.append(
            f'  <a href="https://github.com/{owner}?achievement={slug}&amp;tab=achievements">'
            f'<img src="./assets/profile/achievements/{slug}.svg" width="106" height="152" '
            f'alt="{name}{tier}, earned GitHub achievement" title="{name}{tier}" /></a>'
        )
    return (
        START + '\n<p align="center">\n' + "\n".join(cards) + '\n</p>\n'
        f'<p align="center"><sub><a href="https://github.com/{owner}?tab=achievements">'
        'Earned on GitHub</a> · Updated daily</sub></p>\n' + END
    )


def validate_png(data):
    if len(data) < 24 or len(data) > MAX_PNG_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Invalid achievement image")
    width, height = struct.unpack(">II", data[16:24])
    if not (1 <= width <= 4096 and 1 <= height <= 4096):
        raise ValueError("Invalid achievement image dimensions")
    return data


def cached_png(svg, source):
    """Reuse the embedded image only while it matches GitHub's current badge."""
    try:
        root = ET.fromstring(svg)
        ns = "{http://www.w3.org/2000/svg}"
        metadata = root.find(f"{ns}metadata")
        image = root.find(f"{ns}image")
        if metadata is None or metadata.text != source or image is None:
            return None
        href = image.get("href", "")
        prefix = "data:image/png;base64,"
        if not href.startswith(prefix):
            return None
        return validate_png(base64.b64decode(href[len(prefix):], validate=True))
    except (ET.ParseError, ValueError, binascii.Error):
        return None


def fetch_png(source):
    request = Request(source, headers={"User-Agent": "GitHub-profile-showcase"})
    with urlopen(request, timeout=30) as response:
        if response.headers.get_content_type() != "image/png":
            raise ValueError("Unexpected achievement image format")
        return validate_png(response.read(MAX_PNG_BYTES + 1))


def render_card(badge, png):
    """Render a self-contained card with the original GitHub badge artwork."""
    name = badge["name"]
    lines = textwrap.wrap(name, width=15, break_long_words=False, break_on_hyphens=False)
    first_y = 197 - (len(lines) - 1) * 12
    labels = "\n".join(
        f'    <text class="ink" x="106" y="{first_y + index * 24}" '
        f'font-size="22" font-weight="700" text-anchor="middle">{escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    tier = badge["tier"].upper() if badge["tier"] != "default" else "UNLOCKED"
    title = name + (f" ({badge['tier'].title()})" if badge["tier"] != "default" else "")
    encoded = base64.b64encode(validate_png(png)).decode("ascii")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="212" height="304" viewBox="0 0 212 304" role="img">
  <title>{escape(title)}</title>
  <metadata>{escape(badge["source"])}</metadata>
  <style>
    .surface{{fill:#f7f8fc;stroke:#e1e0ed}}.ink{{fill:#252d47}}.pill{{fill:#e2f4ee}}.mint{{fill:#247965}}.star{{fill:#a18be0}}
    @media(prefers-color-scheme:dark){{.surface{{fill:#11182b;stroke:#303950}}.ink{{fill:#f2effb}}.pill{{fill:#1d3938}}.mint{{fill:#68efd0}}.star{{fill:#bca7ff}}}}
    @media(prefers-reduced-motion:no-preference){{.twinkle{{animation:twinkle 5s ease-in-out infinite}}@keyframes twinkle{{0%,100%{{opacity:.4}}50%{{opacity:1}}}}}}
  </style>
  <rect class="surface" x="4" y="4" width="204" height="296" rx="18"/>
  <path class="star twinkle" d="m24 27 2.5 7 7 2.5-7 2.5-2.5 7-2.5-7-7-2.5 7-2.5zm164 103 2 5 5 2-5 2-2 5-2-5-5-2 5-2z"/>
  <image x="42" y="20" width="128" height="128" href="data:image/png;base64,{encoded}"/>
  <g font-family="Segoe UI,Arial,sans-serif">
{labels}
    <rect class="pill" x="42" y="249" width="128" height="33" rx="16.5"/>
    <text class="mint" x="106" y="272" text-anchor="middle" font-family="Consolas,monospace" font-size="17" font-weight="700" letter-spacing="1">{tier}</text>
  </g>
</svg>
'''


def prepare_cards(badges, directory):
    """Prepare all cards in memory before changing the published showcase."""
    cards = {}
    for slug, badge in badges.items():
        path = directory / f"{slug}.svg"
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        png = cached_png(old, badge["source"]) or fetch_png(badge["source"])
        cards[path] = render_card(badge, png)
    return cards


def replace_section(readme, section):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("Expected one achievement showcase block")
    return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: section, readme, flags=re.S)


if __name__ == "__main__":
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "Muguett-DBY")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner):
        raise ValueError("Expected a GitHub account name")
    request = Request(f"https://github.com/{owner}?tab=achievements", headers={"User-Agent": "GitHub-profile-showcase"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    parser = AchievementParser(owner)
    parser.feed(html)
    destination = ROOT / "README.md"
    updated = replace_section(destination.read_text(encoding="utf-8"), render_section(owner, parser.badges))
    try:
        cards = prepare_cards(parser.badges, CARD_DIR)
    except (OSError, ValueError) as exc:
        # A temporary image CDN failure should not stop the daily city refresh.
        print(f"Keeping the previous achievement showcase: {exc}", file=sys.stderr)
        sys.exit(0)
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    for path, svg in cards.items():
        temporary_card = path.with_suffix(".svg.tmp")
        temporary_card.write_text(svg, encoding="utf-8")
        temporary_card.replace(path)
    temporary = destination.with_suffix(".md.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(destination)
    print("Verified native achievements: " + ", ".join(badge["name"] for badge in parser.badges.values()))
