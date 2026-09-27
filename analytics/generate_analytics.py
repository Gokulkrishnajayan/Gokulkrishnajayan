```python
#!/usr/bin/env python3

"""
Generate self-hosted GitHub analytics SVGs.

Generated files:

    /tmp/github-stats.svg
    /tmp/top-languages.svg

The GitHub Actions workflow publishes these
files to the output branch.

No third-party Python packages are required.
"""

import json
import os
import urllib.request
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
# COLORS
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
}


# ============================================================
# GITHUB API
# ============================================================

def api_get(path, params=None):
    """
    Perform a GitHub REST API GET request.
    """

    url = API + path

    if params:
        url += "?" + urlencode(params)

    request = urllib.request.Request(
        url,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        return json.load(response)


def graphql(query, variables):
    """
    Perform a GitHub GraphQL API request.
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

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = json.load(response)

    if data.get("errors"):

        raise RuntimeError(
            json.dumps(
                data["errors"],
                indent=2
            )
        )

    return data["data"]


# ============================================================
# SVG HELPERS
# ============================================================

def esc(value):
    """
    Escape text for SVG.
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
    radius=12
):
    """
    Create SVG rectangle.
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
# DATA
# ============================================================

def get_stats():
    """
    Get GitHub contribution statistics
    for the current year.
    """

    year = datetime.now(
        timezone.utc
    ).year

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

    data = graphql(
        query,
        {
            "login": USERNAME,

            "from":
                f"{year}-01-01T00:00:00Z",

            "to":
                f"{year}-12-31T23:59:59Z"
        }
    )

    user = data["user"]

    contributions = (
        user["contributionsCollection"]
    )

    return {

        "year": year,

        "followers":
            user["followers"]["totalCount"],

        "repos":
            user["repositories"]["totalCount"],

        "contributions":
            contributions[
                "contributionCalendar"
            ]["totalContributions"],

        "commits":
            contributions[
                "totalCommitContributions"
            ],

        "prs":
            contributions[
                "totalPullRequestContributions"
            ],

        "issues":
            contributions[
                "totalIssueContributions"
            ],

        "reviews":
            contributions[
                "totalPullRequestReviewContributions"
            ],
    }


def get_languages():
    """
    Calculate language usage across
    owned, non-fork, non-archived repositories.
    """

    repositories = []

    page = 1

    while True:

        batch = api_get(
            f"/users/{USERNAME}/repos",
            {
                "per_page": 100,
                "page": page,
                "type": "owner"
            }
        )

        repositories.extend(batch)

        if len(batch) < 100:
            break

        page += 1

    languages = defaultdict(int)

    for repo in repositories:

        if repo.get("fork"):
            continue

        if repo.get("archived"):
            continue

        try:

            repo_languages = api_get(
                f"/repos/{USERNAME}/{repo['name']}/languages"
            )

            for language, amount in (
                repo_languages.items()
            ):

                languages[language] += amount

        except Exception as error:

            print(
                f"Skipping {repo['name']}: {error}"
            )

    return languages


# ============================================================
# FORMATTING
# ============================================================

def fmt(number):
    """
    Format large numbers.
    """

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"

    if number >= 1_000:
        return f"{number / 1_000:.1f}k"

    return str(number)


# ============================================================
# GITHUB ANALYTICS SVG
# ============================================================

def stats_svg(stats):

    # Designed for 3-column README layout.
    width = 500
    height = 240

    svg = [

        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),

        f'<rect '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="16" '
        f'fill="{BG}"/>',

        rect(
            1,
            1,
            width - 2,
            height - 2,
            BG,
            BORDER,
            16
        ),

        txt(
            24,
            32,
            "GitHub Analytics",
            17,
            TEXT,
            700
        ),

        txt(
            width - 24,
            32,
            str(stats["year"]),
            11,
            MUTED,
            500,
            "end"
        ),

        txt(
            24,
            52,
            "Activity this year",
            10,
            MUTED,
            400
        )
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

    card_width = 142
    card_height = 58

    positions = [

        (24, 70),
        (179, 70),
        (334, 70),

        (24, 136),
        (179, 136),
        (334, 136),
    ]

    for (
        (label, value),
        (x, y)
    ) in zip(cards, positions):

        svg.append(
            rect(
                x,
                y,
                card_width,
                card_height,
                CARD,
                BORDER,
                9
            )
        )

        svg.append(
            txt(
                x + 12,
                y + 25,
                fmt(value),
                19,
                ACCENT,
                700
            )
        )

        svg.append(
            txt(
                x + 12,
                y + 44,
                label,
                9,
                MUTED,
                500
            )
        )

    # No footer.
    svg.append("</svg>")

    return "\n".join(svg)


# ============================================================
# TOP LANGUAGES SVG
# ============================================================

def languages_svg(languages):

    # Same dimensions as analytics card.
    width = 500
    height = 240

    items = sorted(
        languages.items(),
        key=lambda item: item[1],
        reverse=True
    )[:6]

    total = sum(
        value for _, value in items
    ) or 1

    svg = [

        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" '
            f'height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),

        f'<rect '
        f'width="{width}" '
        f'height="{height}" '
        f'rx="16" '
        f'fill="{BG}"/>',

        rect(
            1,
            1,
            width - 2,
            height - 2,
            BG,
            BORDER,
            16
        ),

        txt(
            24,
            32,
            "Top Languages",
            17,
            TEXT,
            700
        ),

        txt(
            24,
            52,
            "Across my owned repositories",
            10,
            MUTED,
            400
        )
    ]

    # --------------------------------------------------------
    # LANGUAGE BAR
    # --------------------------------------------------------

    bar_x = 24
    bar_y = 68
    bar_width = 452
    bar_height = 10

    current_x = bar_x

    for language, amount in items:

        segment_width = (
            bar_width * amount / total
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

    # --------------------------------------------------------
    # LANGUAGE LIST
    # --------------------------------------------------------

    row_height = 25

    for index, (
        language,
        amount
    ) in enumerate(items):

        column = index % 2
        row = index // 2

        x = 24 + column * 226
        y = 105 + row * row_height

        percentage = (
            amount / total * 100
        )

        color = LANG_COLORS.get(
            language,
            ACCENT
        )

        svg.append(
            f'<circle '
            f'cx="{x + 5}" '
            f'cy="{y - 4}" '
            f'r="4" '
            f'fill="{color}"/>'
        )

        svg.append(
            txt(
                x + 16,
                y,
                language,
                10,
                TEXT,
                600
            )
        )

        svg.append(
            txt(
                x + 215,
                y,
                f"{percentage:.1f}%",
                9,
                MUTED,
                500,
                "end"
            )
        )

    # No footer.
    svg.append("</svg>")

    return "\n".join(svg)


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"Generating GitHub analytics "
        f"for @{USERNAME}..."
    )

    stats = get_stats()

    languages = get_languages()

    stats_path = "/tmp/github-stats.svg"

    languages_path = "/tmp/top-languages.svg"

    with open(
        stats_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            stats_svg(stats)
        )

    with open(
        languages_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            languages_svg(languages)
        )

    print("Generated:")

    print(
        f"  {stats_path}"
    )

    print(
        f"  {languages_path}"
    )


if __name__ == "__main__":
    main()
```
