#!/usr/bin/env python3
"""Search GitHub issues for crypto bounty opportunities - simplified queries."""
import urllib.request, urllib.parse, json, sys, time

API_URL = "https://api.github.com/search/issues"

QUERIES = [
    'label:bounty is:issue is:open',
    'label:crypto is:issue is:open',
    'label:USDC is:issue is:open',
    'label:ETH is:issue is:open',
    'label:SOL is:issue is:open',
    'label:USDT is:issue is:open',
    'label:reward is:issue is:open',
    'label:bounty is:issue is:open',
    'label:gitcoin is:issue is:open',
    'label:web3 is:issue is:open',
    'label:blockchain is:issue is:open',
    'label:solana is:issue is:open',
    'label:ethereum is:issue is:open',
    'label:defi is:issue is:open',
    'label:nft is:issue is:open',
    'label:dao is:issue is:open',
    'label:token is:issue is:open',
    'label:crypto-reward is:issue is:open',
    'label:paid is:issue is:open',
    'label:tip is:issue is:open',
    'label:help-wanted is:issue is:open',
    'label:good-first-issue is:issue is:open',
    'label:hackathon is:issue is:open',
    'label:challenge is:issue is:open',
    'label:contest is:issue is:open',
    'label:prize is:issue is:open',
    'label:competition is:issue is:open',
    'label:grant is:issue is:open',
    'label:funding is:issue is:open',
    'label:sponsor is:issue is:open',
    'label:bug-bounty is:issue is:open',
    'label:security is:issue is:open',
    'label:vulnerability is:issue is:open',
    'label:open-source is:issue is:open',
    'label:contributor is:issue is:open',
]

def search(query, page=1):
    params = urllib.parse.urlencode({
        'q': query,
        'sort': 'updated',
        'order': 'desc',
        'per_page': 10,
        'page': page
    })
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/vnd.github.v3+json'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"Error for '{query}': {e}")
        return None

def main():
    seen = set()
    results = []
    for q in QUERIES:
        data = search(q)
        if not data or 'items' not in data:
            continue
        for item in data['items']:
            key = item.get('html_url', '')
            if key in seen:
                continue
            seen.add(key)
            labels = [l['name'] for l in item.get('labels', [])]
            results.append({
                'title': item.get('title', ''),
                'url': key,
                'repo': item.get('repository_url', '').split('/')[-1],
                'labels': labels,
                'created': item.get('created_at', ''),
                'updated': item.get('updated_at', ''),
                'state': item.get('state', ''),
                'comments': item.get('comments', 0),
                'body': (item.get('body', '') or '')[:500]
            })
        time.sleep(0.5)
    
    # Filter for likely paid bounties
    paid_labels = {'bounty', 'USDC', 'ETH', 'SOL', 'USDT', 'reward', 'paid', 'tip', 
                   'crypto', 'crypto-reward', 'gitcoin', 'sponsor', 'grant', 'funding'}
    
    interesting = []
    for r in results:
        label_set = set(l.lower() for l in r['labels'])
        if label_set & paid_labels:
            interesting.append(r)
    
    print(f"Total unique issues: {len(results)}")
    print(f"Potential bounty issues: {len(interesting)}")
    print()
    for r in interesting[:30]:
        print(f"[{r['repo']}] {r['title'][:100]}")
        print(f"  URL: {r['url']}")
        print(f"  Labels: {', '.join(r['labels'])}")
        print()
    
    with open('docs/github_bounty_results.json', 'w') as f:
        json.dump(interesting, f, indent=2)
    print("Results saved to docs/github_bounty_results.json")

if __name__ == '__main__':
    main()