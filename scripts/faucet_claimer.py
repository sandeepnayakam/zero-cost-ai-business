#!/usr/bin/env python3
import subprocess, sys, os, re, json, time

# List of faucet URLs to test
urls = [
    "https://faucet.lightning.community/",
    "https://freebitcoin.io/",
    "https://testnet.binance.vision/",
    "https://cloudflare-eth.com/",
]

def http_get(url):
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def fetch_content(url):
    try:
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout
    except Exception as e:
        return f"ERROR: {e}"

# Test each faucet
for url in urls:
    print(f"Testing {url}")
    code = http_get(url)
    print(f"  HTTP status: {code}")
    if code == "200":
        content = fetch_content(url)
        # Extract potential claim endpoints (simple heuristic)
        # Look for forms with action
        forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\']', content, re.I)
        if forms:
            print(f"  Found forms: {forms}")
        # Look for any JSON or API endpoints
        api_matches = re.findall(r'"(/api/.*?)\"', content)
        if api_matches:
            print(f"  Potential API endpoints: {api_matches}")
        # If page contains 'claim' or 'faucet' keywords
        if re.search(r'claim|faucet', content, re.I):
            print("  Contains claim/faucet keywords")
    print()

print("Script finished.")