import httpx
import logging
from core.prompts import get_resume_messages
from core.config import Settings


logger = logging.getLogger(__name__)


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

    async def generate(self, question: str) -> tuple[str, str]:
        """Returns (content, actual_model_name)"""
        raise NotImplementedError


class LocalResumeProvider(LLMProvider):
    name = "local"

    async def generate(self, question: str) -> tuple[str, str]:
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
                "microservices, distributed systems, observability, and applied AI.",
                "sentinel-resume-local"
            )
        return f"Local fallback echo: {question}", "sentinel-resume-local"


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, api_key: str, model_name: str) -> None:
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name

    async def generate(self, question: str) -> str:
        payload = {
            "model": self._model_name,
            "messages": get_resume_messages(question),
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
            # OpenRouter often returns the actual model used even if an alias was requested
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

    async def generate(self, question: str) -> str:
        messages = get_resume_messages(question)
        # Ollama /api/generate usually takes a prompt, we'll combine system and user
        combined_prompt = f"{messages[0]['content']}\n\n{messages[1]['content']}"
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
        return answer.strip(), self._model_name


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

    async def answer_question(self, question: str) -> tuple[str, str, bool]:
        """Returns (content, actual_model, used_fallback)"""
        try:
            content, model = await self._provider.generate(question=question)
            logger.info(f"LLM Response generated using primary model: {model}")
            return content, model, False
        except LLMServiceError as exc:
            # If the primary provider fails due to upstream issues, try fallback
            if (
                exc.category in ("upstream-http-error", "timeout", "network-connectivity")
                and self.provider_name == "openrouter"
                and self._settings.api_key
            ):
                logger.warning(f"Primary OpenRouter model failed: {exc.summary}. Attempting fallback...")
                try:
                    fallback_provider = OpenAICompatibleProvider(
                        name="openrouter",
                        base_url=self._settings.openrouter_base_url,
                        api_key=self._settings.api_key,
                        model_name=self._settings.fallback_model_name
                    )
                    content, model = await fallback_provider.generate(question=question)
                    logger.info(f"LLM Response generated using FALLBACK model: {model}")
                    return content, model, True
                except Exception as fallback_exc:
                    logger.error(f"LLM Fallback also failed: {fallback_exc}")
            
            raise exc

