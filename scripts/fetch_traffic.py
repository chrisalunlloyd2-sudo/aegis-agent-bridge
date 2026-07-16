"""
Fetch traffic data and write traffic.json.

Primary source: Cloudflare Web Analytics (GraphQL API) if secrets configured.
Fallback source: GitHub traffic API for the living-ascii-art Pages repo.

Environment variables:
  CLOUDFLARE_API_TOKEN  - Cloudflare API token
  CLOUDFLARE_ACCOUNT_ID - Cloudflare account ID
  CLOUDFLARE_SITE_TAG   - Web Analytics site tag / beacon token
  GITHUB_TOKEN          - GitHub PAT with repo read + traffic read access
  GITHUB_REPO           - owner/repo for traffic (default: chrisalunlloyd2-sudo/living-ascii-art)
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional


def load_previous(path: str) -> dict:
    if not os.path.exists(path):
        return {"page_views": 0, "history": []}
    with open(path) as f:
        return json.load(f)


def fetch_cloudflare_web_analytics(token: str, account_id: str, site_tag: str) -> Optional[int]:
    """Attempt to fetch today's page views from Cloudflare Web Analytics GraphQL."""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    query = {
        "query": """
        query WebAnalyticsSummary($accountTag: String!, $siteTag: String!, $start: Time!, $end: Time!) {
          viewer {
            accounts(filter: {accountTag: $accountTag}) {
              webAnalyticsSites(filter: {siteTag: $siteTag}) {
                summary: topHttpRequests1mGroups(limit: 1, filter: { datetime_geq: $start, datetime_leq: $end }) {
                  sum {
                    pageViews
                  }
                }
              }
            }
          }
        }
        """,
        "variables": {
            "accountTag": account_id,
            "siteTag": site_tag,
            "start": start.isoformat(),
            "end": now.isoformat(),
        },
    }
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=json.dumps(query).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("errors"):
            print(f"Cloudflare GraphQL errors: {data['errors']}")
            return None
        sites = data.get("data", {}).get("viewer", {}).get("accounts", [{}])[0].get("webAnalyticsSites", [])
        if not sites:
            return None
        totals = sites[0].get("summary", [{}])[0].get("sum", {})
        return totals.get("pageViews", 0)
    except Exception as e:
        print(f"Cloudflare fetch failed: {e}")
        return None


def fetch_github_traffic(token: str, repo: str) -> Optional[int]:
    """Fetch total repository views from GitHub traffic API (fallback)."""
    url = f"https://api.github.com/repos/{repo}/traffic/views"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "aegis-agent-bridge",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        views = data.get("count", 0)
        print(f"GitHub traffic views for {repo}: {views}")
        return views
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")[:500]
        print(f"GitHub traffic fetch failed: {e.code} {body}")
        return None
    except Exception as e:
        print(f"GitHub traffic fetch failed: {e}")
        return None


def main():
    base = os.path.dirname(os.path.dirname(__file__))
    traffic_path = os.path.join(base, "traffic.json")
    prev = load_previous(traffic_path)

    cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    cf_site_tag = os.environ.get("CLOUDFLARE_SITE_TAG")

    gh_token = os.environ.get("GITHUB_TOKEN")
    gh_repo = os.environ.get("GITHUB_REPO", "chrisalunlloyd2-sudo/living-ascii-art")

    views = None
    source = "unknown"

    # Try Cloudflare first
    if cf_token and cf_account and cf_site_tag:
        cf_views = fetch_cloudflare_web_analytics(cf_token, cf_account, cf_site_tag)
        if cf_views is not None:
            views = cf_views
            source = "cloudflare_web_analytics"

    # Fallback to GitHub traffic
    if views is None and gh_token:
        gh_views = fetch_github_traffic(gh_token, gh_repo)
        if gh_views is not None:
            views = gh_views
            source = "github_traffic"

    if views is None:
        views = prev.get("page_views", 0)
        source = prev.get("source", "fallback")

    history = prev.get("history", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if history and history[-1].get("date") == today:
        history[-1]["page_views"] = views
        history[-1]["source"] = source
    else:
        history.append({"date": today, "page_views": views, "source": source})
    history = history[-90:]

    traffic = {
        "page_views": views,
        "source": source,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "history": history,
    }

    with open(traffic_path, "w") as f:
        json.dump(traffic, f, indent=2)
    print(f"wrote {traffic_path}: {views} views (source: {source})")


if __name__ == "__main__":
    main()
