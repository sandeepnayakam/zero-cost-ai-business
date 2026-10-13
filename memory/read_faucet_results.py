import json
import os

# Read key faucet result files
files_to_check = [
    'docs/faucet_results.md',
    'docs/faucet_status.md',
    'docs/working_faucets.json',
    'memory/working_faucets.json',
    'memory/faucet_results.json',
    'memory/faucet_results.txt',
    'memory/faucet_status.txt',
    'memory/faucet_test_results.md',
]

for f in files_to_check:
    if os.path.exists(f):
        print(f'=== {f} ===')
        with open(f, 'r') as fp:
            content = fp.read()
            print(content[:3000])
        print()
    else:
        print(f'=== {f} === NOT FOUND')
        print()