#!/usr/bin/env python3
"""
Zero-Cost AI Business Agent v2
==============================
Multi-provider, multi-action autonomous agent.

Improvements over v1:
  - Multi-provider LLM routing (OpenRouter, Groq, Gemini, OpenAI, Cerebras, Together)
    with quota tracking and auto-failover (see llm_router.py).
  - Multiple actions per cycle (config: max_actions_per_run, default 3).
  - 8+ action types incl. multi-file write, HTTP POST, git ops, gh issues,
    allowlisted subprocess (see actions.py).
  - Sandboxed filesystem writes (config: sandbox_paths).
  - Daily action budget cap (config: max_actions_per_day).
  - Full before/after diff logging of every mutation.
  - Adaptive: agent can decide to skip a cycle ("action":"none") to conserve quota.

Runtime:
  - Set any of: OPENROUTER_API_KEY, GROQ_API_KEY, GOOGLE_AI_API_KEY,
    OPENAI_API_KEY, CEREBRAS_API_KEY, TOGETHER_API_KEY as env vars.
  - Create a file named PAUSE in repo root to halt all runs (kill switch).
"""

import json
import os
import sys
from datetime import datetime, timezone

import actions as act_mod
import llm_router


REPO_ROOT = os.getcwd()
TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
CONFIG_PATH = os.path.join(REPO_ROOT, "config.json")
DAILY_ACTION_LOG = os.path.join(REPO_ROOT, "memory", "daily_action_count.json")


# ----------------------------------------------------------------------------
# Small file helpers (re-imported from actions for top-level use)
# ----------------------------------------------------------------------------
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


def cap_blocked_log(path, max_entries=10):
    content = read_file(path)
    if not content:
        return
    parts = content.split("\n\n")
    header = parts[0] if parts else ""
    entries = [p for p in parts[1:] if p.strip()]
    trimmed = "\n\n".join([header] + entries[-max_entries:])
    write_file(path, trimmed)


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[!] config.json load failed ({e}); using defaults")
        return {
            "max_actions_per_run": 3,
            "max_actions_per_day": 60,
            "sandbox_paths": ["docs/", "site/", "memory/", "prompts/", "scripts/"],
            "subprocess_allowlist": ["python3 ", "pip install", "git "],
            "allowed_auth_headers": [],
            "llm": {"max_tokens": 3000, "temperature": 0.7, "timeout_seconds": 45},
            "log_max_chars": {"reasoning_in_state": 1500, "action_summary": 300},
        }


# ----------------------------------------------------------------------------
# Daily action counter
# ----------------------------------------------------------------------------
def load_daily_action_count():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        with open(DAILY_ACTION_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != today:
            data = {"date": today, "count": 0}
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"date": today, "count": 0}
    return data


def save_daily_action_count(data):
    write_file(DAILY_ACTION_LOG, json.dumps(data, indent=2))


# ----------------------------------------------------------------------------
# KILL SWITCH
# ----------------------------------------------------------------------------
if os.path.exists(os.path.join(REPO_ROOT, "PAUSE")):
    append_file("memory/state.md", f"\n\n[{TIMESTAMP}] Paused by operator. No action taken.\n")
    print(f"[{TIMESTAMP}] Paused by operator.")
    sys.exit(0)


# ----------------------------------------------------------------------------
# Load context
# ----------------------------------------------------------------------------
config = load_config()
state_content = read_file("memory/state.md")
blocked_content = read_file("memory/blocked.md")
revenue_content = read_file("memory/revenue.md")
pending_content = read_file("memory/pending_requests.md")
consult_request_content = read_file("memory/consult_request.md")
consult_response_content = read_file("memory/consult_response.md")
business_prompt = read_file("prompts/business_prompt.md")
action_log_tail = read_file("memory/action_log.md")[-4000:]  # last ~4KB for context

if not business_prompt.strip():
    append_file("memory/blocked.md", f"\n[{TIMESTAMP}] business_prompt.md is empty or missing.\n")
    print("[-] Missing business prompt, logged to blocked.md")
    sys.exit(1)


# ----------------------------------------------------------------------------
# Check that at least one LLM provider is configured
# ----------------------------------------------------------------------------
configured_providers = [
    name for name, pdef in llm_router.PROVIDERS.items()
    if os.getenv(pdef["env_key"])
]
if not configured_providers:
    append_file(
        "memory/blocked.md",
        f"\n[{TIMESTAMP}] No LLM provider API keys set. "
        f"Set at least one of: " +
        ", ".join(p["env_key"] for p in llm_router.PROVIDERS.values()) + "\n",
    )
    cap_blocked_log("memory/blocked.md")
    print("[-] No LLM provider API keys set.")
    sys.exit(1)


