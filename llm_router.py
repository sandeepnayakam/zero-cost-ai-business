#!/usr/bin/env python3
"""
Multi-provider LLM router with quota tracking and auto-failover.

Supported providers (set any subset of these as GitHub Actions secrets):
  - OPENROUTER_API_KEY   (gateway to many free models)
  - GROQ_API_KEY         (ultra-fast free Llama 3.3 70B)
  - GOOGLE_AI_API_KEY    (Gemini 2.0 Flash free tier)
  - OPENAI_API_KEY       (paid fallback, ultra-reliable)
  - CEREBRAS_API_KEY     (free ultra-fast Llama/Qwen)
  - TOGETHER_API_KEY     (free Llama/Mistral)

Routing strategy:
  1. Filter providers that have an API key set AND remaining quota.
  2. Sort by (priority asc, requests_today asc, last_used asc).
  3. Try each in order until one succeeds.
  4. On failure (429 / 5xx / timeout), record the error and try the next.
  5. Quota state persists to memory/quota.json between runs.
"""

import json
import os
import time
from datetime import datetime, timezone

import requests


# ----------------------------------------------------------------------------
# Provider definitions
# ----------------------------------------------------------------------------
# Each provider: endpoint URL, auth header name/prefix, default model list,
# per-day request budget, per-minute request budget, and priority
# (lower priority = preferred when quota is available).
PROVIDERS = {
    "groq": {
        "env_key": "GROQ_API_KEY",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
        ],
        "daily_budget": 200,         # Groq free tier is generous
        "per_minute_budget": 30,
        "priority": 1,
        "is_paid": False,
    },
    "google_gemini": {
        "env_key": "GOOGLE_AI_API_KEY",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "default_model": "gemini-2.0-flash",
        "models": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ],
        "daily_budget": 1500,        # Gemini free tier is huge
        "per_minute_budget": 15,
        "priority": 2,
        "is_paid": False,
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "default_model": "openrouter/free",
        "extra_headers": {
            "HTTP-Referer": "https://github.com/sandeepnayakam/zero-cost-ai-business",
            "X-Title": "Zero-Cost AI Business Agent",
        },
        "models": [
            "openrouter/free",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "mistralai/mistral-nemo:free",
            "qwen/qwen-2.5-72b-instruct:free",
        ],
        "daily_budget": 50,          # OpenRouter free tier is tight
        "per_minute_budget": 20,
        "priority": 3,
        "is_paid": False,
    },
    "cerebras": {
        "env_key": "CEREBRAS_API_KEY",
        "endpoint": "https://api.cerebras.ai/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "default_model": "llama-3.3-70b",
        "models": [
            "llama-3.3-70b",
            "llama3.1-8b",
        ],
        "daily_budget": 50,
        "per_minute_budget": 10,
        "priority": 4,
        "is_paid": False,
    },
    "together": {
        "env_key": "TOGETHER_API_KEY",
        "endpoint": "https://api.together.xyz/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "models": [
            "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        ],
        "daily_budget": 50,
        "per_minute_budget": 10,
        "priority": 5,
        "is_paid": False,
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "daily_budget": 30,          # paid — keep tight
        "per_minute_budget": 50,
        "priority": 99,              # last resort
        "is_paid": True,
    },
}


# ----------------------------------------------------------------------------
# Quota state persistence
# ----------------------------------------------------------------------------
QUOTA_FILE = os.path.join("memory", "quota.json")
UTC_DATE_FMT = "%Y-%m-%d"


def _today_utc():
    return datetime.now(timezone.utc).strftime(UTC_DATE_FMT)


