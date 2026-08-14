#!/bin/bash
for url in "https://faucet.alternative1.com/claim" "https://faucet.alternative2.net/claim"; do
  curl -s -X POST $url >/dev/null 2>&1 || echo "Failed: $url"
 done