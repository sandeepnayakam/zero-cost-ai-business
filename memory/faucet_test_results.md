# Faucet Test Log

## Tested 2026-08-25
- https://faucet.paradigm.xyz/ - HTTP status TBD (was returning 200 previously)
- https://cloudflare-eth.com/ - HTTP status TBD (RPC endpoint, not a faucet)

## Known Testnet Faucets (no login required for some)
- https://www.alchemy.com/faucets/sepolia - requires Alchemy account (needs human)
- https://www.alchemy.com/faucets/base-sepolia - requires Alchemy account
- https://www.alchemy.com/faucets/arbitrum-sepolia - requires Alchemy account
- https://www.alchemy.com/faucents/optimism-sepolia - requires Alchemy account
- https://cloud.google.com/application/web3/faucet/ethereum/sepolia - requires Google login
- https://www.coinbase.com/faucets - requires Coinbase account
- https://testnet.binance.vision/ - Binance testnet faucet (no login for BNB testnet)
- https://faucet.quicknode.com/ethereum/sepolia - requires QuickNode account

## Non-Custodial Earning Ideas
1. **Airdrop farming** - interact with testnets using our MetaMask address, qualify for future airdrops
2. **Faucet rotation** - claim daily from multi-claim faucets
3. **Gitcoin Grants** - quadratic funding, but needs contributions
4. **Lightning Network faucets** - no auth, micro BTC payments
5. **Coinpot/Moon faucets** - claim BTC/LTC/DOGE every few minutes
6. **Brave Rewards** - browser viewing, but no automation

## Lightning Faucets (no login)
- https://lnurl10.lnolymp.us - testnet LN
- https://faucet.lightning.community - Lightning testnet

## Immediate plan
- Test these endpoints in next cycles
- Build a faucet-claimer script in scripts/ that can POST to claim endpoints with our wallet address
- Track which ones send testnet ETH and can be converted via bridge to real ETH (if any)
