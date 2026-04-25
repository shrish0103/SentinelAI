import httpx
from core.prompts import get_resume_messages
from core.config import Settings
from core.logger import get_logger


logger = get_logger(__name__)


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

    async def generate(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        """Returns (content, actual_model_name)"""
        raise NotImplementedError


class LocalResumeProvider(LLMProvider):
    name = "local"

    async def generate(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        question = messages[-1]["content"] if messages else ""
        lower_question = question.lower()
        if "fail" in lower_question:
            raise LLMServiceError(
                provider=self.name,
                model="sentinel-resume-local",
                category="forced-test-failure",
                detail="The local provider was forced to fail for testing.",
                hint="Use a different question or switch MODEL_PROVIDER.",
            )
        return f"Local fallback echo: {question}", "sentinel-resume-local"


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model_name: str) -> None:
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name

    async def generate(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        payload = {
            "model": self._model_name,
            "messages": messages,
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
            content = data["choices"][0]["message"]["content"].strip()
            actual_model = data.get("model", self._model_name)
            return content, actual_model
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

    async def generate(self, messages: list[dict[str, str]]) -> tuple[str, str]:
        combined_prompt = ""
        for m in messages:
            combined_prompt += f"{m['role'].upper()}: {m['content']}\n\n"
            
        payload = {
            "model": self._model_name,
            "prompt": combined_prompt,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
        except Exception as exc:
            raise LLMServiceError(
                provider=self.name,
                model=self._model_name,
                category="request-error",
                detail=str(exc),
                hint="Make sure Ollama is running and reachable.",
            ) from exc

        data = response.json()
        answer = data.get("response")
        return answer.strip(), self._model_name


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider = self._resolve_provider()
        self.provider_name = self._provider.name

    def _resolve_provider(self) -> LLMProvider:
        if self._settings.model_provider == "local":
            return LocalResumeProvider()
        if self._settings.model_provider == "openrouter":
            return OpenAICompatibleProvider(
                name="openrouter",
                base_url=self._settings.openrouter_base_url,
                api_key=self._settings.api_key,
                model_name=self._settings.model_name,
            )
        if self._settings.model_provider == "openai":
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
        raise ValueError(f"Unknown provider: {self._settings.model_provider}")

    async def _execute_generate(self, messages: list[dict[str, str]]) -> tuple[str, str, bool]:
        try:
            content, model = await self._provider.generate(messages=messages)
            return content, model, False
        except LLMServiceError as exc:
            if exc.category in ("upstream-http-error", "timeout") and self.provider_name == "openrouter" and self._settings.api_key:
                logger.warning(f"Primary model failed. Attempting fallback...")
                fallback_provider = OpenAICompatibleProvider(
                    name="openrouter",
                    base_url=self._settings.openrouter_base_url,
                    api_key=self._settings.api_key,
                    model_name=self._settings.fallback_model_name
                )
                content, model = await fallback_provider.generate(messages=messages)
                return content, model, True
            raise exc

    async def answer_question(self, question: str) -> tuple[str, str, bool]:
        """Answering questions with resume context (default behavior)."""
        messages = get_resume_messages(question)
        return await self._execute_generate(messages)

    async def answer_general_question(self, question: str) -> tuple[str, str, bool]:
        """Answering questions without resume context (General AI Mode)."""
        messages = [
            {"role": "system", "content": "You are a helpful and intelligent AI assistant. You answer any question based on your general knowledge. You are not restricted to any specific resume or portfolio context."},
            {"role": "user", "content": question}
        ]
        return await self._execute_generate(messages)
