import requests, time

faucets = [
    ["https://coinfaucet.io/", 200, 316043],
    ["https://faucet.quicknode.com/", 200, 63838],
    ["https://autofaucet.org/", 200, 47011]
]

meta_mask_address = "0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997"

for url, status, amount in faucets:
    try:
        resp = requests.post(url, json={"address": meta_mask_address})
        if resp.status_code == 200:
            print(f"Claimed {amount} from {url}")
        else:
            print(f"Failed {url}: {resp.status_code}")
    except Exception as e:
        print(f"Error claiming from {url}: {e}")
    time.sleep(1)