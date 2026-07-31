#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
from html import escape

USERNAME = os.environ.get("GITHUB_USERNAME", "hownameee")
TOKEN = os.environ.get("GITHUB_TOKEN", None)
HIDE_LANGS = [l.strip().lower() for l in os.environ.get("HIDE_LANGS", "jupyter notebook").split(",") if l.strip()]

# Standard GitHub Language Colors
LANGUAGE_COLORS = {
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "C++": "#f34b7d",
    "C": "#555555",
    "Python": "#3572A5",
    "CSS": "#563d7c",
    "HTML": "#e34c26",
    "Go": "#00ADD8",
    "Lua": "#000080",
    "Shell": "#89e051",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "C#": "#178600",
}

DEFAULT_COLOR = "#8be9fd"

CARD_WIDTH = 380
CARD_HEIGHT = 170
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
CARD_PADDING = 22
BAR_Y = 55
BAR_WIDTH = CARD_WIDTH - (CARD_PADDING * 2)
BAR_HEIGHT = 11
LEGEND_COLUMN_WIDTH = 160
LEGEND_COLUMN_GAP = 16


def render_shell(content):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" fill="none" role="img" aria-labelledby="title description" shape-rendering="geometricPrecision">
    <title id="title">Most Used Languages</title>
    <desc id="description">A breakdown of the programming languages used across public repositories.</desc>
    <defs>
        <clipPath id="bar-clip">
            <rect x="{CARD_PADDING}" y="{BAR_Y}" width="{BAR_WIDTH}" height="{BAR_HEIGHT}" rx="6"/>
        </clipPath>
        <style>
            text {{ font-family: {FONT_STACK}; }}
            .heading {{ fill: #ff79c6; font-size: 16px; font-weight: 700; letter-spacing: .15px; }}
            .eyebrow {{ fill: #6272a4; font-size: 8px; font-weight: 700; letter-spacing: 1.15px; }}
            .name {{ fill: #f8f8f2; font-size: 12px; font-weight: 600; }}
            .percent {{ fill: #a8adc2; font-size: 10px; font-weight: 650; }}
            .empty-title {{ fill: #f8f8f2; font-size: 12px; font-weight: 600; }}
            .empty-copy {{ fill: #6272a4; font-size: 10px; font-weight: 500; }}
        </style>
    </defs>
    <rect x=".5" y=".5" width="379" height="169" rx="10" fill="#282a36" stroke="#44475a"/>
    <circle cx="27" cy="29" r="8" fill="#ff79c6" opacity=".12"/>
    <circle cx="27" cy="29" r="4" fill="#ff79c6"/>
    <text x="42" y="34" class="heading">Most Used Languages</text>
    <text x="358" y="32" text-anchor="end" class="eyebrow">PUBLIC REPOS</text>
    {content}
</svg>\n"""


def fetch_json(url):
    headers = {"User-Agent": "Python-TopLangs-Generator"}
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_language_stats(username):
    url = f"https://api.github.com/users/{username}/repos?per_page=100"
    try:
        repos = fetch_json(url)
    except Exception as e:
        print(f"Error fetching repos for user {username}: {e}", file=sys.stderr)
        return {}

    lang_totals = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        langs_url = repo.get("languages_url")
        if not langs_url:
            continue
        try:
            langs = fetch_json(langs_url)
            for lang, byte_count in langs.items():
                if lang.lower() in HIDE_LANGS:
                    continue
                lang_totals[lang] = lang_totals.get(lang, 0) + byte_count
        except Exception as e:
            print(f"Warning: could not fetch languages for {repo.get('name')}: {e}", file=sys.stderr)

    return lang_totals


def generate_svg(lang_totals):
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)
    total_bytes = sum(b for _, b in sorted_langs)

    if total_bytes == 0:
        return render_shell("""
    <g transform="translate(22 55)">
        <rect width="336" height="82" rx="8" fill="#242630" stroke="#44475a" stroke-dasharray="3 4"/>
        <circle cx="168" cy="25" r="7" fill="#bd93f9" opacity=".12"/>
        <circle cx="168" cy="25" r="3" fill="#bd93f9"/>
        <text x="168" y="49" text-anchor="middle" class="empty-title">No language data yet</text>
        <text x="168" y="65" text-anchor="middle" class="empty-copy">The next update will try again automatically.</text>
    </g>""")

    # Take top 6 languages, combine rest into "Other" if many
    top_langs = []
    other_bytes = 0
    for idx, (lang, bytes_cnt) in enumerate(sorted_langs):
        if idx < 5:
            top_langs.append((lang, bytes_cnt))
        else:
            other_bytes += bytes_cnt

    if other_bytes > 0:
        top_langs.append(("Other", other_bytes))

    # Calculate percentages
    processed = []
    for lang, bytes_cnt in top_langs:
        pct = (bytes_cnt / total_bytes) * 100
        color = LANGUAGE_COLORS.get(lang, DEFAULT_COLOR if lang != "Other" else "#6272a4")
        processed.append({
            "name": lang,
            "pct": pct,
            "color": color
        })

    # Build stacked progress bar segments
    bar_x = CARD_PADDING
    bar_y = BAR_Y
    bar_width = BAR_WIDTH
    bar_height = BAR_HEIGHT

    segments_svg = []
    current_x = bar_x

    for item in processed:
        seg_w = (item["pct"] / 100.0) * bar_width
        color = item["color"]
        segments_svg.append(f'<rect x="{current_x:.2f}" y="{bar_y}" width="{seg_w:.2f}" height="{bar_height}" fill="{color}"/>')
        current_x += seg_w

    segments_markup = "\n            ".join(segments_svg)

    bar_svg = f"""
    <g aria-label="Language distribution bar">
        <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="6" fill="#20212b" stroke="#44475a"/>
        <g clip-path="url(#bar-clip)">
            {segments_markup}
        </g>
        <rect x="{bar_x + .5}" y="{bar_y + .5}" width="{bar_width - 1}" height="{bar_height - 1}" rx="5.5" stroke="#f8f8f2" stroke-opacity=".08"/>
    </g>
    """

    # Build 2-column legend below progress bar
    legend_items = []
    col_width = LEGEND_COLUMN_WIDTH
    start_y = 84
    row_height = 25

    for idx, item in enumerate(processed):
        col = idx % 2
        row = idx // 2
        x = CARD_PADDING + col * (col_width + LEGEND_COLUMN_GAP)
        y = start_y + row * row_height

        name = escape(item["name"])
        pct_str = f'{item["pct"]:.1f}%'
        color = item["color"]

        legend_items.append(f"""
        <g transform="translate({x}, {y})" aria-label="{name}: {pct_str}">
            <circle cx="6" cy="6" r="7" fill="{color}" opacity=".13"/>
            <circle cx="6" cy="6" r="3.5" fill="{color}"/>
            <text x="19" y="10" class="name">{name}</text>
            <rect x="116" y="-4" width="44" height="20" rx="6" fill="#303241" stroke="#44475a"/>
            <text x="138" y="10" text-anchor="middle" class="percent">{pct_str}</text>
        </g>
        """)

    return render_shell(f"""{bar_svg}
    {"".join(legend_items)}""")


def main():
    print(f"Fetching language stats for user '{USERNAME}'...")
    stats = get_language_stats(USERNAME)
    print(f"Retrieved stats for {len(stats)} languages.")
    svg = generate_svg(stats)

    os.makedirs("assets", exist_ok=True)
    out_path = os.path.join("assets", "top-langs.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Successfully generated top languages SVG at '{out_path}'.")


if __name__ == "__main__":
    main()
