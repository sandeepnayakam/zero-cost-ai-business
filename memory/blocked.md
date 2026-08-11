# Blocked Actions Log

Example:
- [2026-07-31] Need to manually sign Ronin wallet transaction at [pending_link]
- [2026-07-30] Human verification required for Stripe payment processing

Key Rules:
1. Never omit a pending request requiring human action
2. Do not stall workflow waiting for pending item
3. Follow all pending requests marked with [URGENT]


[2026-08-10 14:32:25 UTC] GitHub deployment requires authenticated gh CLI (pending human action)


[2026-08-11 12:25:18 UTC] All LLM providers failed: All LLM providers failed. Errors:
google_gemini/gemini-2.0-flash: 404 Client Error: Not Found for url: https://generativelanguage.googleapis.com/v1beta/openai/chat/completions | [{
  "error": {
    "code": 404,
    "message": "This model models/gemini-2.0-flash is no longer available. Please update your code to use a newer model for the latest features and improvements. We recommend you to use the Interactions API (https://ai.google.dev/gemini-api/docs/migrate-to-interactio
google_gemini/gemini-
