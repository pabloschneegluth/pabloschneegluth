"""Genera assets/languages-dark.svg y assets/languages-light.svg
con los lenguajes más usados en tus repos (públicos y privados)."""

import json
import os
import sys
import urllib.request
from html import escape

# ---------- Configuración ----------
LIMIT = 8  # cuántos lenguajes mostrar
EXCLUDED_LANGS = {"Jupyter Notebook", "HTML", "CSS"}  # lenguajes a ignorar
EXCLUDED_REPOS = {"pabloschneegluth"}  # repos a ignorar (por nombre)
INCLUDE_ARCHIVED = True
OUT_DIR = "assets"
# -----------------------------------

QUERY = """
query($cursor: String) {
  viewer {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        isArchived
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_languages(token):
    totals, colors, cursor = {}, {}, None
    while True:
        body = json.dumps({"query": QUERY, "variables": {"cursor": cursor}}).encode()
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=body,
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as resp:
            data = json.load(resp)
        if "errors" in data:
            # No se imprimen detalles: el log de Actions es público
            sys.exit("GraphQL error (check the token scopes)")

        repos = data["data"]["viewer"]["repositories"]
        for repo in repos["nodes"]:
            if repo["name"] in EXCLUDED_REPOS:
                continue
            if repo["isArchived"] and not INCLUDE_ARCHIVED:
                continue
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name in EXCLUDED_LANGS:
                    continue
                totals[name] = totals.get(name, 0) + edge["size"]
                colors[name] = edge["node"]["color"] or "#8b949e"

        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:LIMIT]
    total = sum(size for _, size in top) or 1
    return [(name, size / total * 100, colors[name]) for name, size in top]


THEMES = {
    "dark": {"title": "#00bfff", "text": "#e6edf3", "muted": "#8b949e", "track": "#21262d"},
    "light": {"title": "#1e90ff", "text": "#1f2328", "muted": "#59636e", "track": "#eaeef2"},
}


def render(langs, theme):
    t = THEMES[theme]
    width, pad = 540, 30
    bar_y, bar_h = 62, 12
    col_w = (width - 2 * pad - 40) / 2
    rows = (len(langs) + 1) // 2
    height = bar_y + bar_h + 34 + rows * 30 - 6

    # Barra apilada
    bar_w = width - 2 * pad
    segments, x = [], pad
    for i, (name, pct, color) in enumerate(langs):
        w = bar_w * pct / 100
        segments.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{max(w, 0.5):.2f}" height="{bar_h}" fill="{color}"/>'
        )
        x += w

    # Leyenda en dos columnas
    items = []
    for i, (name, pct, color) in enumerate(langs):
        col, row = i % 2, i // 2
        ix = pad + col * (col_w + 40)
        iy = bar_y + bar_h + 38 + row * 30
        delay = 0.35 + i * 0.07
        items.append(
            f'<g class="item" style="animation-delay:{delay:.2f}s">'
            f'<circle cx="{ix + 6}" cy="{iy - 5}" r="6" fill="{color}" stroke="{t["muted"]}" stroke-opacity="0.35"/>'
            f'<text x="{ix + 22}" y="{iy}" class="name">{escape(name)}</text>'
            f'<text x="{ix + col_w}" y="{iy}" class="pct" text-anchor="end">{pct:.1f}%</text>'
            f"</g>"
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Most used languages">
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif; }}
    .title {{ font-size: 20px; font-weight: 700; fill: {t['title']}; }}
    .name {{ font-size: 14px; font-weight: 600; fill: {t['text']}; }}
    .pct {{ font-size: 13px; fill: {t['muted']}; font-variant-numeric: tabular-nums; }}
    .item {{ opacity: 0; animation: fade .5s ease-out forwards; }}
    @keyframes fade {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
  </style>
  <text x="{width / 2}" y="34" class="title" text-anchor="middle">Most Used Languages</text>
  <defs>
    <clipPath id="bar"><rect x="{pad}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}"/></clipPath>
    <clipPath id="reveal"><rect x="{pad}" y="{bar_y}" width="0" height="{bar_h}">
      <animate attributeName="width" from="0" to="{bar_w}" dur="0.9s" fill="freeze" calcMode="spline" keySplines="0.3 0 0.2 1" keyTimes="0;1"/>
    </rect></clipPath>
  </defs>
  <rect x="{pad}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="{bar_h / 2}" fill="{t['track']}"/>
  <g clip-path="url(#bar)"><g clip-path="url(#reveal)">{''.join(segments)}</g></g>
  {''.join(items)}
</svg>
"""


def main():
    if os.environ.get("SAMPLE"):
        langs = json.loads(os.environ["SAMPLE"])
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            sys.exit("GH_TOKEN is not set")
        langs = fetch_languages(token)

    os.makedirs(OUT_DIR, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT_DIR, f"languages-{theme}.svg"), "w") as f:
            f.write(render(langs, theme))
    print(f"Generated card with {len(langs)} languages")


if __name__ == "__main__":
    main()
