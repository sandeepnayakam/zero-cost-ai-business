#!/usr/bin/env python3
"""
Zero-Cost AI Business Agent
Runs once per scheduled cycle. Reads memory + prompt, calls a free
OpenRouter model, and executes set of real actions. Everything else is reasoning + logging + action
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

REPO_ROOT = os.getcwd()
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def read_file(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return default


def append_file(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def cap_blocked_log(path, max_entries=5):
    """Keep blocked.md from growing forever - keep header + last N entries."""
    content = read_file(path)
    if not content:
        return
    parts = content.split("\n\n")
    header = parts[0] if parts else ""
    entries = [p for p in parts[1:] if p.strip()]
    trimmed = "\n\n".join([header] + entries[-max_entries:])
    write_file(path, trimmed)


# === KILL SWITCH ===
if os.path.exists(os.path.join(REPO_ROOT, "PAUSE")):
    append_file("memory/state.md", f"\n\n[{TIMESTAMP}] Paused by operator. No action taken.\n")
    print(f"[{TIMESTAMP}] Paused by operator.")
    sys.exit(0)

# === READ ALL MEMORY FILES ===
state_content = read_file("memory/state.md")
blocked_content = read_file("memory/blocked.md")
revenue_content = read_file("memory/revenue.md")
pending_content = read_file("memory/pending_requests.md")
consult_request_content = read_file("memory/consult_request.md")
consult_response_content = read_file("memory/consult_response.md")
business_prompt = read_file("prompts/business_prompt.md")

if not business_prompt.strip():
    append_file("memory/blocked.md", f"\n[{TIMESTAMP}] business_prompt.md is empty or missing.\n")
    print("[-] Missing business prompt, logged to blocked.md")
    sys.exit(1)

# === CHECK API KEY ===
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    append_file("memory/blocked.md", f"\n[{TIMESTAMP}] OPENROUTER_API_KEY not set.\n")
    print("[-] Missing API key, logged to blocked.md")
    sys.exit(1)

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/sandeepnayakam/zero-cost-ai-business",
    "X-Title": "Zero-Cost AI Business Agent",
}

RESPONSE_FORMAT_INSTRUCTIONS = """
Respond with ONLY a single JSON object, no other text, in exactly this shape:
{
  "reasoning": "<your full reasoning as plain text>",
  "action": "none" | "write_file" | "http_get",
  "action_params": {
    "path": "<only used if action is write_file - MUST start with docs/>",
    "content": "<only used if action is write_file>",
    "url": "<only used if action is http_get - must be http:// or https://>"
  },
  "revenue_update": "<any confirmed REAL realized profit to log, or empty string>",
  "pending_request": "<a new human-action request to log, or empty string>",
  "blocked_note": "<a new blocker to log, or empty string>"
}
Only ONE action per cycle. If unsure, use action "none".
"""

user_message = f"""Current timestamp: {TIMESTAMP}

STATE:
{state_content}

BLOCKED ITEMS:
{blocked_content}

REVENUE:
{revenue_content}

PENDING REQUESTS (awaiting human):
{pending_content}

YOUR LAST CONSULT QUESTION:
{consult_request_content}

HUMAN'S ANSWER TO YOUR LAST CONSULT QUESTION:
{consult_response_content}

{RESPONSE_FORMAT_INSTRUCTIONS}
"""

messages = [
    {"role": "system", "content": business_prompt},
    {"role": "user", "content": user_message},
]

FREE_MODELS = ["openrouter/free"]
MAX_RETRIES_PER_MODEL = 2
RETRY_DELAY_SECONDS = 15

response_content = None
used_model = None

for model_id in FREE_MODELS:
    for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7,
        }
        try:
            resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=45)
            resp.raise_for_status()
            data = resp.json()
            if "choices" in data and data["choices"]:
                response_content = data["choices"][0]["message"]["content"]
                used_model = model_id
                break
            print(f"[!] Empty choices from {model_id}, attempt {attempt}")
        except requests.exceptions.RequestException as e:
            body = getattr(e.response, "text", "")[:300] if getattr(e, "response", None) else ""
            print(f"[!] {model_id} attempt {attempt} failed: {e} | {body}")
        if attempt < MAX_RETRIES_PER_MODEL:
            time.sleep(RETRY_DELAY_SECONDS)
    if response_content:
        break

if response_content is None:
    append_file(
        "memory/blocked.md",
        f"\n[{TIMESTAMP}] All models failed after retries. Tried: {', '.join(FREE_MODELS)}.\n",
    )
    cap_blocked_log("memory/blocked.md")
    print("[-] All models failed, logged to blocked.md")
    sys.exit(1)

# === PARSE STRUCTURED RESPONSE (fail safe: treat as reasoning-only if parsing fails) ===
parsed = None
try:
    cleaned = response_content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    parsed = json.loads(cleaned)
except (json.JSONDecodeError, ValueError):
    parsed = {"reasoning": response_content, "action": "none", "action_params": {},
              "revenue_update": "", "pending_request": "", "blocked_note": ""}

reasoning = parsed.get("reasoning", "")
action = parsed.get("action", "none")
action_params = parsed.get("action_params", {}) or {}
action_result = "No action taken."


# === APPLY MEMORY UPDATES ===
if parsed.get("revenue_update"):
    append_file("memory/revenue.md", f"\n[{TIMESTAMP}] {parsed['revenue_update']}\n")

if parsed.get("pending_request"):
    append_file("memory/pending_requests.md", f"\n[{TIMESTAMP}] {parsed['pending_request']}\n")

if parsed.get("blocked_note"):
    append_file("memory/blocked.md", f"\n[{TIMESTAMP}] {parsed['blocked_note']}\n")
    cap_blocked_log("memory/blocked.md")

# === LOG FULL DETAIL (uncapped, for audit) ===
log_entry = (
    f"## Run {TIMESTAMP}\nModel: {used_model}\nAction: {action}\n"
    f"Action result: {action_result}\n\nReasoning:\n{reasoning}\n---\n"
)
append_file("memory/action_log.md", log_entry)

# === COMPACT, CORRECTLY-TRUNCATED SUMMARY ===
def excerpt(text, limit):
    text = text.strip()
    return text[:limit] + ("..." if len(text) > limit else "")

state_content_out = (
    f"## Summary\n{TIMESTAMP}: {excerpt(reasoning, 200)}\n\n"
    f"**Last Run:** {TIMESTAMP}\n**Model Used:** {used_model}\n**Action:** {action}\n"
    f"**Action Result:** {excerpt(action_result, 300)}\n\n"
    f"{excerpt(reasoning, 1500)}\n"
)
write_file("memory/state.md", state_content_out)

print(f"[+] Run complete at {TIMESTAMP} | model={used_model} | action={action}")
