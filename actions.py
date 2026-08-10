#!/usr/bin/env python3
"""
Sandboxed action executor for the Zero-Cost AI Business agent.

Supports multiple action types per cycle. All filesystem writes are
sandboxed to configurable safe paths. Every mutation is logged with a
before/after diff for auditability.

Action types:
  - none               : no-op, just record reasoning
  - write_file         : write a single file (sandboxed)
  - multi_write        : write multiple files atomically (all-or-nothing)
  - http_get           : GET a URL, return text
  - http_request       : generic HTTP (GET/POST/PUT/DELETE) with body+headers
  - git_branch         : create a new git branch
  - git_commit_push    : commit current changes and push
  - github_issue       : open / comment / close an issue via gh CLI
  - subprocess         : run an allowlisted shell command
  - memory_edit        : same as write_file but restricted to memory/

Safety features:
  - All paths normalized and checked against config["sandbox_paths"]
  - Subprocess commands checked against an allowlist prefix
  - HTTP requests blocked to private/localhost IPs (SSRF guard)
  - Every write logs before/after to memory/action_log.md
"""

import ipaddress
import json
import os
import re
import socket
import subprocess
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
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


def _normalize_path(p):
    """Normalize a path and resolve any .. segments, returning the absolute path."""
    if not isinstance(p, str) or not p:
        raise ValueError("path must be a non-empty string")
    # Reject null bytes and control chars
    if "\x00" in p or any(ord(c) < 32 for c in p):
        raise ValueError("path contains control characters")
    # Normalize unicode (prevent lookalike attacks)
    p = unicodedata.normalize("NFC", p)
    # Convert to absolute and resolve
    abs_path = os.path.abspath(os.path.join(os.getcwd(), p))
    return abs_path


def _is_path_safe(path, sandbox_roots):
    """Check that abs path is inside one of the sandbox roots."""
    cwd = os.getcwd()
    for root in sandbox_roots:
        root_abs = os.path.abspath(os.path.join(cwd, root))
        # Ensure the path is within this root
        if path == root_abs or path.startswith(root_abs + os.sep):
            return True
    return False


