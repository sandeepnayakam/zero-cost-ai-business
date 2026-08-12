import requests
from bs4 import BeautifulSoup
import json

# Common crypto faucets to try
FAUCETS = [
    {'name': 'Ronin Faucet', 'url': 'https://faucet.roninchain.com', 'method': 'GET'},
    {'name': 'Ethereum Faucet', 'url': 'https://ethereumfaucet.com', 'method': 'GET'},
    {'name': 'Polygon Faucet', 'url': 'https://polygonfaucet.com', 'method': 'GET'},
]

# Wallet addresses to use
WALLET_RONIN = '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B'
WALLET_METAMASK = '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_faucet(faucet):
    try:
        print(f"Checking {faucet['name']} at {faucet['url']}...")
        response = requests.get(faucet['url'], headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for claim buttons or forms
            claim_buttons = soup.find_all('a', href=True)
            for btn in claim_buttons:
                if 'claim' in btn['href'].lower() or 'faucet' in btn['href'].lower():
                    print(f"Found claim link: {btn['href']}")
            # Look for wallet input fields
            inputs = soup.find_all('input', type='text')
            print(f"Found {len(inputs)} text inputs")
        return response.status_code
    except Exception as e:
        print(f"Error with {faucet['name']}: {e}")
        return None

if __name__ == '__main__':
    print("Crypto Faucet Checker - Starting scan...")
    for faucet in FAUCETS:
        check_faucet(faucet)
    print("\nScan complete. Check results above for any claim opportunities.")
