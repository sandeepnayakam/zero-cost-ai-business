import requests, re, json, time, os
from urllib.parse import urljoin

# List of known faucet URLs to test (including ones we found working)
FAUCET_URLS = [
    "https://coinfaucet.io/",
    "https://faucet.quicknode.com/",
    "https://autofaucet.org/",
    "https://faucet.crypto.com/",
    "https://faucet.metamask.io/",
    "https://faucets.io/",
    "https://freebitco.in/",
    "https://www.freebitco.in/",
    "https://faucet.coinpayments.net/",
]

# Ronin wallet address (public only)
RONIN_ADDRESS = "0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B"

def check_faucet(url):
    try:
        resp = requests.get(url, timeout=10, verify=False)
        status = resp.status_code
        accessible = status == 200
        size = len(resp.content) if accessible else 0
        return accessible, status, size
    except Exception as e:
        return False, str(e), 0

def extract_links(html, base):
    # crude extraction of links that look like faucet pages
    links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\']', html, re.I)
    faucet_links = []
    for link in links:
        abs_link = urljoin(base, link)
        if 'coinfaucet' in abs_link or 'faucet' in abs_link:
            faucet_links.append(abs_link)
    return list(set(faucet_links))

def main():
    working = []
    for url in FAUCET_URLS:
        accessible, status, size = check_faucet(url)
        print(f"Testing: {url}")
        print(f"  Status: {status}, Accessible: {accessible}, Size: {size}")
        if accessible:
            working.append((url, status, size))
            # If it's coinfaucet.io, try to extract sub‑faucets
            if url.startswith("https://coinfaucet.io"):
                try:
                    resp = requests.get(url, timeout=10, verify=False)
                    sub_links = extract_links(resp.text, url)
                    print(f"  Extracted {len(sub_links)} potential sub‑faucet links")
                    for sub in sub_links[:5]:  # limit to 5 for now
                        print(f"    - {sub}")
                except Exception as e:
                    print(f"  Error extracting links: {e}")
        print()
    print("\n=== SUMMARY ===")
    for url, status, size in working:
        print(f"WORKING: {url} (size: {size})")
    # Save working list to a file for later use
    with open("memory/working_faucets.json", "w") as f:
        json.dump(working, f, indent=2)

if __name__ == "__main__":
    main()