def _now_minute_key():
    """Returns a key like '2026-08-10T13:45' for per-minute bucketing."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def load_quota_state():
    """Load persisted quota state, or initialize fresh."""
    try:
        with open(QUOTA_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    # Reset daily counters if it's a new day
    today = _today_utc()
    for provider_name, info in state.items():
        if info.get("date") != today:
            info["requests_today"] = 0
            info["date"] = today
        # Clean out per-minute bucket entries older than 2 minutes
        bucket = info.get("minute_bucket", {})
        cutoff = _now_minute_key()
        info["minute_bucket"] = {
            k: v for k, v in bucket.items() if k >= cutoff
        }
    return state


def save_quota_state(state):
    os.makedirs(os.path.dirname(QUOTA_FILE), exist_ok=True)
    with open(QUOTA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def _init_provider_state(state, provider_name):
    if provider_name not in state:
        state[provider_name] = {
            "date": _today_utc(),
            "requests_today": 0,
            "minute_bucket": {},
            "last_used": None,
            "last_error": None,
            "last_error_at": None,
            "consecutive_errors": 0,
            "total_calls": 0,
            "total_errors": 0,
        }
    return state[provider_name]


def _has_quota(provider_def, info):
    today = _today_utc()
    if info.get("date") != today:
        info["requests_today"] = 0
        info["date"] = today
    if info["requests_today"] >= provider_def["daily_budget"]:
        return False, "daily budget exhausted"
    # Per-minute: count requests in the current minute bucket
    minute_key = _now_minute_key()
    bucket = info.get("minute_bucket", {})
    if bucket.get(minute_key, 0) >= provider_def["per_minute_budget"]:
        return False, "per-minute budget exhausted"
    return True, None


def _record_use(state, provider_name):
    info = _init_provider_state(state, provider_name)
    info["requests_today"] = (info.get("requests_today") or 0) + 1
    info["last_used"] = datetime.now(timezone.utc).isoformat()
    info["total_calls"] = (info.get("total_calls") or 0) + 1
    minute_key = _now_minute_key()
    bucket = info.get("minute_bucket", {})
    bucket[minute_key] = bucket.get(minute_key, 0) + 1
    info["minute_bucket"] = bucket
    info["consecutive_errors"] = 0


def _record_error(state, provider_name, error_msg):
    info = _init_provider_state(state, provider_name)
    info["last_error"] = (error_msg or "")[:500]
    info["last_error_at"] = datetime.now(timezone.utc).isoformat()
    info["consecutive_errors"] = (info.get("consecutive_errors") or 0) + 1
    info["total_errors"] = (info.get("total_errors") or 0) + 1


# ----------------------------------------------------------------------------
# Single provider call
# ----------------------------------------------------------------------------
def _call_provider(provider_name, provider_def, api_key, messages, model=None,
                   max_tokens=2000, temperature=0.7, timeout=45):
    headers = {
        provider_def["auth_header"]: provider_def["auth_prefix"] + api_key,
        "Content-Type": "application/json",
    }
    for k, v in provider_def.get("extra_headers", {}).items():
        headers[k] = v
    payload = {
        "model": model or provider_def["default_model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(
        provider_def["endpoint"], headers=headers, json=payload, timeout=timeout
    )
    resp.raise_for_status()
    data = resp.json()
    if not (data.get("choices") and len(data["choices"]) > 0):
        raise ValueError(f"empty choices from {provider_name}")
    msg = data["choices"][0].get("message") or {}
    content = msg.get("content")
    # Some providers return content=null when the response is filtered or
    # the model is overloaded. Also handle reasoning_content (used by some
    # OpenRouter deepseek/qwen models that put output in a separate field).
    if content is None:
        content = msg.get("reasoning_content") or ""
    if not isinstance(content, str):
        # Some providers return a list of content blocks (OpenAI-style);
        # concatenate any text blocks.
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            content = "\n".join(parts)
        else:
            content = str(content) if content is not None else ""
    content = content.strip()
    if not content:
        used = model or provider_def["default_model"]
        raise ValueError(f"empty/null content from {provider_name}/{used}")
    return content, (model or provider_def["default_model"])


# ----------------------------------------------------------------------------
# Public router API
# ----------------------------------------------------------------------------
def route_completion(messages, max_tokens=2000, temperature=0.7,
                     preferred_provider=None):
    """
    Try providers in quota-aware priority order until one succeeds.

    Returns: (content, used_provider, used_model, state) on success
    Raises:  RuntimeError if all providers fail
    """
    state = load_quota_state()

    # Build candidate list
    candidates = []
    for name, pdef in PROVIDERS.items():
        api_key = os.getenv(pdef["env_key"])
        if not api_key:
            continue
        info = _init_provider_state(state, name)
        # Skip a provider with too many consecutive errors (let it cool down)
        if info.get("consecutive_errors", 0) >= 5:
            continue
        has_q, reason = _has_quota(pdef, info)
        if not has_q:
            continue
        candidates.append((name, pdef))

    if not candidates:
        save_quota_state(state)
        raise RuntimeError(
            "No LLM providers available (no API keys set, all quotas exhausted, "
            "or all providers in cooldown)."
        )

    # Sort: preferred first, then by priority, then by fewest requests today
    if preferred_provider:
        candidates.sort(key=lambda c: (
            0 if c[0] == preferred_provider else 1,
            c[1]["priority"],
            state[c[0]].get("requests_today", 0),
        ))
    else:
        candidates.sort(key=lambda c: (
            c[1]["priority"],
            state[c[0]].get("requests_today", 0),
        ))

    errors = []
    for name, pdef in candidates:
        api_key = os.getenv(pdef["env_key"])
        # Try default model first, then alternates on failure
        models_to_try = [pdef["default_model"]] + [
            m for m in pdef["models"] if m != pdef["default_model"]
        ]
        for model_id in models_to_try:
            try:
                _record_use(state, name)
                save_quota_state(state)
                content, used_model = _call_provider(
                    name, pdef, api_key, messages,
                    model=model_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                save_quota_state(state)
                return content, name, used_model, state
            except requests.exceptions.RequestException as e:
                body = ""
                if getattr(e, "response", None) is not None:
                    body = (e.response.text or "")[:300]
                err = f"{name}/{model_id}: {e} | {body}"
                errors.append(err)
                _record_error(state, name, err)
                save_quota_state(state)
                # 429 = rate limit, try next model/provider immediately
                # 4xx other than 429 = bad model? try next model
                # 5xx/timeout = try next provider
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 429:
                    break  # don't try more models on this provider, move to next
                # For 400/404 (bad model), try next model. For 5xx, move on.
                if status and 400 <= status < 500 and status != 429:
                    continue  # try next model
                break  # 5xx or network error, move to next provider
            except (ValueError, KeyError, TypeError) as e:
                err = f"{name}/{model_id}: parse error: {e}"
                errors.append(err)
                _record_error(state, name, err)
                save_quota_state(state)
                break  # move to next provider

    save_quota_state(state)
    raise RuntimeError(
        "All LLM providers failed. Errors:\n" + "\n".join(errors[:10])
    )


def provider_status():
    """Return a human-readable summary of provider state for logging."""
    state = load_quota_state()
    lines = []
    for name, pdef in PROVIDERS.items():
        api_key = os.getenv(pdef["env_key"])
        info = state.get(name, {})
        if not api_key:
            lines.append(f"  - {name}: NOT CONFIGURED (no API key)")
            continue
        used = info.get("requests_today", 0)
        budget = pdef["daily_budget"]
        errs = info.get("consecutive_errors", 0)
        status = "OK" if errs < 5 else "COOLDOWN"
        lines.append(
            f"  - {name}: {used}/{budget} today, errs={errs}, {status}"
        )
    return "\n".join(lines)
