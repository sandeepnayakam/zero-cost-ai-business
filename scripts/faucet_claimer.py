import requests

def claim(url):
    try:
        resp = requests.get(url)
        print(f'Claimed {url}: {resp.status_code}')
    except Exception as e:
        print(f'Failed: {e}')

# Example usage
claim('https://example-faucet.com/claim')