import sys
import requests

# List of faucet URLs to check (from pending requests and common ones)
urls = [
    'https://coninfaucet.io/',
    'https://autofaucet.org/',
    'https://faucet.quicknode.com/',
    'https://ethereumfaucet.com/',
    'https://cryptotask.org/',
    'https://freebitco.in/',
    'https://freedoge.co.in/',
    'https://firefaucet.win/',
    'https://allcoins.pw/',
    'https://faucetcrypto.com/'
]

reachable = []
for url in urls:
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            reachable.append(url)
            print(f'UP: {url}')
        else:
            print(f'DOWN ({resp.status_code}): {url}')
    except Exception as e:
        print(f'ERROR: {url} - {e}')

print('\nReachable faucets:')
for u in reachable:
    print(u)
