"""Generate GitHub stats SVG cards for the profile README.

Uses only the standard library and the GitHub GraphQL API, so it runs in
GitHub Actions with the default GITHUB_TOKEN and no third-party services.
"""

import json
import os
import urllib.request
from html import escape
from pathlib import Path

USERNAME = os.environ.get("GH_USERNAME", "LeandroColombo111")
TOKEN = os.environ["GITHUB_TOKEN"]
EXCLUDED_LANGUAGES = {"Jupyter Notebook"}
OUT_DIR = Path(__file__).resolve().parent.parent / "stats"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

BG = "#0d1117"
BORDER = "#30363d"
TITLE = "#58a6ff"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
FONT = "font-family:'Segoe UI',Ubuntu,Helvetica,Arial,sans-serif"


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    return payload["data"]["user"]


def card(width, height, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" '
        f'fill="{BG}" stroke="{BORDER}"/>'
        f'<text x="24" y="36" fill="{TITLE}" style="{FONT};font-size:17px;font-weight:600">'
        f"{escape(title)}</text>{body}</svg>"
    )


def stats_card(user):
    contrib = user["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    rows = [
        ("Contributions (last year)", contrib["contributionCalendar"]["totalContributions"]),
        ("Commits (last year)", contrib["totalCommitContributions"] + contrib["restrictedContributionsCount"]),
        ("Pull requests (last year)", contrib["totalPullRequestContributions"]),
        ("Public repositories", user["repositories"]["totalCount"]),
        ("Stars earned", stars),
    ]
    body = ""
    for i, (label, value) in enumerate(rows):
        y = 70 + i * 26
        body += (
            f'<text x="24" y="{y}" fill="{TEXT}" style="{FONT};font-size:14px">{escape(label)}</text>'
            f'<text x="376" y="{y}" fill="{TEXT}" text-anchor="end" '
            f'style="{FONT};font-size:14px;font-weight:600">{value:,}</text>'
        )
    return card(400, 70 + len(rows) * 26, "GitHub Stats", body)


def languages_card(user, top=6):
    totals, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in EXCLUDED_LANGUAGES:
                continue
            totals[name] = totals.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or MUTED
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top]
    grand = sum(size for _, size in ranked) or 1

    bar, x = "", 24
    for name, size in ranked:
        w = 352 * size / grand
        bar += f'<rect x="{x:.2f}" y="54" width="{w:.2f}" height="10" fill="{colors[name]}"/>'
        x += w
    body = f'<clipPath id="c"><rect x="24" y="54" width="352" height="10" rx="5"/></clipPath><g clip-path="url(#c)">{bar}</g>'

    for i, (name, size) in enumerate(ranked):
        col, row = i % 2, i // 2
        cx, cy = 24 + col * 180, 92 + row * 24
        body += (
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{colors[name]}"/>'
            f'<text x="{cx + 16}" y="{cy}" fill="{TEXT}" style="{FONT};font-size:13px">'
            f'{escape(name)} <tspan fill="{MUTED}">{100 * size / grand:.1f}%</tspan></text>'
        )
    return card(400, 92 + ((len(ranked) + 1) // 2) * 24, "Top Languages", body)


def main():
    user = fetch()
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "stats.svg").write_text(stats_card(user))
    (OUT_DIR / "top-langs.svg").write_text(languages_card(user))


if __name__ == "__main__":
    main()
