"""Small provider-agnostic client for an OpenAI-compatible chat endpoint.

The agent layer never reads a student's Anumati locker directly. Callers must
explicitly provide the text/data that the agent is allowed to process.
"""
import json
import os

import requests
from rest_framework.exceptions import APIException


class AgentUnavailable(APIException):
    status_code = 503
    default_detail = "The AI agent is not configured. Set LLM_BASE_URL, LLM_API_KEY and LLM_MODEL."
    default_code = "agent_unavailable"


def chat(system_prompt, user_prompt, *, temperature=0.2, json_mode=False):
    base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "")
    model = os.getenv("LLM_MODEL", "")

    if not base_url or not api_key or not model:
        raise AgentUnavailable()

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        raise AgentUnavailable(f"AI provider request failed: {exc}") from exc


def json_chat(system_prompt, user_prompt, *, temperature=0.1):
    raw = chat(system_prompt, user_prompt, temperature=temperature, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AgentUnavailable("The AI agent returned invalid JSON.") from exc
