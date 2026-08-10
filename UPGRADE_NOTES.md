# Zero-Cost AI Business — Upgrade Notes (v1 → v2)

This document explains everything that changed, how to set it up, and how to operate the upgraded agent.

---

## TL;DR — What's new

| Capability                | v1                                  | v2                                              |
|---------------------------|-------------------------------------|-------------------------------------------------|
| LLM providers             | 1 (OpenRouter)                      | up to 6 (OpenRouter, Groq, Gemini, OpenAI, Cerebras, Together) with auto-failover |
| Run frequency             | every 2 hours                       | every 15 minutes                                |
| Actions per cycle         | 1                                   | up to 3 (configurable)                          |
| Action types              | write_file, http_get                | write_file, multi_write, http_get, http_request (POST/PUT/PATCH/DELETE), git_branch, git_commit_push, github_issue, subprocess, memory_edit |
| Quota tracking            | none                                | per-provider daily + per-minute budgets, persisted to memory/quota.json |
| Safety                    | kill switch (PAUSE file)            | kill switch + sandboxed paths + subprocess allowlist + SSRF guard + daily action budget + diff logging |
| Self-evolution            | none                                | can open issues/PRs to propose code changes; can edit its own prompt via memory_edit |
| Audit trail               | basic                               | before/after diff for every mutation in action_log.md |

---

## File layout

```
.
├── agent.py                    # Main entry point (v2)
├── llm_router.py               # Multi-provider quota-aware router
├── actions.py                  # Sandboxed action executor
├── config.json                 # Runtime tunables (budgets, sandbox, allowlist)
├── requirements.txt            # Python deps (just `requests` for now)
├── .github/workflows/loop.yml  # 15-min cron, multi-provider secrets
├── prompts/
│   └── business_prompt.md      # Updated system prompt (multi-action schema)
├── memory/                     # State files (preserved from v1)
│   ├── state.md
│   ├── blocked.md
│   ├── revenue.md
│   ├── pending_requests.md
│   ├── consult_request.md
│   ├── consult_response.md
│   ├── action_log.md
│   ├── quota.json              # NEW: persisted quota state (auto-created)
│   └── daily_action_count.json # NEW: daily action counter (auto-created)
├── docs/                       # Sandbox root: documentation outputs
├── site/                       # Sandbox root: GitHub Pages content
└── scripts/                    # Sandbox root: utility scripts
```

---

## Setup steps

### 1. Replace repo files

Copy these files from this upgrade package into your GitHub repo, overwriting the v1 versions:
- `agent.py`
- `prompts/business_prompt.md`
- `.github/workflows/loop.yml`

Copy these new files into the repo root:
- `llm_router.py`
- `actions.py`
- `config.json`
- `requirements.txt`

Create empty directories if they don't exist:
```bash
mkdir -p docs site scripts
```

The `memory/` folder is preserved as-is — your existing state, revenue log, and pending requests carry over.

### 2. Add API keys as GitHub secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret. Add any subset of:

| Secret name             | Where to get it                                                        | Free tier notes                                |
|-------------------------|------------------------------------------------------------------------|------------------------------------------------|
| `OPENROUTER_API_KEY`    | https://openrouter.ai/keys                                             | Already had this in v1. ~50 req/day free       |
| `GROQ_API_KEY`          | https://console.groq.com/keys                                          | 30 req/min, ~1000 req/day free, super fast     |
| `GOOGLE_AI_API_KEY`     | https://aistudio.google.com/app/apikey                                 | 1500 req/day on Gemini 2.0 Flash free tier     |
| `CEREBRAS_API_KEY`      | https://cerebras.ai/                                                   | Free Llama 3.3 70B, very fast                  |
| `TOGETHER_API_KEY`      | https://api.together.ai/settings/api-keys                              | $5 free credit, multiple free models           |
| `OPENAI_API_KEY`        | https://platform.openai.com/api-keys                                   | Paid. Set as last-resort fallback only         |
| `GH_PAT`                | https://github.com/settings/tokens (classic, repo scope)               | Already had this in v1. Used for git push + gh CLI |

**Recommended minimum:** `OPENROUTER_API_KEY` + `GROQ_API_KEY` + `GOOGLE_AI_API_KEY` will give you ~1500+ free requests/day total — more than enough for a 15-minute cadence.

### 3. Enable GitHub Pages (optional, recommended)

If you want the agent to publish websites it builds:
1. Repo → Settings → Pages
2. Source: Deploy from branch
3. Branch: `main`, folder: `/site`
4. Save

The agent can now write HTML/CSS/JS to `site/` and they'll be live at `https://<your-username>.github.io/<repo-name>/` within a minute.

### 4. Verify the workflow

Go to Actions tab → "Zero-Cost Business Autonomous Loop v2" → Enable workflow. Trigger it manually with "Run workflow" button to test.

You should see in the run logs:
- `[+] LLM responded via <provider>/<model>`
- `[+] Run complete at <ts> | provider=... | actions=N/M | daily=N/M`

If you see `[-] No LLM provider API keys set` — your secret names don't match. Double-check spelling.

