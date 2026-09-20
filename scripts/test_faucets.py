import requests
import re
import json
from urllib.parse import urljoin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Known crypto faucets to test
FAUCETS = [
    'https://coinfaucet.io/',
    'https://faucet.quicknode.com/',
    'https://faucet.metamask.io/',
    'https://freebitco.in/',
    'https://faucets.io/',
    'https://www.freebitco.in/',
    'https://faucet.crypto.com/',
    'https://faucet.coinpayments.net/',
    'https://autofaucet.org/',
    'https://faucet.crypto faucets.com/',
]

def test_faucet(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        return {'url': url, 'status': r.status_code, 'size': len(r.text), 'accessible': r.status_code == 200}
    except Exception as e:
        return {'url': url, 'status': 0, 'error': str(e), 'accessible': False}

def extract_faucet_links(html, base_url):
    links = re.findall(r'href=["\']([^"\'>]*faucet[^"\'>]*)["\']', html, re.I)
    links += re.findall(r'href=["\']([^"\'>]*claim[^"\'>]*)["\']', html, re.I)
    links += re.findall(r'href=["\']([^"\'>]*free[^"\'>]*crypto[^"\'>]*)["\']', html, re.I)
    # Filter and deduplicate
    seen = set()
    result = []
    for link in links:
        full = urljoin(base_url, link)
        if full not in seen and 'faucet' in full.lower() or 'claim' in full.lower():
            seen.add(full)
            result.append(full)
    return result[:20]

print("Testing faucets...")
results = []
for url in FAUCETS:
    print(f"Testing: {url}")
    result = test_faucet(url)
    results.append(result)
    print(f"  Status: {result.get('status', 'ERR')}, Accessible: {result['accessible']}")
    if result['accessible'] and result['size'] > 0:
        links = extract_faucet_links(result.get('html', ''), url)
        if links:
            print(f"  Found {len(links)} potential faucet links")

print("\n=== SUMMARY ===")
for r in results:
    if r['accessible']:
        print(f"WORKING: {r['url']} (size: {r['size']})")
    else:
        print(f"FAILED: {r['url']} - {r.get('error', 'status '+str(r.get('status')))}")

# Save results
with open('/home/gibbon/synthtool/memory/faucet_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nResults saved to memory/faucet_results.json")
