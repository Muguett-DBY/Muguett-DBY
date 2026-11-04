"""Render the profile's responsive project cards from its local preview images."""

import base64
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "assets" / "projects"
OUTPUT = PROJECTS / "cards"

CARDS = (
    ("hireway", "01", "CAREER EXPLORATION", "HireWay",
     "Australian careers, starting with your education and skills.",
     "hireway-home.png", "#71e7c9"),
    ("photography", "02", "CREATIVE SPACE", "Naihuangbao Photography",
     "A home for portraits, galleries, and booking information.",
     "photography-home.png", "#ffcf9c"),
    ("custard-web", "03", "PERSONAL WEBSITE", "Custard Web",
     "My work, engineering notes, and experiments in one home.",
     "custard-work.png", "#c8b6ff"),
    ("veilreach", "04", "LITTLE WORLDS", "Veilreach",
     "A Minecraft world of silver fog and moonlit ruins.",
     "veilreach-world.svg", "#9fc9ff"),
)

STYLE = """
  <style>
    .card { fill: #111a2e; stroke: #34415d; }
    .title { fill: #f2f1ff; font: 700 40px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    .body { fill: #bfcce0; font: 22px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    .label { font: 700 15px ui-monospace, monospace; letter-spacing: 2px; }
    .meta { fill: #899ab7; font: 700 14px ui-monospace, monospace; letter-spacing: 2px; }
    .frame { fill: #1a263d; stroke: #43526d; }
    @media (prefers-color-scheme: light) {
      .card { fill: #f7f9ff; stroke: #d6deed; }
      .title { fill: #17223b; }
      .body { fill: #475975; }
      .label { fill: #355576; }
      .meta { fill: #697c99; }
      .frame { fill: #e9eff8; stroke: #cad5e6; }
    }
  </style>"""


def image_data(filename: str) -> str:
    image = (PROJECTS / filename).read_bytes()
    if image.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif image.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif image.startswith(b"<svg"):
        mime = "image/svg+xml"
    else:
        raise ValueError(f"Unexpected preview image format: {filename}")
    encoded = base64.b64encode(image).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def card_svg(item: tuple[str, ...], mobile: bool) -> str:
    _, number, category, title, description, filename, accent = item
    data = image_data(filename)
    w, h = (720, 590) if mobile else (1200, 278)
    image_x, image_y, image_w, image_h = (32, 197, 656, 369) if mobile else (770, 29, 392, 220)
    title_size = 39 if mobile and len(title) > 19 else 44 if mobile else 40
    lines = textwrap.wrap(description, 47 if mobile else 57)
    body = "".join(
        f'<text class="body" x="{34 if mobile else 45}" y="{151 + i * 31}">{escape(line)}</text>'
        for i, line in enumerate(lines)
    )
    meta = "" if mobile else f'  <text class="meta" x="45" y="232">PROJECT {number} / CUSTARD WORKSHOP</text>\n'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
  <title>{escape(title)}</title>
  <desc>{escape(description)}</desc>
{STYLE.strip()}
  <rect class="card" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="24" />
  <circle cx="45" cy="42" r="5" fill="{accent}" />
  <text class="label" x="62" y="47" fill="{accent}">{escape(category)}</text>
  <text class="title" style="font-size:{title_size}px" x="{34 if mobile else 45}" y="{103 if mobile else 105}">{escape(title)}</text>
  {body}
{meta}  <defs><clipPath id="preview"><rect x="{image_x}" y="{image_y}" width="{image_w}" height="{image_h}" rx="10" /></clipPath></defs>
  <rect class="frame" x="{image_x - 2}" y="{image_y - 2}" width="{image_w + 4}" height="{image_h + 4}" rx="12" />
  <image href="{data}" x="{image_x}" y="{image_y}" width="{image_w}" height="{image_h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#preview)" />
</svg>
'''


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for item in CARDS:
        for mobile in (False, True):
            suffix = "-mobile" if mobile else ""
            (OUTPUT / f"{item[0]}{suffix}.svg").write_text(card_svg(item, mobile), encoding="utf-8", newline="\n")