# ----------------------------------------------------------------------------
# Build prompt
# ----------------------------------------------------------------------------
RESPONSE_FORMAT_INSTRUCTIONS = f"""
Respond with ONLY a single JSON object, no other text, no markdown fences, in EXACTLY this shape:
{{
  "reasoning": "<your full reasoning as plain text, 2-5 sentences>",
  "actions": [
    {{
      "action": "none" | "write_file" | "multi_write" | "http_get" | "http_request" | "git_branch" | "git_commit_push" | "github_issue" | "subprocess" | "memory_edit",
      "action_params": {{
        "path": "<for write_file/memory_edit - MUST be inside one of: {', '.join(config['sandbox_paths'])}>",
        "content": "<for write_file/memory_edit>",
        "files": [{{"path": "...", "content": "..."}}, ...],
        "url": "<for http_get/http_request - http(s) only, no private/localhost IPs>",
        "method": "GET|POST|PUT|PATCH|DELETE",
        "body": "<string or object>",
        "headers": {{"X-API-Key": "..."}},
        "branch": "<git_branch>",
        "base": "<git_branch base, default HEAD>",
        "message": "<git_commit_push commit message>",
        "files": ["-A"] or ["docs/foo.html", ...],
        "op": "open|comment|close",
        "title": "<github_issue open>",
        "body": "<github_issue body>",
        "number": <int for github_issue comment/close>,
        "command": "<subprocess command - must match allowlist: {', '.join(config.get('subprocess_allowlist', []))}>",
        "timeout": <seconds, max 300>
      }}
    }},
    ...up to {config.get('max_actions_per_run', 3)} actions
  ],
  "revenue_update": "<any confirmed REAL realized profit to log, or empty string>",
  "pending_request": "<a new human-action request to log, or empty string>",
  "blocked_note": "<a new blocker to log, or empty string>",
  "skip_next_cycle": <true if you should NOT run next cycle to conserve quota, else false>
}}

Rules:
- Output pure JSON. No prose before or after. No ``` fences.
- Up to {config.get('max_actions_per_run', 3)} actions per cycle. Use "none" alone if you have nothing to do.
- All file paths MUST be inside one of the sandbox roots: {', '.join(config['sandbox_paths'])}.
- Subprocess commands MUST start with one of: {', '.join(config.get('subprocess_allowlist', []))}.
- HTTP requests to localhost / private IPs / 169.254.x.x are blocked.
- Today's UTC date is part of the timestamp above.
"""

user_message = f"""Current timestamp: {TIMESTAMP}

CONFIG:
- Max actions this cycle: {config.get('max_actions_per_run', 3)}
- Daily action budget remaining: {max(0, config.get('max_actions_per_day', 60) - load_daily_action_count().get('count', 0))}
- Sandbox paths: {', '.join(config['sandbox_paths'])}
- Subprocess allowlist: {', '.join(config.get('subprocess_allowlist', []))}

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

RECENT ACTION LOG (last ~4KB):
{action_log_tail}

LLM PROVIDER STATUS:
{llm_router.provider_status()}

{RESPONSE_FORMAT_INSTRUCTIONS}
"""

messages = [
    {"role": "system", "content": business_prompt},
    {"role": "user", "content": user_message},
]


# ----------------------------------------------------------------------------
# Call LLM (with multi-provider failover)
# ----------------------------------------------------------------------------
try:
    response_content, used_provider, used_model, _quota_state = llm_router.route_completion(
        messages,
        max_tokens=config.get("llm", {}).get("max_tokens", 3000),
        temperature=config.get("llm", {}).get("temperature", 0.7),
    )
except RuntimeError as e:
    append_file(
        "memory/blocked.md",
        f"\n[{TIMESTAMP}] All LLM providers failed: {str(e)[:500]}\n",
    )
    cap_blocked_log("memory/blocked.md")
    print(f"[-] All LLM providers failed: {e}")
    sys.exit(1)

print(f"[+] LLM responded via {used_provider}/{used_model}")


# ----------------------------------------------------------------------------
# Parse JSON response (tolerant of markdown fences)
# ----------------------------------------------------------------------------
parsed = None
cleaned = response_content.strip()
if cleaned.startswith("```"):
    # strip opening fence (``` or ```json)
    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned.lstrip("`")
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

try:
    parsed = json.loads(cleaned)
except (json.JSONDecodeError, ValueError) as e:
    # Fallback: treat raw response as reasoning-only
    print(f"[!] JSON parse failed: {e}; treating as reasoning-only")
    parsed = {
        "reasoning": response_content[:3000],
        "actions": [{"action": "none", "action_params": {}}],
        "revenue_update": "",
        "pending_request": "",
        "blocked_note": "",
        "skip_next_cycle": False,
    }

