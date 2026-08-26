import os
import json

files_to_read = [
    'memory/crypto_earning_strategy.md',
    'docs/faucet_research.md',
    'docs/faucet_analysis.txt',
    'docs/faucet_alternatives.txt',
    'docs/faucet_log.txt',
    'docs/faucet_results.json',
    'docs/faucet_results.txt',
]

for f in files_to_read:
    if os.path.exists(f):
        print(f'=== {f} ===')
        with open(f, 'r') as fp:
            content = fp.read()
            print(content[:5000])
            print('...' if len(content) > 5000 else '')
        print()
    else:
        print(f'=== {f} === NOT FOUND')
        print()