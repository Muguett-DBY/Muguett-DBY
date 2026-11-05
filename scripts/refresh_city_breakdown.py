"""Keep the readable activity breakdown in sync with the contribution city."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- city-breakdown:start -->"
END = "<!-- city-breakdown:end -->"
FIELDS = (
    ("Commit", "commits"),
    ("Issue", "issues opened"),
    ("PullReq", "PRs opened"),
    ("Review", "reviews"),
    ("Repo", "repos created"),
)


def extract_counts(root: ET.Element) -> dict[str, int]:
    """Read the values the upstream generator puts in its radar tooltips."""
    counts = {}
    expected = {key for key, _ in FIELDS}
    for axis in root.findall('.//{*}g[@class="axis"]'):
        label = axis.find("{*}text")
        if label is None or label.text not in expected:
            continue
        title = label.find("{*}title")
        value = title.text if title is not None else None
        if label.text in counts or value is None or not re.fullmatch(r"[0-9]+", value):
            raise ValueError(f"Invalid radar value for {label.text}")
        counts[label.text] = int(value)
    if set(counts) != expected:
        raise ValueError("The city radar does not contain all expected activity values")
    return counts


def render_block(counts: dict[str, int] | None) -> str:
    if counts is None:
        content = '  <sub>Activity breakdown unavailable for this snapshot.</sub>'
    else:
        content = " ·\n".join(
            f"  <strong>{counts[key]:,}</strong>&nbsp;{label.replace(' ', '&nbsp;')}"
            for key, label in FIELDS
        )
    return f'{START}\n<p align="center">\n{content}\n</p>\n{END}'


def replace_block(readme: str, block: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("Expected exactly one activity-breakdown block")
    start, end = readme.index(START), readme.index(END) + len(END)
    if end <= start:
        raise ValueError("Activity-breakdown markers are out of order")
    return readme[:start] + block + readme[end:]


def main() -> None:
    city = ET.parse(ROOT / "profile-3d-contrib" / "custard-city.svg").getroot()
    try:
        counts = extract_counts(city)
    except ValueError as error:
        # The city remains useful if the upstream SVG layout ever changes.
        # Avoid publishing old values with the date of a new snapshot.
        print(f"Activity breakdown unavailable: {error}", file=sys.stderr)
        counts = None
    readme = ROOT / "README.md"
    updated = replace_block(readme.read_text(encoding="utf-8"), render_block(counts))
    readme.write_text(updated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
