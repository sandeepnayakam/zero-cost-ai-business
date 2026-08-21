import requests

def check_faucet(url, address):
    params = {'address': address}
    try:
        resp = requests.get(url, params=params)
        if 'success' in resp.text.lower() or 'approved' in resp.text.lower(): return True
    except: pass
    return False

if __name__ == '__main__':
    metamask = '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'
    ronin = '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B'
    faucets = [
        'https://faucet.solana.com',  # Prioritize Solana faucet
        'https://faucet.ankr.com/ethereum'  # Keep Ankr as fallback
    ]
    for faucet in faucets:
        if check_faucet(faucet, metamask): print(f'MetaMask got funds from {faucet}')
        if check_faucet(faucet, ronin): print(f'Ronin got funds from {faucet}')