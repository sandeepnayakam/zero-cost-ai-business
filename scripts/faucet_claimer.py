import requests
from bs4 import BeautifulSoup
import re

# Read faucets.md and extract URLs
with open('docs/faucets.md') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')
urls = []

# Extract Bitcoin faucets
bitcoin_section = soup.find('h2', text='Bitcoin Faucets')
if bitcoin_section:
    for link in bitcoin_section.find_next('ul').find_all('a'):
        urls.append(link['href'])

# Repeat for other crypto sections (Ethereum, Ronin, etc.) if needed

# Claim each URL
for url in urls:
    try:
        resp = requests.get(url)
        print(f'Claimed {url}: {resp.status_code}')
    except Exception as e:
        print(f'Failed: {e}')