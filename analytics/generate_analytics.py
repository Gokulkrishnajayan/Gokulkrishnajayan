#!/usr/bin/env python3

"""
Self-hosted GitHub Analytics Generator

Generates:
    output/github-stats.svg
    output/top-languages.svg

No Vercel.
No github-readme-stats.
No third-party Python packages.
Only GitHub's API + GitHub Actions.
"""

import json
import os
import urllib.request
import urllib.error

from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.environ["GITHUB_TOKEN"]

USERNAME = os.environ.get(
    "GITHUB_USERNAME",
    "Gokulkrishnajayan"
)

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Gokulkrishnajayan-github-analytics",
}


# ============================================================
# DESIGN
# ============================================================

BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"

TEXT = "#f0f6fc"
MUTED = "#8b949e"

ACCENT = "#36BCF7"


LANG_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "PHP": "#4F5D95",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
    "Kotlin": "#A97BFF",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "Vue": "#41b883",
    "Jupyter Notebook": "#DA5B0B",
    "Swift": "#F05138",
    "C#": "#178600",
    "SCSS": "#c6538c",
    "Less": "#1d365d",
    "Dockerfile": "#384d54",
}


# ============================================================
# GITHUB REST API
# ============================================================

def api_get(path, params=None):
    """
    Perform a GET request against GitHub's REST API.
    """

    url = API + path

    if params:
        url += "?" + urlencode(params)

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        raise RuntimeError(
            f"GitHub API request failed: "
            f"{error.code} {error.reason}\n{body}"
        )


# ============================================================
# GITHUB GRAPHQL API
# ============================================================

