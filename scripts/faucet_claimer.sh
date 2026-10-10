#!/bin/sh
ADDRESS="0xAa4E76e5Be5334c0f2Fe0716C42B2FC61D4c150B"
while IFS= read -r url; do
  if [ -n "$url" ]; then
    echo "Attempting claim from $url for address $ADDRESS"
    curl -s "$url?address=$ADDRESS" | head -n 20
  fi
done < faucet_list.txt
