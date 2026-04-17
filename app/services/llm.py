from core.config import Settings
import httpx


class LLMServiceError(Exception):
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        category: str,
        detail: str,
        status_code: int | None = None,
        hint: str | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.category = category
        self.detail = detail
        self.status_code = status_code
        self.hint = hint
        super().__init__(self.user_message)

    @property
    def user_message(self) -> str:
        parts = [
            f"Provider '{self.provider}' failed for model '{self.model}'.",
            f"Category: {self.category}.",
            f"Detail: {self.detail}.",
        ]
        if self.status_code is not None:
            parts.append(f"HTTP status: {self.status_code}.")
        if self.hint:
            parts.append(f"Hint: {self.hint}.")
        return " ".join(parts)

    @property
    def summary(self) -> str:
        return f"{self.provider}:{self.model} -> {self.category}"


class LLMProvider:
    name = "base"

    async def generate(self, question: str, context: str) -> str:
        raise NotImplementedError


class LocalResumeProvider(LLMProvider):
    name = "local"

    async def generate(self, question: str, context: str) -> str:
        lower_question = question.lower()
        if "fail" in lower_question:
            raise LLMServiceError(
                provider=self.name,
                model="sentinel-resume-local",
                category="forced-test-failure",
                detail="The local provider was forced to fail for testing.",
                hint="Use a different question or switch MODEL_PROVIDER.",
            )
        if "specialize" in lower_question or "specialise" in lower_question:
            return (
                "Shrish specializes in backend engineering, FastAPI, "
                "microservices, distributed systems, observability, and applied AI."
            )
        return f"Context: {context}\n\nQuestion: {question}"


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model_name: str) -> None:
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name

    async def generate(self, question: str, context: str) -> str:
        payload = {
            "model": self._model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the SentinelAI portfolio assistant. Answer based only on the "
                        "provided resume context. If the context is insufficient, say so briefly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Resume context:\n{context}\n\nQuestion:\n{question}",
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self.name == "openrouter":
            headers["HTTP-Referer"] = "https://sentinelai.local"
            headers["X-Title"] = "SentinelAI"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="timeout",
                detail="The upstream provider did not respond before the timeout expired",
                hint="Retry shortly or switch to a smaller model.",
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="network-connectivity",
                detail=f"Connection to {self._base_url} could not be established",
                hint="Check internet connectivity, DNS, firewall rules, or provider reachability.",
            ) from exc
        except httpx.RequestError as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="request-error",
                detail=str(exc),
                hint="Retry shortly and inspect provider/network health.",
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text.strip()[:400] or "Upstream provider returned an error response"
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="upstream-http-error",
                detail=detail,
                status_code=response.status_code,
                hint="Verify model availability, account credits, and provider-side limits.",
            ) from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="invalid-response-payload",
                detail="The provider response did not contain choices[0].message.content",
                hint="Inspect the upstream payload format and model compatibility.",
            ) from exc


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model_name: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name

    async def generate(self, question: str, context: str) -> str:
        payload = {
            "model": self._model_name,
            "prompt": (
                "You are the SentinelAI portfolio assistant. Answer based only on the "
                f"provided resume context.\n\nResume context:\n{context}\n\nQuestion:\n{question}"
            ),
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="timeout",
                detail="The Ollama endpoint did not respond before timeout",
                hint="Check whether the local Ollama model is loaded and healthy.",
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="network-connectivity",
                detail=f"Connection to {self._base_url} could not be established",
                hint="Make sure Ollama is running and reachable on the configured port.",
            ) from exc
        except httpx.RequestError as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="request-error",
                detail=str(exc),
                hint="Retry shortly and inspect the local inference service.",
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = response.text.strip()[:400] or "Ollama returned an error response"
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="upstream-http-error",
                detail=detail,
                status_code=response.status_code,
                hint="Check model availability and local resource pressure.",
            ) from exc

        data = response.json()
        answer = data.get("response")
        if not answer:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="invalid-response-payload",
                detail="The Ollama response did not include a response field",
                hint="Inspect the upstream payload format and model compatibility.",
            )
        return answer.strip()


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = self._resolve_provider()
        self.provider_name = self._provider.name
        self.using_fallback = self._settings.model_provider != self._provider.name

    def _resolve_provider(self) -> LLMProvider:
        if self._settings.model_provider == "local":
            return LocalResumeProvider()
        if self._settings.model_provider == "openrouter":
            if not self._settings.api_key:
                raise LLMServiceError(
                    provider="openrouter",
                    model=self._settings.model_name,
                    category="configuration-error",
                    detail="API_KEY is missing from the environment",
                    hint="Set API_KEY in .env before calling /resume/ask.",
                )
            return OpenAICompatibleProvider(
                name="openrouter",
                base_url=self._settings.openrouter_base_url,
                api_key=self._settings.api_key,
                model_name=self._settings.model_name,
            )
        if self._settings.model_provider == "openai":
            if not self._settings.api_key:
                raise LLMServiceError(
                    provider="openai",
                    model=self._settings.model_name,
                    category="configuration-error",
                    detail="API_KEY is missing from the environment",
                    hint="Set API_KEY in .env before calling /resume/ask.",
                )
            return OpenAICompatibleProvider(
                name="openai",
                base_url=self._settings.openai_base_url,
                api_key=self._settings.api_key,
                model_name=self._settings.model_name,
            )
        if self._settings.model_provider == "ollama":
            return OllamaProvider(
                base_url=self._settings.ollama_base_url,
                model_name=self._settings.model_name,
            )
        raise LLMServiceError(
            provider=self._settings.model_provider,
            model=self._settings.model_name,
            category="configuration-error",
            detail=f"Unknown provider '{self._settings.model_provider}'",
            hint="Choose one of: openrouter, openai, ollama, local.",
        )

    async def answer_question(self, question: str) -> str:
        return await self._provider.generate(question=question, context=self._settings.resume_context)
