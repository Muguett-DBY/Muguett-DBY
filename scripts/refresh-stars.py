"""Render a local star counter from GitHub's public repository counts."""
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def fetch_stars(owner):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner):
        raise ValueError("Expected a GitHub account name")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Custard-GitHub-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    total = repositories = 0
    page = 1
    while True:
        query = urlencode({"type": "owner", "per_page": 100, "page": page})
        request = Request(f"https://api.github.com/users/{owner}/repos?{query}", headers=headers)
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
        if not isinstance(data, list):
            raise ValueError("GitHub did not return a repository list")
        for repository in data:
            if repository["private"] or repository["owner"]["login"].casefold() != owner.casefold():
                continue
            stars = repository["stargazers_count"]
            if type(stars) is not int or stars < 0:
                raise ValueError("GitHub returned an invalid star count")
            total += stars
            repositories += 1
        if len(data) < 100:
            return total, repositories
        page += 1


def render_badge(owner, total, repositories):
    count = f"{total:,}"
    value_width = max(72, 28 + len(count) * 10)
    width = 164 + value_width
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="38" viewBox="0 0 {width} 38" role="img" aria-labelledby="title description">
  <title id="title">Total stars received: {count}</title>
  <desc id="description">{escape(owner)} has received {count} stars across {repositories} public repositories. Includes archived repositories and forks. Updated daily from GitHub.</desc>
  <defs><clipPath id="rounded"><rect width="{width}" height="38" rx="12"/></clipPath></defs>
  <g clip-path="url(#rounded)">
    <rect width="{width}" height="38" fill="#11182b"/>
    <rect x="164" width="{value_width}" height="38" fill="#68efd0"/>
  </g>
  <path d="m24 10 2.8 5.7 6.3.9-4.5 4.4 1 6.2-5.6-3-5.6 3 1-6.2-4.5-4.4 6.3-.9z" fill="#bca7ff"/>
  <g font-family="Segoe UI,Arial,sans-serif" font-weight="700">
    <text x="44" y="24" fill="#d0ccdf" font-size="12" letter-spacing="1">TOTAL STARS</text>
    <text x="{164 + value_width / 2:g}" y="25" fill="#11182b" font-size="17" text-anchor="middle">{count}</text>
  </g>
</svg>
'''


if __name__ == "__main__":
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "Muguett-DBY")
    total, repositories = fetch_stars(owner)
    badge = render_badge(owner, total, repositories)
    ET.fromstring(badge)
    # Keep the previous badge intact if GitHub is unavailable or validation fails.
    destination = ROOT / "assets" / "total-stars.svg"
    temporary = destination.with_suffix(".svg.tmp")
    temporary.write_text(badge, encoding="utf-8")
    temporary.replace(destination)
    print(f"{owner}: {total} stars across {repositories} public repositories")
