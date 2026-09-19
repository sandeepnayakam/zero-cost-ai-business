import requests
import re
import time

# List of known crypto faucets to test
faucets = [
    "https://faucet.paradigm.xyz/claim?address=",
    "https://faucet.quicknode.com/ethereum/sepolia",
    "https://faucet.metamask.io/",
    "https://www.alchemy.com/faucet",
    "https://faucet.quicknode.com/",
]

ronin_address = "0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B"

results = []
for faucet_url in faucets:
    try:
        full_url = faucet_url + ronin_address if faucet_url.endswith("=") else faucet_url
        resp = requests.get(full_url, timeout=15, allow_redirects=True)
        results.append(f"{faucet_url}: status={resp.status_code}, len={len(resp.text)}")
        # Check for common reward keywords
        if any(word in resp.text.lower() for word in ["success", "reward", "claimed", "sent", "transaction", "hash"]):
            results.append(f"  -> POSSIBLE REWARD FOUND")
    except Exception as e:
        results.append(f"{faucet_url}: ERROR - {str(e)[:100]}")

with open("memory/faucet_results.md", "w") as f:
    f.write("# Faucet Test Results\n\n")
    for r in results:
        f.write(r + "\n")

print("\n".join(results))
