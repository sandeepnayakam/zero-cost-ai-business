import os
import glob

research_files = [
    'docs/faucets_list.html',
    'docs/faucet_list.txt',
    'memory/faucet_research.md',
    'memory/new_crypto_opportunities.md',
    'memory/crypto_earning_strategy.md',
    'memory/faucet_research_plan.md'
]

for f in research_files:
    if os.path.exists(f):
        print(f'=== {f} ===')
        with open(f, 'r') as fp:
            content = fp.read()
            print(content[:3000])
            print('...' if len(content) > 3000 else '')
        print()
    else:
        print(f'=== {f} === NOT FOUND')
        print()
