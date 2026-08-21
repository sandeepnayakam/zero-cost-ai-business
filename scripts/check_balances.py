import json, urllib.request, sys

addresses = {
    'MetaMask': '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997',
    'Ronin': '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B',
}

rpcs = [
    'https://eth.llamarpc.com',
    'https://rpc.ankr.com/eth',
    'https://cloudflare-eth.com',
    'https://ethereum.publicnode.com',
    'https://eth.merkle.io',
    'https://eth-mainnet.public.blastapi.io',
    'https://ethereum-rpc.publicnode.com',
    'https://eth.drpc.org',
    'https://1rpc.io/eth',
    'https://eth-pokt.nodies.app',
]

payload = json.dumps({
    'jsonrpc': '2.0',
    'method': 'eth_getBalance',
    'params': ['0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997', 'latest'],
    'id': 1
}).encode()

for rpc in rpcs:
    try:
        req = urllib.request.Request(rpc, data=payload, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if 'result' in data:
            wei = int(data['result'], 16)
            eth = wei / 1e18
            print(f'[{rpc}] MetaMask: {eth} ETH ({wei} wei)')
        else:
            print(f'[{rpc}] Error: {data}')
    except Exception as e:
        print(f'[{rpc}] FAILED: {e}')

# Also check Ronin address on Ronin RPC
ronin_rpcs = [
    'https://rpc.roninchain.com',
    'https://api.roninchain.com',
]
ronin_payload = json.dumps({
    'jsonrpc': '2.0',
    'method': 'eth_getBalance',
    'params': ['0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B', 'latest'],
    'id': 1
}).encode()
for rpc in ronin_rpcs:
    try:
        req = urllib.request.Request(rpc, data=ronin_payload, headers={'Content-Type': 'application/json'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if 'result' in data:
            wei = int(data['result'], 16)
            eth = wei / 1e18
            print(f'[{rpc}] Ronin: {eth} RON ({wei} wei)')
        else:
            print(f'[{rpc}] Error: {data}')
    except Exception as e:
        print(f'[{rpc}] FAILED: {e}')

print('\nDone.')