reasoning = parsed.get("reasoning", "")
actions_list = parsed.get("actions") or []
if not isinstance(actions_list, list):
    actions_list = []
if not actions_list:
    actions_list = [{"action": "none", "action_params": {}}]

# Cap to max_actions_per_run
max_per_run = config.get("max_actions_per_run", 3)
if len(actions_list) > max_per_run:
    print(f"[!] LLM returned {len(actions_list)} actions, capping to {max_per_run}")
    actions_list = actions_list[:max_per_run]


# ----------------------------------------------------------------------------
# Apply memory updates (revenue / pending / blocked)
# ----------------------------------------------------------------------------
if parsed.get("revenue_update"):
    append_file("memory/revenue.md", f"\n[{TIMESTAMP}] {parsed['revenue_update']}\n")

if parsed.get("pending_request"):
    append_file(
        "memory/pending_requests.md",
        f"\n[{TIMESTAMP}] {parsed['pending_request']}\n",
    )

if parsed.get("blocked_note"):
    append_file("memory/blocked.md", f"\n[{TIMESTAMP}] {parsed['blocked_note']}\n")
    cap_blocked_log("memory/blocked.md")


# ----------------------------------------------------------------------------
# Execute actions (respecting daily budget)
# ----------------------------------------------------------------------------
daily_count = load_daily_action_count()
daily_budget = config.get("max_actions_per_day", 60)
actions_taken = 0
action_results = []
for action_obj in actions_list:
    if daily_count["count"] >= daily_budget:
        msg = f"Daily action budget ({daily_budget}) reached; skipping remaining actions."
        print(f"[!] {msg}")
        action_results.append({"ok": False, "action": "skip", "error": msg,
                               "summary": msg})
        break
    # "none" doesn't count against budget
    if action_obj.get("action") == "none":
        action_results.append({"ok": True, "action": "none", "summary": "no-op",
                               "error": ""})
        continue
    result = act_mod.execute_action(action_obj, config)
    action_results.append(result)
    if result["ok"]:
        daily_count["count"] += 1
        actions_taken += 1
    else:
        # Log blocked action but don't count against budget
        append_file(
            "memory/action_log.md",
            f"\n[{TIMESTAMP}] ACTION BLOCKED: {result['action']} -> {result['error']}\n---\n",
        )
        print(f"[!] Action blocked: {result['action']} -> {result['error']}")

save_daily_action_count(daily_count)


# ----------------------------------------------------------------------------
# Audit log (uncapped, full reasoning + per-action results)
# ----------------------------------------------------------------------------
results_summary = "\n".join(
    f"  - {r['action']}: {'OK' if r['ok'] else 'FAIL'} {r.get('summary','') or r.get('error','')}"
    for r in action_results
)
log_entry = (
    f"## Run {TIMESTAMP}\n"
    f"Provider: {used_provider}\nModel: {used_model}\n"
    f"Actions executed: {actions_taken}/{len(actions_list)} "
    f"(daily total: {daily_count['count']}/{daily_budget})\n\n"
    f"Action results:\n{results_summary}\n\n"
    f"Reasoning:\n{reasoning}\n---\n"
)
append_file("memory/action_log.md", log_entry)


# ----------------------------------------------------------------------------
# Compact state.md summary for next cycle
# ----------------------------------------------------------------------------
def excerpt(text, limit):
    text = (text or "").strip()
    return text[:limit] + ("..." if len(text) > limit else "")


reasoning_limit = config.get("log_max_chars", {}).get("reasoning_in_state", 1500)
action_summary_limit = config.get("log_max_chars", {}).get("action_summary", 300)
skip_flag = " (skipping next cycle per agent)" if parsed.get("skip_next_cycle") else ""

state_out = (
    f"## Summary\n{TIMESTAMP}{skip_flag}\n\n"
    f"**Last Run:** {TIMESTAMP}\n"
    f"**Provider/Model:** {used_provider} / {used_model}\n"
    f"**Actions this cycle:** {actions_taken}/{len(actions_list)}\n"
    f"**Daily action count:** {daily_count['count']}/{daily_budget}\n\n"
    f"**Action results:**\n{results_summary[:action_summary_limit]}\n\n"
    f"**Reasoning:**\n{excerpt(reasoning, reasoning_limit)}\n"
)
write_file("memory/state.md", state_out)


print(
    f"[+] Run complete at {TIMESTAMP} | provider={used_provider} | "
    f"model={used_model} | actions={actions_taken}/{len(actions_list)} | "
    f"daily={daily_count['count']}/{daily_budget}"
)
