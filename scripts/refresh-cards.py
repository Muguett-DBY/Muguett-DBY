"""Refresh checked SVG snapshots. Requires only the Python standard library."""
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime
from zoneinfo import ZoneInfo
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = {
    'username': 'Muguett-DBY', 'bg_color': '11182b', 'title_color': '68efd0',
    'text_color': 'd0ccdf', 'icon_color': 'bca7ff', 'hide_border': 'true',
    'border_radius': '12', 'disable_animations': 'true',
}
URLS = {
    'github-stats.svg': 'https://github-readme-stats.vercel.app/api?' + urlencode(BASE | {
        'show_icons': 'true', 'hide_rank': 'true', 'hide': 'issues,contribs',
        'custom_title': 'My GitHub workshop', 'card_width': '460',
    }),
    'top-languages.svg': 'https://github-readme-stats.vercel.app/api/top-langs/?' + urlencode(BASE | {
        'layout': 'compact', 'langs_count': '6', 'card_width': '460',
        'custom_title': 'Languages across my repos',
    }),
    'capsule-footer.svg': 'https://capsule-render.vercel.app/api?' + urlencode({
        'type': 'waving', 'color': '0:68efd0,50:8075ca,100:bca7ff', 'height': '140',
        'section': 'footer', 'text': 'See you in the next little world.', 'fontSize': '22',
        'fontColor': '0b1020', 'fontAlignY': '77',
    }),
}

pending = {}
for name, url in URLS.items():
    with urlopen(Request(url, headers={'User-Agent': 'Custard-GitHub-profile'}), timeout=45) as response:
        data = response.read()
    doc = ET.fromstring(data)
    if doc.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError(f'{name}: expected SVG')
    visible = ' '.join(' '.join(e.itertext()) for e in doc.iter() if e.tag.rsplit('}', 1)[-1] in ('text', 'title', 'desc'))
    if re.search(r'something went wrong|rate limit|could not fetch|bad credentials|user not found', visible, re.I):
        raise ValueError(f'{name}: service returned an error card')
    if any(e.tag.rsplit('}', 1)[-1] in ('script', 'foreignObject') for e in doc.iter()):
        raise ValueError(f'{name}: unsupported active SVG content')
    pending[name] = data

# Publish files only after every response is valid; a failed refresh keeps old cards.
for name, data in pending.items():
    (ROOT / 'assets' / name).write_bytes(data)
    print(f'{name}: {len(data)} bytes')
date = datetime.now(ZoneInfo('Australia/Sydney')).date().isoformat()
readme = ROOT / 'README.md'
text = readme.read_text(encoding='utf-8')
text = re.sub(r'<!-- cards-date -->.*?<!-- /cards-date -->', f'<!-- cards-date -->{date}<!-- /cards-date -->', text)
readme.write_text(text, encoding='utf-8')
