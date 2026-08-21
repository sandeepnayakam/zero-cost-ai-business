import requests, json, os
addr='0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'
url=f'https://api.ethplorer.io/getAddressInfo/{addr}?apiKey=freekey'
try:
    resp=requests.get(url,timeout=10)
    resp.raise_for_status()
    data=resp.json()
    bal=data.get('balance',0)
    out=f'address:{addr}\nbalance:{bal} ETH\n'
    with open('memory/balance.txt','w') as f:
        f.write(out)
except Exception as e:
    with open('memory/balance.txt','w') as f:
        f.write(f'error:{e}')
