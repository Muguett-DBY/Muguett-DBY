"""Show only native achievements that GitHub currently displays on the profile."""
from html import escape
from html.parser import HTMLParser
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- earned-achievements:start -->"
END = "<!-- earned-achievements:end -->"


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
    images = []
    for slug, badge in badges.items():
        name = escape(badge["name"], quote=True)
        tier = f" ({badge['tier'].title()})" if badge["tier"] != "default" else ""
        images.append(
            f'  <a href="https://github.com/{owner}?achievement={slug}&amp;tab=achievements">'
            f'<img src="{badge["source"]}" width="80" height="80" alt="{name}{tier}" title="{name}{tier}" /></a>'
        )
    return (
        START + '\n<p align="center">\n' + "\n".join(images) + '\n</p>\n'
        f'<p align="center"><sub><a href="https://github.com/{owner}?tab=achievements">'
        'Earned on GitHub</a> · Updated daily</sub></p>\n' + END
    )


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
    temporary = destination.with_suffix(".md.tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(destination)
    print("Verified native achievements: " + ", ".join(badge["name"] for badge in parser.badges.values()))
