#!/usr/bin/env python3
"""Check wallet balances after faucet claims"""

import json

def check_balances():
    wallets = {
        'Ronin': '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B',
        'MetaMask': '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997',
        'Solana': '2emXSLoziaB5wdC8y48ovbu41agh9PzR5ro8o7kRDUvM',
        'Bitcoin': 'bc1qh3areygq598ntxht0yp5yv87ej7g6aqvw8fl4z',
        'Tron': 'TJxkyJW57Tb8qmvvv5rCh3L2FYssRvWFEv'
    }
    print('Wallet addresses for verification after faucet claims:')
    for name, addr in wallets.items():
        print(f'{name}: {addr}')

if __name__ == '__main__':
    check_balances()