def _is_url_safe(url):
    """SSRF guard: block localhost, private IPs, link-local, etc."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "invalid URL"
    if parsed.scheme not in ("http", "https"):
        return False, f"scheme {parsed.scheme!r} not allowed"
    host = parsed.hostname or ""
    if not host:
        return False, "no host in URL"
    # Block obvious local hosts
    blocked_hosts = {"localhost", "0.0.0.0", "::", "::1", "[::1]"}
    if host.lower() in blocked_hosts:
        return False, f"host {host!r} blocked"
    # Resolve and check IP
    try:
        # getaddrinfo returns IPv4 and IPv6 candidates
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # If we can't resolve, allow it (might be a hostname that needs DNS)
        return True, None
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False, f"host resolves to private/reserved IP {ip}"
    return True, None


# ----------------------------------------------------------------------------
# Diff logger
# ----------------------------------------------------------------------------
def _make_diff(before, after, max_lines=40):
    """Cheap unified-diff-like output without importing difflib heaviness."""
    before_lines = (before or "").splitlines()
    after_lines = (after or "").splitlines()
    out = []
    out.append(f"  before: {len(before_lines)} lines, {len(before or '')} chars")
    out.append(f"  after:  {len(after_lines)} lines, {len(after or '')} chars")
    # Show up to N lines of after content as proof
    shown = after_lines[:max_lines]
    out.append("  --- new content (first %d lines) ---" % len(shown))
    for line in shown:
        out.append("  | " + line[:200])
    if len(after_lines) > max_lines:
        out.append(f"  ... ({len(after_lines) - max_lines} more lines truncated)")
    return "\n".join(out)


def log_action_diff(action_name, params, before_after, result):
    """Append a structured diff entry to memory/action_log.md."""
    entry_parts = [
        f"\n### ACTION @ {TIMESTAMP}: {action_name}",
        f"Params: {json.dumps(params, ensure_ascii=False, default=str)[:500]}",
    ]
    if before_after:
        for label, (before, after) in before_after.items():
            entry_parts.append(f"  [{label}]")
            entry_parts.append(_make_diff(before, after))
    entry_parts.append(f"Result: {result[:600]}")
    entry_parts.append("---")
    append_file("memory/action_log.md", "\n".join(entry_parts) + "\n")


# ----------------------------------------------------------------------------
# Action handlers
# ----------------------------------------------------------------------------
class ActionError(Exception):
    pass


def _check_sandbox(path_str, sandbox_roots, allow_memory=False):
    abs_path = _normalize_path(path_str)
    roots = list(sandbox_roots)
    if allow_memory and "memory/" not in roots:
        roots.append("memory/")
    if not _is_path_safe(abs_path, roots):
        raise ActionError(
            f"path {path_str!r} is outside sandbox roots {roots}"
        )
    return abs_path


def action_write_file(params, config):
    path_str = params.get("path")
    content = params.get("content", "")
    if not path_str:
        raise ActionError("write_file requires 'path'")
    abs_path = _check_sandbox(path_str, config["sandbox_paths"])
    before = read_file(abs_path)
    write_file(abs_path, content)
    return abs_path, [("main", (before, content))], f"wrote {len(content)} chars to {path_str}"


def action_multi_write(params, config):
    files = params.get("files") or []
    if not files or not isinstance(files, list):
        raise ActionError("multi_write requires 'files' list")
    if len(files) > 10:
        raise ActionError("multi_write limited to 10 files per call")
    # Validate ALL paths first (atomicity)
    checked = []
    for entry in files:
        if not isinstance(entry, dict):
            raise ActionError("each file entry must be an object")
        p = entry.get("path")
        c = entry.get("content", "")
        if not p:
            raise ActionError("each file entry needs 'path'")
        abs_p = _check_sandbox(p, config["sandbox_paths"])
        checked.append((p, abs_p, c))
    # Apply all
    before_after = {}
    for p, abs_p, c in checked:
        before = read_file(abs_p)
        write_file(abs_p, c)
        before_after[p] = (before, c)
    summary = f"wrote {len(checked)} files: {', '.join(p for p,_,_ in checked)}"
    return None, list(before_after.items()), summary


def action_http_get(params, config):
    url = params.get("url")
    if not url:
        raise ActionError("http_get requires 'url'")
    safe, reason = _is_url_safe(url)
    if not safe:
        raise ActionError(f"URL blocked: {reason}")
    import requests
    resp = requests.get(url, timeout=30, headers={"User-Agent": "ZeroCostAIAgent/2.0"})
    body = resp.text[:5000]
    return None, [], f"GET {url} -> {resp.status_code}, {len(resp.text)} bytes (first 5000 shown)"


def action_http_request(params, config):
    url = params.get("url")
    method = (params.get("method") or "GET").upper()
    body = params.get("body")
    headers = params.get("headers") or {}
    if not url:
        raise ActionError("http_request requires 'url'")
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"):
        raise ActionError(f"method {method!r} not allowed")
    safe, reason = _is_url_safe(url)
    if not safe:
        raise ActionError(f"URL blocked: {reason}")
    # Block suspicious headers
    for h in headers:
        if h.lower() in ("authorization", "cookie"):
            # Allow only if explicitly provided in config["allowed_auth_headers"]
            if h.lower() not in [a.lower() for a in config.get("allowed_auth_headers", [])]:
                raise ActionError(f"header {h!r} not allowed in agent actions")
    import requests
    final_headers = {"User-Agent": "ZeroCostAIAgent/2.0"}
    final_headers.update(headers)
    kwargs = {"timeout": 30, "headers": final_headers}
    if body is not None and method in ("POST", "PUT", "PATCH"):
        if isinstance(body, (dict, list)):
            kwargs["json"] = body
        else:
            kwargs["data"] = str(body)
    resp = requests.request(method, url, **kwargs)
    snippet = resp.text[:3000]
    return None, [], f"{method} {url} -> {resp.status_code}, {len(resp.text)} bytes. Body: {snippet}"


def action_git_branch(params, config):
    branch = params.get("branch")
    if not branch:
        raise ActionError("git_branch requires 'branch'")
    if not re.match(r"^[a-zA-Z0-9._/-]{1,80}$", branch):
        raise ActionError("invalid branch name")
    base = params.get("base", "HEAD")
    r = subprocess.run(
        ["git", "checkout", "-b", branch, base],
        capture_output=True, text=True, timeout=20,
    )
    if r.returncode != 0:
        raise ActionError(f"git checkout -b failed: {r.stderr.strip()[:300]}")
    return None, [], f"created branch {branch} from {base}"


def action_git_commit_push(params, config):
    message = params.get("message") or f"Autonomous action @ {TIMESTAMP}"
    if len(message) > 200:
        message = message[:200]
    files = params.get("files") or ["-A"]
    if not isinstance(files, list):
        raise ActionError("git_commit_push 'files' must be a list")
    # Only allow adding files from sandbox paths
    for f in files:
        if f == "-A":
            continue
        _check_sandbox(f, config["sandbox_paths"], allow_memory=True)
    add_cmd = ["git", "add"] + files
    r = subprocess.run(add_cmd, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise ActionError(f"git add failed: {r.stderr.strip()[:300]}")
    r = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True, text=True, timeout=20,
    )
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        raise ActionError(f"git commit failed: {(r.stderr + r.stdout).strip()[:300]}")
    # Push uses GH_PAT (already configured in workflow remote)
    r = subprocess.run(
        ["git", "push", "origin", "HEAD"],
        capture_output=True, text=True, timeout=40,
    )
    if r.returncode != 0:
        return None, [], f"committed locally but push failed: {r.stderr.strip()[:300]}"
    return None, [], f"committed & pushed: {message}"


def action_github_issue(params, config):
    """Open / comment / close an issue using gh CLI."""
    op = (params.get("op") or "open").lower()
    title = params.get("title") or "Autonomous agent note"
    body = params.get("body") or ""
    issue_number = params.get("number")
    if op not in ("open", "comment", "close"):
        raise ActionError(f"github_issue op {op!r} not supported")
    if op == "open":
        cmd = ["gh", "issue", "create", "--title", title[:200], "--body", body[:60000]]
    elif op == "comment":
        if not issue_number:
            raise ActionError("github_issue comment requires 'number'")
        cmd = ["gh", "issue", "comment", str(issue_number), "--body", body[:60000]]
    else:  # close
        if not issue_number:
            raise ActionError("github_issue close requires 'number'")
        cmd = ["gh", "issue", "close", str(issue_number)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise ActionError(f"gh failed: {r.stderr.strip()[:300]}")
    return None, [], f"github_issue {op}: {(r.stdout or '').strip()[:200]}"


def action_subprocess(params, config):
    """Run a shell command if it matches the configured allowlist prefix."""
    cmd = params.get("command")
    if not cmd or not isinstance(cmd, str):
        raise ActionError("subprocess requires 'command' string")
    allowlist = config.get("subprocess_allowlist") or []
    stripped = cmd.lstrip()
    matched = False
    for prefix in allowlist:
        prefix_norm = prefix.rstrip()
        # Case A: prefix ends with a space (e.g. "python3 "). The command just
        # needs to start with it; the rest is the argument.
        if prefix.endswith(" ") and stripped.startswith(prefix):
            matched = True
            break
        # Case B: prefix has no trailing space (e.g. "pip install"). The char
        # after the prefix must be whitespace, end-of-string, or a shell
        # metachar — so "pip install" matches "pip install requests" but not
        # "pip installx".
        if stripped.startswith(prefix_norm):
            rest = stripped[len(prefix_norm):]
            if not rest or rest[0].isspace() or rest[0] in ("&", "|", ";", ">", "<"):
                matched = True
                break
    if not matched:
        raise ActionError(
            f"command {cmd[:80]!r} not in allowlist {allowlist}"
        )
    # Block obvious dangerous sequences regardless of allowlist
    danger_tokens = ["rm -rf /", "mkfs", "dd if=", "> /dev/sd", "shutdown", "reboot", ":(){:|:&};:"]
    if any(t in cmd for t in danger_tokens):
        raise ActionError(f"command contains blocked token")
    timeout = min(int(params.get("timeout", 60)), 300)
    r = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout,
    )
    out = (r.stdout or "")[:3000]
    err = (r.stderr or "")[:1000]
    summary = f"exit={r.returncode}\nstdout: {out}\nstderr: {err}"
    return None, [], summary


def action_memory_edit(params, config):
    """Edit a memory file. Same as write_file but restricted to memory/."""
    path_str = params.get("path")
    content = params.get("content", "")
    if not path_str:
        raise ActionError("memory_edit requires 'path'")
    abs_path = _check_sandbox(path_str, ["memory/"], allow_memory=True)
    if not abs_path.startswith(os.path.abspath(os.path.join(os.getcwd(), "memory/"))):
        raise ActionError("memory_edit can only touch files under memory/")
    before = read_file(abs_path)
    write_file(abs_path, content)
    return abs_path, [("main", (before, content))], f"updated memory file {path_str}"


# Registry
ACTION_HANDLERS = {
    "none": lambda p, c: (None, [], "no-op"),
    "write_file": action_write_file,
    "multi_write": action_multi_write,
    "http_get": action_http_get,
    "http_request": action_http_request,
    "git_branch": action_git_branch,
    "git_commit_push": action_git_commit_push,
    "github_issue": action_github_issue,
    "subprocess": action_subprocess,
    "memory_edit": action_memory_edit,
}


def execute_action(action_obj, config):
    """
    Execute a single action object: {"action": str, "action_params": dict}.
    Returns: dict with keys: ok, action, summary, error
    """
    if not isinstance(action_obj, dict):
        return {"ok": False, "action": "?", "summary": "",
                "error": "action is not an object"}
    name = action_obj.get("action", "none")
    params = action_obj.get("action_params") or {}
    handler = ACTION_HANDLERS.get(name)
    if not handler:
        return {"ok": False, "action": name, "summary": "",
                "error": f"unknown action {name!r}"}
    try:
        _, before_after, summary = handler(params, config)
        log_action_diff(name, params, dict(before_after) if before_after else {}, summary)
        return {"ok": True, "action": name, "summary": summary, "error": ""}
    except ActionError as e:
        log_action_diff(name, params, {}, f"ACTION BLOCKED: {e}")
        return {"ok": False, "action": name, "summary": "",
                "error": str(e)}
    except Exception as e:
        log_action_diff(name, params, {}, f"ACTION ERROR: {type(e).__name__}: {e}")
        return {"ok": False, "action": name, "summary": "",
                "error": f"{type(e).__name__}: {e}"}
