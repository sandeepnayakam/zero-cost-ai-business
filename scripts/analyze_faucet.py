import re
import json
import sys

# Read the HTML from the previous fetch
with open('memory/coinfaucet_homepage.html', 'r') as f:
    html = f.read()

print('=== FORMS ===')
forms = re.findall(r'<form[^>]*action=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
for form in forms:
    print(f'  Action: {form}')

print('\n=== INPUT FIELDS ===')
inputs = re.findall(r'<input[^>]*>', html, re.IGNORECASE)
for inp in inputs:
    print(f'  {inp}')

print('\n=== BUTTONS ===')
buttons = re.findall(r'<button[^>]*>[^<]*</button>', html, re.IGNORECASE)
for btn in buttons:
    print(f'  {btn}')

print('\n=== JAVASCRIPT ENDPOINTS ===')
js_urls = re.findall(r'["\'](/api/[^"\']+)["\']', html)
js_urls += re.findall(r'["\'](/faucet[^"\']*)["\']', html)
js_urls += re.findall(r'["\'](/claim[^"\']*)["\']', html)
for url in set(js_urls):
    print(f'  {url}')

print('\n=== CSRF/TOKEN PATTERNS ===')
csrf = re.findall(r'csrf[^"\']*["\']([^"\']+)["\']', html, re.IGNORECASE)
csrf += re.findall(r'_token[^"\']*["\']([^"\']+)["\']', html, re.IGNORECASE)
for token in csrf:
    print(f'  {token}')

print('\n=== WALLET ADDRESS FIELDS ===')
wallet_fields = re.findall(r'["\']wallet["\'][^>]*>', html, re.IGNORECASE)
wallet_fields += re.findall(r'["\']address["\'][^>]*>', html, re.IGNORECASE)
for wf in wallet_fields:
    print(f'  {wf}')

print('\n=== ALL LINKS TO FAUCET/CLAIM PAGES ===')
links = re.findall(r'href=["\']([^"\']*(?:faucet|claim|earn|reward)[^"\']*)["\']', html, re.IGNORECASE)
for link in set(links):
    print(f'  {link}')

# Save results
results = {
    'forms': forms,
    'inputs': inputs,
    'buttons': buttons,
    'js_endpoints': list(set(js_urls)),
    'csrf_tokens': csrf,
    'wallet_fields': wallet_fields,
    'faucet_links': list(set(links))
}
with open('memory/faucet_analysis_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print('\nResults saved to memory/faucet_analysis_results.json')