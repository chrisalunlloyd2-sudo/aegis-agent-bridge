"""
Fetch Cloudflare Web Analytics page-view data and write traffic.json.

This script uses Cloudflare's GraphQL Analytics API for Web Analytics.
Required environment variables:
  CLOUDFLARE_API_TOKEN  - token with Analytics:Read permission
  CLOUDFLARE_ACCOUNT_ID - Cloudflare account ID
  CLOUDFLARE_SITE_TAG   - Web Analytics site tag (shown in dashboard URL)

If not configured, writes an empty traffic.json placeholder.
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional


def load_previous(path: str) -> dict:
    if not os.path.exists(path):
        return {"page_views": 0, "history": []}
    with open(path) as f:
        return json.load(f)


def fetch_cloudflare_web_analytics(token: str, account_id: str, site_tag: str) -> Optional[int]:
    """
    Use Cloudflare GraphQL Analytics API to get total page views for today.
    Returns page view count or None if unavailable.
    """
    try:
        import urllib.request
        import urllib.error
    except ImportError:
        return None

    query = {
        "query": """
        query WebAnalyticsPageViews($accountTag: String!, $siteTag: String!) {
          viewer {
            accounts(filter: { accountTag: $accountTag }) {
              webAnalyticsSites(filter: { siteTag: $siteTag }) {
                topBanners: top(deviceType: botManagement, httpProtocol: botManagement, ip: botManagement, isp: botManagement, os: botManagement, tls: botManagement, userAgent: botManagement) {
                  totals {
                    pageViews
                  }
                }
              }
            }
          }
        }
        """,
        "variables": {"accountTag": account_id, "siteTag": site_tag},
    }

    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/graphql",
        data=json.dumps(query).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        totals = data["data"]["viewer"]["accounts"][0]["webAnalyticsSites"][0]["topBanners"]["totals"]
        return totals.get("pageViews", 0)
    except Exception as e:
        print(f"Cloudflare fetch failed: {e}")
        return None


def main():
    base = os.path.dirname(os.path.dirname(__file__))
    traffic_path = os.path.join(base, "traffic.json")
    prev = load_previous(traffic_path)

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    site_tag = os.environ.get("CLOUDFLARE_SITE_TAG")

    views = None
    if token and account_id and site_tag:
        views = fetch_cloudflare_web_analytics(token, account_id, site_tag)

    if views is None:
        views = prev.get("page_views", 0)

    history = prev.get("history", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if history and history[-1].get("date") == today:
        history[-1]["page_views"] = views
    else:
        history.append({"date": today, "page_views": views})
    history = history[-90:]  # keep 90 days

    traffic = {
        "page_views": views,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "history": history,
    }

    with open(traffic_path, "w") as f:
        json.dump(traffic, f, indent=2)
    print(f"wrote {traffic_path}: {views} views")


if __name__ == "__main__":
    main()
