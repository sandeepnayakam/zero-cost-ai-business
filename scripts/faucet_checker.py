#!/usr/bin/env python3
import urllib.request, json, re, sys

# Crypto wallet addresses
METAMASK = '0xd6DFE6b54bF3dBC919Fde57009452fe6bbb0D997'
RONIN = '0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B'
BITCOIN = 'bc1qh3areygq598ntxht0yp5yv87ej7g6aqvw8fl4z'
SOLANA = '2emXSLoziaB5wdC8y48ovbu41agh9PzR5ro8o7kRDUvM'
TRON = 'TJxkyJW57Tb8qmvvv5rCh3L2FYssRvWFEv'

def probe_url(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, resp.read().decode()
    except Exception as e:
        return None, str(e)

def check_ethereum_faucet(url):
    """Check paradigm.xyz faucet"""
    status, data = probe_url(url)
    print(f'[{url}] status={status}')
    if 'wallet' in data.lower() or 'connect' in data.lower():
        print('  -> Requires wallet connection')
    if 'claim' in data.lower() or 'request' in data.lower():
        print('  -> Has claim button')
    return status == 200

def check_bitcoin_faucet(url):
    """Check bitcoin faucet"""
    status, data = probe_url(url)
    print(f'[{url}] status={status}')
    if 'bitcoin' in data.lower():
        print('  -> Bitcoin faucet detected')
    return status == 200

def check_moralis_faucet():
    """Check Moralis faucet"""
    url = 'https://faucets.moralis.io/'
    status, data = probe_url(url)
    print(f'[{url}] status={status}')
    if 'connect' in data.lower():
        print('  -> Requires wallet connection')
    return status == 200

def check_chainlink_faucets():
    """Check chain.link faucets"""
    url = 'https://faucets.chain.link/'
    status, data = probe_url(url)
    print(f'[{url}] status={status}')
    if 'claim' in data.lower():
        print('  -> Has claim options')
    return status == 200

def check_etherscan_faucet():
    """Check etherscan faucet"""
    url = 'https://faucet.etherscan.io/'
    status, data = probe_url(url)
    print(f'[{url}] status={status}')
    return status == 200

def check_freebitco():
    """Check freebitco.in"""
    url = 'https://freebitco.in/'
    status, data = probe_url(url)
    print(f'[{url}] status={status}')
    if 'claim' in data.lower() or 'hourly' in data.lower():
        print('  -> Has hourly claim feature')
    if 'bitcoin' in data.lower():
        print('  -> Pays in Bitcoin')
    return status == 200

if __name__ == '__main__':
    print('=== Faucet Probing Script ===\n')
    print('Target wallets:')
    print(f'  MetaMask: {METAMASK}')
    print(f'  Ronin: {RONIN}')
    print(f'  Bitcoin: {BITCOIN}')
    print(f'  Solana: {SOLANA}')
    print(f'  Tron: {TRON}')
    print()\n    
    print('--- Testing Ethereum Faucets ---')
    check_ethereum_faucet('https://faucet.paradigm.xyz/')
    print()
    
    print('--- Testing Bitcoin Faucets ---')
    check_bitcoin_faucet('https://bitcoinfaucet.co/')
    check_bitcoin_faucet('https://bitcoinfaucet.uux.sh/')
    print()
    
    print('--- Testing Multi-Chain Faucets ---')
    check_chainlink_faucets()
    check_etherscan_faucet()
    check_moralis_faucet()
    print()
    
    print('--- Testing Freebitco ---')
    check_freebitco()
    print()
    
    print('=== Probing Complete ===')
