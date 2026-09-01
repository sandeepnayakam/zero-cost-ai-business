#!/usr/bin/env python3
import urllib.request, json, sys

def probe(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        data = resp.read().decode()
        return resp.status, data
    except Exception as e:
        return None, str(e)

# FaucetPay endpoints
endpoints = [
    ('FaucetPay info', 'https://api.faucetpay.io/api/v1/info', {}),
    ('FaucetPay BTC list', 'https://api.faucetpay.io/api/v1/faucet/list?currency=BTC&page=1', {}),
    ('FaucetPay claim test', 'https://api.faucetpay.io/api/v1/claim?address=0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997&currency=BTC&amount=0.00001', {}),
]
for name, url, hdrs in endpoints:
    status, data = probe(url, hdrs)
    print(f'[{name}] status={status}')
    print(f'  data={data[:500]}')
    print()
