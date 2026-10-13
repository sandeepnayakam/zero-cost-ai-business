import os

# List all claimer scripts
scripts_dir = 'scripts'
for f in os.listdir(scripts_dir):
    if 'claim' in f.lower() or 'faucet' in f.lower():
        path = os.path.join(scripts_dir, f)
        print(f'=== {path} ===')
        with open(path, 'r') as fp:
            content = fp.read()
            print(content[:2000])
        print()