def graphql(query, variables):
    """
    Execute a GitHub GraphQL query.
    """

    body = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        GRAPHQL,
        data=body,
        headers={
            **HEADERS,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        raise RuntimeError(
            f"GitHub GraphQL request failed: "
            f"{error.code} {error.reason}\n{body}"
        )

    if data.get("errors"):
        raise RuntimeError(
            "GitHub GraphQL error:\n"
            + json.dumps(data["errors"], indent=2)
        )

    return data["data"]


# ============================================================
# SVG HELPERS
# ============================================================

def esc(value):
    """
    Escape text for safe SVG/XML output.
    """

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def txt(
    x,
    y,
    text,
    size=14,
    fill=TEXT,
    weight=400,
    anchor="start"
):
    """
    Create SVG text.
    """

    return (
        f'<text '
        f'x="{x}" '
        f'y="{y}" '
        f'font-family="Inter,Segoe UI,Arial,sans-serif" '
        f'font-size="{size}" '
        f'font-weight="{weight}" '
        f'fill="{fill}" '
        f'text-anchor="{anchor}">'
        f'{esc(text)}'
        f'</text>'
    )


def rect(
    x,
    y,
    width,
    height,
    fill=CARD,
    stroke=BORDER,
    radius=14
):
    """
    Create SVG rounded rectangle.
    """

    return (
        f'<rect '
        f'x="{x}" '
        f'y="{y}" '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="{radius}" '
        f'fill="{fill}" '
        f'stroke="{stroke}"/>'
    )


# ============================================================
# NUMBER FORMAT
# ============================================================

def fmt(number):
    """
    Format large numbers in a compact way.
    """

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"

    if number >= 1_000:
        return f"{number / 1_000:.1f}k"

    return str(number)


# ============================================================
# GET GITHUB STATISTICS
# ============================================================

def get_stats():

    year = datetime.now(timezone.utc).year

    """
    IMPORTANT:

    totalContributions is NOT directly available on
    ContributionsCollection.

    Correct path:

        contributionsCollection
            └── contributionCalendar
                    └── totalContributions
    """

    query = """
    query(
        $login: String!,
        $from: DateTime!,
        $to: DateTime!
    ) {

        user(login: $login) {

            followers {
                totalCount
            }

            repositories(
                ownerAffiliations: OWNER
                first: 1
            ) {
                totalCount
            }

            contributionsCollection(
                from: $from
                to: $to
            ) {

                contributionCalendar {
                    totalContributions
                }

                totalCommitContributions

                totalIssueContributions

                totalPullRequestContributions

                totalPullRequestReviewContributions
            }
        }
    }
    """

    variables = {
        "login": USERNAME,
        "from": f"{year}-01-01T00:00:00Z",
        "to": f"{year}-12-31T23:59:59Z"
    }

    data = graphql(query, variables)

    user = data["user"]

    contributions = user["contributionsCollection"]

    return {
        "year": year,

        "followers": (
            user["followers"]["totalCount"]
        ),

        "repos": (
            user["repositories"]["totalCount"]
        ),

        "contributions": (
            contributions[
                "contributionCalendar"
            ]["totalContributions"]
        ),

        "commits": (
            contributions[
                "totalCommitContributions"
            ]
        ),

        "prs": (
            contributions[
                "totalPullRequestContributions"
            ]
        ),

        "issues": (
            contributions[
                "totalIssueContributions"
            ]
        ),

        "reviews": (
            contributions[
                "totalPullRequestReviewContributions"
            ]
        ),
    }


# ============================================================
# GET LANGUAGES
# ============================================================

def get_languages():

    repositories = []

    page = 1

    while True:

        batch = api_get(
            f"/users/{USERNAME}/repos",
            {
                "per_page": 100,
                "page": page,
                "type": "owner",
                "sort": "updated"
            }
        )

        if not batch:
            break

        repositories.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    languages = defaultdict(int)

    print(
        f"Found {len(repositories)} repositories."
    )

    for repo in repositories:

        name = repo.get("name")

        # Ignore forks
        if repo.get("fork"):
            continue

        # Ignore archived repositories
        if repo.get("archived"):
            continue

        try:

            language_data = api_get(
                f"/repos/{USERNAME}/{name}/languages"
            )

            for language, bytes_count in language_data.items():

                languages[language] += bytes_count

        except Exception as error:

            print(
                f"Skipping {name}: {error}"
            )

    return languages


# ============================================================
# GITHUB STATS SVG
# ============================================================

def stats_svg(stats):

    width = 760
    height = 300

    svg = [

        f'<svg '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" '
        f'height="{height}" '
        f'viewBox="0 0 {width} {height}">',

        # Background
        f'<rect '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="16" '
        f'fill="{BG}"/>',

        # Card border
        rect(
            1,
            1,
            width - 2,
            height - 2
        ),

        # Title
        txt(
            28,
            38,
            "GitHub Analytics",
            18,
            TEXT,
            700
        ),

        # Year
        txt(
            width - 28,
            38,
            str(stats["year"]),
            12,
            MUTED,
            500,
            "end"
        ),

        # Subtitle
        txt(
            28,
            60,
            "Self-hosted from GitHub API • updated by GitHub Actions",
            11,
            MUTED
        ),
    ]

    cards = [

        (
            "Contributions",
            stats["contributions"]
        ),

        (
            "Commits",
            stats["commits"]
        ),

        (
            "Pull Requests",
            stats["prs"]
        ),

        (
            "Issues",
            stats["issues"]
        ),

        (
            "Repositories",
            stats["repos"]
        ),

        (
            "Followers",
            stats["followers"]
        ),
    ]

    for index, (label, value) in enumerate(cards):

        column = index % 3
        row = index // 3

        x = 28 + column * 244
        y = 82 + row * 88

        svg.append(
            rect(
                x,
                y,
                216,
                68,
                BG,
                BORDER,
                10
            )
        )

        svg.append(
            txt(
                x + 16,
                y + 30,
                fmt(value),
                23,
                ACCENT,
                700
            )
        )

        svg.append(
            txt(
                x + 16,
                y + 51,
                label,
                11,
                MUTED,
                500
            )
        )

    # Footer
    svg.append(
        txt(
            28,
            270,
            f"@{USERNAME}",
            11,
            MUTED,
            500
        )
    )

    svg.append(
        txt(
            width - 28,
            270,
            "Generated in my repository",
            11,
            MUTED,
            400,
            "end"
        )
    )

    svg.append("</svg>")

    return "\n".join(svg)


# ============================================================
# TOP LANGUAGES SVG
# ============================================================

def languages_svg(languages):

    # Top 8 languages
    items = sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True
    )[:8]

    total = sum(
        value for _, value in items
    ) or 1

    width = 760
    height = 300

    svg = [

        f'<svg '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" '
        f'height="{height}" '
        f'viewBox="0 0 {width} {height}">',

        # Background
        f'<rect '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="16" '
        f'fill="{BG}"/>',

        # Border
        rect(
            1,
            1,
            width - 2,
            height - 2
        ),

        # Title
        txt(
            28,
            38,
            "Top Languages",
            18,
            TEXT,
            700
        ),

        # Subtitle
        txt(
            28,
            60,
            "Across my owned, non-fork repositories",
            11,
            MUTED
        ),
    ]

    # ========================================================
    # LANGUAGE BAR
    # ========================================================

    bar_x = 28
    bar_y = 82
    bar_width = 704
    bar_height = 12

    current_x = bar_x

    for language, amount in items:

        segment_width = (
            bar_width *
            amount /
            total
        )

        color = LANG_COLORS.get(
            language,
            ACCENT
        )

        svg.append(
            f'<rect '
            f'x="{current_x:.2f}" '
            f'y="{bar_y}" '
            f'width="{max(segment_width, 2):.2f}" '
            f'height="{bar_height}" '
            f'fill="{color}"/>'
        )

        current_x += segment_width

    # ========================================================
    # LANGUAGE LIST
    # ========================================================

    for index, (language, amount) in enumerate(items):

        column = index % 2
        row = index // 2

        x = 28 + column * 352
        y = 125 + row * 38

        percentage = (
            amount /
            total *
            100
        )

        color = LANG_COLORS.get(
            language,
            ACCENT
        )

        # Dot
        svg.append(
            f'<circle '
            f'cx="{x + 6}" '
            f'cy="{y - 4}" '
            f'r="5" '
            f'fill="{color}"/>'
        )

        # Language
        svg.append(
            txt(
                x + 20,
                y,
                language,
                12,
                TEXT,
                600
            )
        )

        # Percentage
        svg.append(
            txt(
                x + 320,
                y,
                f"{percentage:.1f}%",
                11,
                MUTED,
                500,
                "end"
            )
        )

    # Footer
    svg.append(
        txt(
            28,
            270,
            f"@{USERNAME}",
            11,
            MUTED,
            500
        )
    )

    svg.append(
        txt(
            width - 28,
            270,
            "Generated in my repository",
            11,
            MUTED,
            400,
            "end"
        )
    )

    svg.append("</svg>")

    return "\n".join(svg)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("Self-hosted GitHub Analytics")
    print(f"Username: {USERNAME}")
    print("=" * 60)

    # Create output directory
    os.makedirs(
        "output",
        exist_ok=True
    )

    # --------------------------------------------------------
    # GitHub statistics
    # --------------------------------------------------------

    print("\nFetching GitHub statistics...")

    stats = get_stats()

    print(
        f"Contributions: {stats['contributions']}"
    )

    print(
        f"Commits:       {stats['commits']}"
    )

    print(
        f"Pull Requests: {stats['prs']}"
    )

    print(
        f"Issues:        {stats['issues']}"
    )

    print(
        f"Repositories:  {stats['repos']}"
    )

    print(
        f"Followers:     {stats['followers']}"
    )

    # --------------------------------------------------------
    # Languages
    # --------------------------------------------------------

    print("\nFetching repository languages...")

    languages = get_languages()

    print(
        f"Languages found: {len(languages)}"
    )

    # --------------------------------------------------------
    # Generate stats SVG
    # --------------------------------------------------------

    stats_path = (
        "output/github-stats.svg"
    )

    with open(
        stats_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            stats_svg(stats)
        )

    print(
        f"\nCreated: {stats_path}"
    )

    # --------------------------------------------------------
    # Generate languages SVG
    # --------------------------------------------------------

    languages_path = (
        "output/top-languages.svg"
    )

    with open(
        languages_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            languages_svg(languages)
        )

    print(
        f"Created: {languages_path}"
    )

    print("\nAnalytics generation completed successfully.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
