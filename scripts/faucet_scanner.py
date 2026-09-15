#!/usr/bin/env python3
"""Scan multiple crypto faucet sites for working endpoints."""
import requests
import time

SITES = [
    "https://faucet.ether.io/",
    "https://www.freebitco.in/",
    "https://cryptotask.org/",
    "https://www.cointiply.com/",
    "https://faucet.crypto.in/",
    "https://freeethereum.org/",
    "https://faucet.polygon.technology/",
    "https://faucet.avalabs.org/",
    "https://faucet.testnet.matic.network/",
    "https://claim.fantom.network/",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def check_site(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.status_code
    except Exception as e:
        return f"ERR: {type(e).__name__}"

if __name__ == "__main__":
    results = []
    for site in SITES:
        code = check_site(site)
        results.append((site, code))
        print(f"{site} -> {code}")
        time.sleep(1)
    
    working = [(s, c) for s, c in results if isinstance(c, int) and c == 200]
    print(f"\nWorking sites (200): {working}")
