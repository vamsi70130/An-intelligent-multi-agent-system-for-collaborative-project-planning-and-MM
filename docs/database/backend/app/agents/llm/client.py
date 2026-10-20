"""
LLM abstraction layer (spec Step 28).

Supports:
  - LLM_PROVIDER=anthropic          (Anthropic Messages API)
  - LLM_PROVIDER=openai_compatible  (any OpenAI-compatible /chat/completions endpoint)
  - LLM_PROVIDER=ollama             (local Ollama server)

If LLM_PROVIDER is unset/unknown, or a required key is missing, this
module raises LLMNotConfiguredError rather than returning a fabricated
response. Callers (agents) must catch this and surface
NOT_CONFIGURED to the API/UI -- never silently invent AI output.
"""
import json

import httpx

from app.core.config import get_settings


class LLMNotConfiguredError(Exception):
    pass


class LLMCallError(Exception):
    pass


def _call_anthropic(system: str, user: str, settings) -> str:
    if not settings.LLM_API_KEY:
        raise LLMNotConfiguredError(
            "LLM_PROVIDER=anthropic but LLM_API_KEY is not set."
        )
    model = settings.LLM_MODEL or "claude-sonnet-4-5"
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.LLM_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4000,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=90)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise LLMCallError(f"Anthropic API error {e.response.status_code}: {e.response.text[:500]}")
    except httpx.RequestError as e:
        raise LLMCallError(f"Anthropic API request failed: {e}")
    data = resp.json()
    parts = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
    return "".join(parts)


def _call_openai_compatible(system: str, user: str, settings) -> str:
    if not settings.LLM_API_KEY:
        raise LLMNotConfiguredError(
            "LLM_PROVIDER=openai_compatible but LLM_API_KEY is not set."
        )
    if not settings.LLM_BASE_URL:
        raise LLMNotConfiguredError(
            "LLM_PROVIDER=openai_compatible but LLM_BASE_URL is not set."
        )
    model = settings.LLM_MODEL or "gpt-4o-mini"
    url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "content-type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
    }
    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=90)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise LLMCallError(f"OpenAI-compatible API error {e.response.status_code}: {e.response.text[:500]}")
    except httpx.RequestError as e:
        raise LLMCallError(f"OpenAI-compatible API request failed: {e}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_ollama(system: str, user: str, settings) -> str:
    base_url = settings.LLM_BASE_URL or "http://localhost:11434"
    model = settings.LLM_MODEL
    if not model:
        raise LLMNotConfiguredError("LLM_PROVIDER=ollama but LLM_MODEL is not set.")
    url = base_url.rstrip("/") + "/api/chat"
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
    }
    try:
        resp = httpx.post(url, json=body, timeout=180)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise LLMCallError(f"Ollama error {e.response.status_code}: {e.response.text[:500]}")
    except httpx.RequestError as e:
        raise LLMCallError(
            f"Could not reach Ollama at {base_url}. Is it running? ({e})"
        )
    data = resp.json()
    return data.get("message", {}).get("content", "")


def call_llm_json(system: str, user: str) -> dict:
    """Calls the configured LLM and parses a JSON object from its
    response. Raises LLMNotConfiguredError / LLMCallError on failure --
    never returns a fabricated dict."""
    settings = get_settings()
    provider = (settings.LLM_PROVIDER or "").strip().lower()

    if provider == "anthropic":
        raw = _call_anthropic(system, user, settings)
    elif provider == "openai_compatible":
        raw = _call_openai_compatible(system, user, settings)
    elif provider == "ollama":
        raw = _call_ollama(system, user, settings)
    else:
        raise LLMNotConfiguredError(
            "No LLM provider configured. Set LLM_PROVIDER to one of "
            "'anthropic', 'openai_compatible', or 'ollama' in your .env."
        )

    raw = raw.strip()
    # tolerate ```json fences
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMCallError(f"LLM did not return valid JSON: {e}. Raw output (truncated): {raw[:500]}")
