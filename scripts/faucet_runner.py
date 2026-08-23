import requests
from time import sleep

faucets = [
  {"url": "https://faucet.sepolia.ethereum.org/", "method": "POST", "data": {"address": "0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B", "coin": "ETH"}},
  {"url": "https://sepoliafaucet.com/", "method": "GET"},
  {"url": "https://faucet.quicknode.com/ethereum/sepolia", "method": "POST", "data": {"address": "0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B"}}
]

for f in faucets:
    try:
        if f['method'] == 'POST":
            r = requests.post(f['url'], json=f['data'])
        else:
            r = requests.get(f['url'])
        if r.status_code == 200: print(f'Claimed from {f['url']}')
        sleep(5)
    except: pass

# Log results to memory/faucet_results.json