from __future__ import annotations

import json
import os
from typing import Callable
from urllib import request


def _default_http_post(url: str, headers: dict[str, str], body: dict[str, object]) -> dict[str, object]:
    payload = json.dumps(body).encode("utf-8")
    http_request = request.Request(url, data=payload, headers=headers, method="POST")
    with request.urlopen(http_request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class OpenAICompatibleResponseProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        http_post: Callable[[str, dict[str, str], dict[str, object]], dict[str, object]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.http_post = http_post or _default_http_post

    def __call__(self, body: str) -> str:
        response = self.http_post(
            self.base_url,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Extraia conhecimento estruturado de Markdown e retorne apenas JSON com as chaves "
                            "'entities' e 'context'. Cada entity deve ter 'type' e 'name'. Cada context deve ter "
                            "'node_type', 'predicate' e 'content'."
                        ),
                    },
                    {"role": "user", "content": body},
                ],
            },
        )
        return str(response["choices"][0]["message"]["content"])


_QA_SYSTEM_PROMPT = (
    "Você é um assistente de segundo cérebro.\n\n"
    "Use APENAS o contexto fornecido.\n"
    "Não invente informações.\n"
    "Se não houver dados suficientes, diga claramente.\n"
    "Cite fontes quando disponíveis.\n"
    "Responda em português brasileiro."
)


class QAResponseProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        http_post: Callable[[str, dict[str, str], dict[str, object]], dict[str, object]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.http_post = http_post or _default_http_post

    def __call__(self, body: str) -> str:
        response = self.http_post(
            self.base_url,
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": _QA_SYSTEM_PROMPT},
                    {"role": "user", "content": body},
                ],
            },
        )
        return str(response["choices"][0]["message"]["content"])


def build_qa_provider_from_env() -> QAResponseProvider | None:
    api_key = os.getenv("BRAIN4ME_LLM_API_KEY", "").strip()
    model = os.getenv("BRAIN4ME_LLM_MODEL", "").strip()
    if not api_key or not model:
        return None

    base_url = os.getenv("BRAIN4ME_LLM_API_URL", "").strip() or "https://api.openai.com/v1/chat/completions"
    return QAResponseProvider(api_key=api_key, model=model, base_url=base_url)


def build_openai_compatible_provider_from_env() -> OpenAICompatibleResponseProvider | None:
    api_key = os.getenv("BRAIN4ME_LLM_API_KEY", "").strip()
    model = os.getenv("BRAIN4ME_LLM_MODEL", "").strip()
    if not api_key or not model:
        return None

    base_url = os.getenv("BRAIN4ME_LLM_API_URL", "").strip() or "https://api.openai.com/v1/chat/completions"
    return OpenAICompatibleResponseProvider(api_key=api_key, model=model, base_url=base_url)
