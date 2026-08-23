#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import time
import sys

# Wallet addresses
RONIN = '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B'
METAMASK = '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'

# Known working faucets
FAUCETS = [
    ('https://faucets.chain.link/', {'address': RONIN, 'coin': 'eth'}),
    ('https://faucet.quicknode.com/ethereum/sepolia', {'address': METAMASK, 'coin': 'eth'}),
]

def try_faucet(url, data, method='POST'):
    try:
        encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(url, data=encoded_data, method=method)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header('User-Agent', 'Mozilla/5.0')
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            return {'success': True, 'url': url, 'status': resp.status, 'body': body[:500]}
    except urllib.error.HTTPError as e:
        return {'success': False, 'url': url, 'error': f'HTTP {e.code}: {e.reason}'}
    except urllib.error.URLError as e:
        return {'success': False, 'url': url, 'error': str(e.reason)}
    except Exception as e:
        return {'success': False, 'url': url, 'error': str(e)}

def main():
    results = []
    for url, data in FAUCETS:
        print(f'Trying {url}...')
        result = try_faucet(url, data)
        results.append(result)
        print(f'  Result: {result}')
        time.sleep(2)
    
    with open('memory/faucet_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print('Results saved to memory/faucet_results.json')
    return results

if __name__ == '__main__':
    main()
