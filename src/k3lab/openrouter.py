from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


@dataclass(frozen=True)
class Pricing:
    prompt_per_token: float
    completion_per_token: float


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    generation_id: str | None
    provider: str | None


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return str(content or "")


class OpenRouterClient:
    def __init__(self, api_key: str, opener: Callable[..., Any] = urllib.request.urlopen):
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self.api_key = api_key
        self.opener = opener

    def pricing(self, model: str, timeout: int = 30) -> Pricing:
        request = urllib.request.Request(
            OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        with self.opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        record = next((item for item in payload.get("data", []) if item.get("id") == model), None)
        if not record:
            raise RuntimeError(f"OpenRouter catalog does not contain model: {model}")
        pricing = record.get("pricing") or {}
        try:
            prompt = float(pricing["prompt"])
            completion = float(pricing["completion"])
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"OpenRouter catalog omitted usable pricing for: {model}") from error
        if prompt < 0 or completion < 0:
            raise RuntimeError(f"OpenRouter catalog returned invalid pricing for: {model}")
        return Pricing(prompt_per_token=prompt, completion_per_token=completion)

    def complete(self, model: str, prompt: str, max_tokens: int, timeout: int = 300) -> Completion:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return only the JSON object requested by the user."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "usage": {"include": True},
        }
        request = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/JoeProAI/kimi-k3-lab",
                "X-Title": "Kimi K3 OpenWeights Lab",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"OpenRouter HTTP {error.code}: {detail}") from error
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter response contained no choices")
        usage = payload.get("usage") or {}
        cost = usage.get("cost")
        if cost is None:
            raise RuntimeError("OpenRouter response omitted usage.cost; refusing an unpriced run")
        return Completion(
            text=_content_text((choices[0].get("message") or {}).get("content")),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            cost_usd=float(cost),
            generation_id=payload.get("id"),
            provider=payload.get("provider"),
        )
