import urllib.request
import json

ronin_address = '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B'

# Ronin RPC endpoints
ronin_rpcs = [
    'https://api.roninchain.com/rpc',
    'https://ronin.drpc.org',
    'https://ronin-rpc.publicnode.com',
    'https://ronin-mainnet.g.alchemy.com/v2/demo',
]

for rpc in ronin_rpcs:
    try:
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'eth_getBalance',
            'params': [ronin_address, 'latest'],
            'id': 1
        }).encode()
        req = urllib.request.Request(rpc, data=payload, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if 'result' in data:
            wei = int(data['result'], 16)
            ron = wei / 1e18
            print(f'[{rpc}] Ronin: {ron} RON ({wei} wei)')
        else:
            print(f'[{rpc}] Error: {data}')
    except Exception as e:
        print(f'[{rpc}] FAILED: {e}')