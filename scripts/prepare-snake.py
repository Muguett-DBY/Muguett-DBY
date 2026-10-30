"""Validate both snake themes and respect reduced-motion preferences."""
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
RULE = "@media(prefers-reduced-motion:reduce){.c,.s,.u{animation:none!important}}"

for name in ("contribution-snake.svg", "contribution-snake-light.svg"):
    path = ROOT / "assets" / name
    source = path.read_text(encoding="utf-8")
    if len(source.encode("utf-8")) > 5 * 1024 * 1024:
        raise ValueError(f"{name}: image is too large")
    node = ET.fromstring(source)
    if node.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError(f"{name}: expected an SVG image")
    if any(e.tag.rsplit("}", 1)[-1] in {"script", "foreignObject"} for e in node.iter()):
        raise ValueError(f"{name}: unsupported active SVG content")
    if RULE not in source:
        if source.count("</style>") != 1:
            raise ValueError(f"{name}: expected one generated stylesheet")
        source = source.replace("</style>", RULE + "</style>")
        path.write_text(source, encoding="utf-8")
    print(f"{name}: valid; reduced motion supported")
