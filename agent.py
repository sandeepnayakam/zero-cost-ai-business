#!/usr/bin/env python3
"""
Zero-Cost AI Business Agent
Autonomous business operator running on GitHub Actions schedule.
Reads memory + prompt, calls free OpenRouter model, logs decisions only (no external actions).
"""

import os
import sys
from datetime import datetime

# === KILL SWITCH CHECK ===
if os.path.exists("PAUSE"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open("memory/state.md", "r") as f:
            current_state = f.read()
    except FileNotFoundError:
        current_state = ""

    with open("memory/state.md", "w") as f:
        f.write(f"## Summary\n{timestamp}: Paused by operator. No action taken.\n\n")
        f.write(f"**Last Run:** {timestamp}\n")
        if current_state:
            f.write(f"\n{current_state}")

    print(f"[{timestamp}] Agent paused by operator.")
    sys.exit(0)

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# === READ MEMORY FILES (repo-relative paths) ===
def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""

state_content = read_file("memory/state.md")
blocked_content = read_file("memory/blocked.md")
business_prompt = read_file("prompts/business_prompt.md")

# === CALL OPENROUTER API ===
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    error_msg = f"\n[{timestamp}] OPENROUTER_API_KEY environment variable not set or empty.\n"
    with open("memory/blocked.md", "a") as f:
        f.write(error_msg)
    print("[-] Missing API key, logged to blocked.md")
    sys.exit(1)

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/sandeepnayakam/zero-cost-ai-business",
    "X-Title": "Zero-Cost AI Business Agent"
}

# Currently confirmed-free tier models on OpenRouter
FREE_MODELS = [
    "google/gemini-2.0-flash:free",
    "mistralai/mistral-nemo:free",
    "neversleep/llama-3.1-8b:free"
]

messages = [
    {"role": "system", "content": business_prompt},
    {"role": "user", "content": f"Current state:\n{state_content}\n\nBlocked items:\n{blocked_content}\n\nRespond with reasoning + logging decisions only. Do NOT execute any external actions (no browser automation, no live API execution, no fund transfers). Log all decisions."}
]

response_content = None
used_model = None

for model_id in FREE_MODELS:
    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0.7
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and data["choices"]:
            response_content = data["choices"][0]["message"]["content"]
            used_model = model_id
            break
    except requests.exceptions.Timeout:
        print(f"[!] Timeout with {model_id}, trying next...")
    except requests.exceptions.RequestException as e:
        print(f"[!] Request failed for {model_id}: {e}, trying next...")
    except (KeyError, IndexError) as e:
        print(f"[!] Unexpected response format from {model_id}: {e}, trying next...")

if response_content is None:
    error_msg = f"\n[{timestamp}] All free models failed/unavailable. Tried: {', '.join(FREE_MODELS)}.\n"
    with open("memory/blocked.md", "a") as f:
        f.write(error_msg)
    print("[-] All models failed, logged to blocked.md")
    sys.exit(1)

# === LOG RESULTS ===
log_entry = f"## Run {timestamp}\nModel: {used_model}\n\n{response_content}\n---\n"
with open("memory/action_log.md", "a") as f:
    f.write(log_entry)

summary_preview = response_content[:200].replace("\n", " ").strip()
state_content_out = (
    f"## Summary\n"
    f"{timestamp}: {summary_preview}...\n\n"
    f"**Last Run:** {timestamp}\n"
    f"**Model Used:** {used_model}\n\n"
    f"{response_content[:500]}...\n"
)

with open("memory/state.md", "w") as f:
    f.write(state_content_out)

print(f"[+] Run complete at {timestamp}")
print(f"[+] Model: {used_model}")
print("[+] Logged to action_log.md, updated state.md")
