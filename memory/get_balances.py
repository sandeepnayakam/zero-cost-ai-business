import requests, json

def get_balance_eth(address):
    url = f'https://api.blockcypher.com/v1/eth/main/addrs/{address}'
    r = requests.get(url)
    r.raise_for_status()
    return r.json().get('balance', 0)

def main():
    balances = {
        'metamask': get_balance_eth('0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'),
        'ronin': get_balance_eth('0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B')
    }
    with open('memory/balances.json', 'w') as f:
        json.dump(balances, f)

if __name__ == '__main__':
    main()
