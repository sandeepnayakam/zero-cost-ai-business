#!/usr/bin/env python3
import urllib.request, json, sys, time

API_URL = "https://api.github.com/search/issues"
TERMS = ["USDC","ETH","SOL","USDT","crypto reward","paid in crypto","bounty"]

def build_query():
    return " OR ".join([f'"{term}"' for term in TERMS]) + " is:issue is:open"

def search_bounties():
    query = build_query()
    params = {"q": query, "sort": "updated", "order": "desc", "per_page": 100}
    data = urllib.request.Request(API_URL + "?" + "&".join([f"{k}={urllib.parse.quote(str(v))}" for k,v in params.items()]),
                                 headers={"Accept": "application/vnd.github+json",
                                            "User-Agent": "zero-cost-profit-research/1.0",
                                            "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urllib.request.urlopen(data, timeout=10) as resp:
            if resp.status != 200:
                print("Error", resp.status)
                return []
            return json.loads(resp.read().decode())
    except Exception as e:
        print("Exception", e)
        return []

if __name__ == "__main__":
    issues = search_bounties()
    for issue in issues:
        print(issue["html_url"])