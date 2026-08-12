import requests
import time

# Common crypto faucets to try
FAUCETS = [
    {'name': 'Ronin Faucet', 'url': 'https://faucet.roninchain.com', 'method': 'GET'},
    {'name': 'Ethereum Faucet', 'url': 'https://ethereumfaucet.com', 'method': 'GET'},
    {'name': 'Polygon Faucet', 'url': 'https://polygonfaucet.com', 'method': 'GET'},
]

WALLET_RONIN = '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B'
WALLET_METAMASK = '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def claim_from_faucet(faucet):
    try:
        print(f"Claiming from {faucet['name']}...")
        response = requests.get(faucet['url'], headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            # Look for claim forms/buttons
            return response.text[:500]
        return None
    except Exception as e:
        print(f"Error with {faucet['name']}: {e}")
        return None

if __name__ == '__main__':
    for faucet in FAUCETS:
        result = claim_from_faucet(faucet)
        if result:
            print(f"Success from {faucet['name']}")
        time.sleep(2)
