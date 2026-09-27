#!/usr/bin/env python3
"""Generate self-hosted GitHub analytics SVGs using only GitHub's API.
No Vercel, no stats image service, and no third-party Python packages.
"""
import json, os, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ.get("GITHUB_USERNAME", "Gokulkrishnajayan")
API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "Gokulkrishnajayan-github-analytics",
}
BG, CARD, BORDER = "#0d1117", "#161b22", "#30363d"
TEXT, MUTED, ACCENT = "#f0f6fc", "#8b949e", "#36BCF7"
LANG_COLORS = {
    "JavaScript":"#f1e05a", "TypeScript":"#3178c6", "Python":"#3572A5",
    "HTML":"#e34c26", "CSS":"#563d7c", "C++":"#f34b7d", "C":"#555555",
    "Java":"#b07219", "PHP":"#4F5D95", "Shell":"#89e051", "Dart":"#00B4AB",
    "Kotlin":"#A97BFF", "Go":"#00ADD8", "Rust":"#dea584", "Ruby":"#701516",
    "Vue":"#41b883", "Jupyter Notebook":"#DA5B0B"
}

def api_get(path, params=None):
    url = API + path + (("?" + urlencode(params)) if params else "")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def graphql(query, variables):
    body = json.dumps({"query":query,"variables":variables}).encode()
    req = urllib.request.Request(GRAPHQL, data=body, headers={**HEADERS,"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r: data=json.load(r)
    if data.get("errors"): raise RuntimeError(json.dumps(data["errors"]))
    return data["data"]

def esc(v):
    return str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&apos;")

def txt(x,y,s,size=14,fill=TEXT,weight=400,anchor="start"):
    return f'<text x="{x}" y="{y}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>'

def rect(x,y,w,h,fill=CARD,stroke=BORDER,r=14):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'

def get_stats():
    year=datetime.now(timezone.utc).year
    q='''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){followers{totalCount} repositories(ownerAffiliations:OWNER,first:1){totalCount} contributionsCollection(from:$from,to:$to){totalContributions totalCommitContributions totalIssueContributions totalPullRequestContributions totalPullRequestReviewContributions}}}'''
    u=graphql(q,{"login":USERNAME,"from":f"{year}-01-01T00:00:00Z","to":f"{year}-12-31T23:59:59Z"})["user"]
    c=u["contributionsCollection"]
    return {"year":year,"followers":u["followers"]["totalCount"],"repos":u["repositories"]["totalCount"],"contributions":c["totalContributions"],"commits":c["totalCommitContributions"],"prs":c["totalPullRequestContributions"],"issues":c["totalIssueContributions"],"reviews":c["totalPullRequestReviewContributions"]}

def get_languages():
    repos=[]; page=1
    while True:
        batch=api_get(f"/users/{USERNAME}/repos",{"per_page":100,"page":page,"type":"owner"})
        repos += batch
        if len(batch)<100: break
        page += 1
    langs=defaultdict(int)
    for repo in repos:
        if repo.get("fork") or repo.get("archived"): continue
        try:
            for lang,n in api_get(f"/repos/{USERNAME}/{repo['name']}/languages").items(): langs[lang]+=n
        except Exception as e: print(f"Skipping {repo['name']}: {e}")
    return langs

def fmt(n):
    if n>=1_000_000:return f"{n/1_000_000:.1f}M"
    if n>=1_000:return f"{n/1_000:.1f}k"
    return str(n)

def stats_svg(s):
    w,h=760,300; a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/>',rect(1,1,w-2,h-2),txt(28,38,"GitHub Analytics",18,TEXT,700),txt(w-28,38,str(s["year"]),12,MUTED,500,"end"),txt(28,60,"Self-hosted from GitHub API • updated by GitHub Actions",11,MUTED)]
    cards=[("Contributions",s["contributions"]),("Commits",s["commits"]),("Pull Requests",s["prs"]),("Issues",s["issues"]),("Repositories",s["repos"]),("Followers",s["followers"])]
    for i,(label,val) in enumerate(cards):
        x=28+(i%3)*244; y=82+(i//3)*88
        a += [rect(x,y,216,68,BG,BORDER,10),txt(x+16,y+30,fmt(val),23,ACCENT,700),txt(x+16,y+51,label,11,MUTED,500)]
    a += [txt(28,270,f"@{USERNAME}",11,MUTED,500),txt(w-28,270,"Generated in my repository",11,MUTED,400,"end"),"</svg>"]
    return "\n".join(a)

def languages_svg(langs):
    items=sorted(langs.items(),key=lambda x:x[1],reverse=True)[:8]; total=sum(v for _,v in items) or 1
    w,h=760,300; a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/>',rect(1,1,w-2,h-2),txt(28,38,"Top Languages",18,TEXT,700),txt(28,60,"Across my owned, non-fork repositories",11,MUTED)]
    x0,y0,bw=28,82,704; cur=x0
    for lang,n in items:
        width=bw*n/total; a.append(f'<rect x="{cur:.2f}" y="{y0}" width="{max(width,2):.2f}" height="12" fill="{LANG_COLORS.get(lang,ACCENT)}"/>'); cur+=width
    for i,(lang,n) in enumerate(items):
        col,row=i%2,i//2; x=28+col*352; y=125+row*38; pct=n/total*100; color=LANG_COLORS.get(lang,ACCENT)
        a += [f'<circle cx="{x+6}" cy="{y-4}" r="5" fill="{color}"/>',txt(x+20,y,lang,12,TEXT,600),txt(x+320,y,f"{pct:.1f}%",11,MUTED,500,"end")]
    a += [txt(28,270,f"@{USERNAME}",11,MUTED,500),txt(w-28,270,"Generated in my repository",11,MUTED,400,"end"),"</svg>"]
    return "\n".join(a)

def main():
    os.makedirs("output",exist_ok=True)
    with open("output/github-stats.svg","w",encoding="utf-8") as f:f.write(stats_svg(get_stats()))
    with open("output/top-languages.svg","w",encoding="utf-8") as f:f.write(languages_svg(get_languages()))
    print("Generated self-hosted analytics SVGs.")

if __name__=="__main__": main()