If you see `[-] All LLM providers failed` — every provider returned an error. Check `memory/blocked.md` in the next commit; it'll have the error details.

---

## Tuning

Edit `config.json` to change runtime behavior. Commit + push to apply.

| Setting                  | What it does                                                            | Default |
|--------------------------|-------------------------------------------------------------------------|---------|
| `max_actions_per_run`    | Hard cap on actions per 15-min cycle                                    | 3       |
| `max_actions_per_day`    | Hard cap on actions per UTC day (prevents runaway loops)                | 60      |
| `max_paid_spend_per_day_usd` | Future-use cost ceiling for paid providers (not yet enforced)      | 0.50    |
| `sandbox_paths`          | Top-level dirs the agent can write to                                   | docs/, site/, memory/, prompts/, scripts/ |
| `subprocess_allowlist`   | Command prefixes the agent can run via `subprocess` action              | pip install, python3, node, npm, git, gh, ls, cat, echo, mkdir, curl, wget |
| `llm.max_tokens`         | Max response tokens per LLM call                                        | 3000    |
| `llm.temperature`        | Sampling temperature                                                    | 0.7     |
| `providers_enabled`      | Toggle each provider on/off (independent of whether key is set)         | Groq, Gemini, OpenRouter on; others off |

To change the cron schedule, edit `.github/workflows/loop.yml`:
```yaml
schedule:
  - cron: '*/15 * * * *'  # every 15 min
  # - cron: '*/30 * * * *'  # every 30 min (safer if you only have 1-2 providers)
  # - cron: '0 * * * *'     # every hour
```

---

## Operating the agent

### Pause it
Create a file named `PAUSE` in the repo root (any content, including empty). The next scheduled run will detect it and exit immediately without taking any action. Delete the file to resume.

```bash
# Locally
touch PAUSE && git add PAUSE && git commit -m "pause agent" && git push
# To resume
git rm PAUSE && git commit -m "resume agent" && git push
```

### Watch what it's doing
- **`memory/state.md`** — short summary of the most recent run
- **`memory/action_log.md`** — full audit log with diffs (grows over time)
- **`memory/quota.json`** — per-provider quota state, reset daily
- **`memory/blocked.md`** — anything that needs your attention
- **`memory/pending_requests.md`** — actions only you can do
- **GitHub Actions tab** — run logs with detailed `[+]` / `[!]` lines
- **GitHub Issues tab** — agent can open issues to track its own backlog or propose changes

### Consult workflow (unchanged from v1)
- Agent writes a hard strategic question to `memory/consult_request.md` (at most once per day)
- You paste the question into Claude / ChatGPT free chat, get an answer
- Write the answer into `memory/consult_response.md`
- Agent reads the answer on the next run

### Force a provider preference
The router prefers providers by priority (Groq < Gemini < OpenRouter < Cerebras < Together < OpenAI). If you want to force a specific provider (e.g. to save OpenRouter quota for backups), edit `llm_router.py` `PROVIDERS` dict and bump the `priority` value. Lower number = higher priority.

---

## Safety guarantees

1. **No writes outside sandbox.** All `write_file` / `multi_write` / `memory_edit` paths are normalized and checked against `config.sandbox_paths`. The agent CANNOT modify `agent.py`, `actions.py`, `llm_router.py`, `config.json`, or `.github/workflows/*.yml` — those require a manual PR.
2. **No shell escape.** `subprocess` action validates the command starts with one of the allowlist prefixes AND rejects dangerous tokens (`rm -rf /`, `mkfs`, `dd if=`, etc.) regardless.
3. **No SSRF.** All HTTP actions resolve the hostname and block private/loopback/link-local/multicast IPs.
4. **No auth header leakage.** `Authorization` and `Cookie` headers in `http_request` are blocked unless explicitly added to `config.allowed_auth_headers`.
5. **Daily action budget.** Hard cap via `max_actions_per_day`. Once hit, remaining actions in all subsequent cycles that day are skipped.
6. **Kill switch.** `PAUSE` file halts all runs immediately.
7. **Full audit.** Every mutation is logged with a before/after diff in `memory/action_log.md`. You can `git log memory/action_log.md` to see every change.

---

## Troubleshooting

**"All LLM providers failed"** — check `memory/blocked.md` for the error. Most common causes:
- API key typo or wrong secret name
- Free tier exhausted (will reset at midnight UTC)
- Provider outage (the router will skip it for 5 consecutive-error cooldown)

**"No LLM provider API keys set"** — none of the `*_API_KEY` env vars reached the workflow. Verify secret names match exactly (case-sensitive) and that the workflow `env:` block references them.

**Workflow not triggering** — GitHub disables scheduled workflows after 60 days of repo inactivity. Push any commit to re-enable. Also confirm the workflow is enabled in the Actions tab.

**Agent stuck in a loop** — create the `PAUSE` file, wait for the run to acknowledge it, then investigate `memory/state.md`. You can also delete `memory/quota.json` to reset quota counters if they look corrupted.

**Quota state looks wrong** — `memory/quota.json` is plain JSON, safe to edit or delete. It'll be regenerated on the next run.
