import logging
from openai import AsyncOpenAI
from backend.config import encryption
from backend.models import ApiSettings
from backend.services.token_counter import token_counter

logger = logging.getLogger(__name__)

PROVIDER_BASE_URLS = {
    "openai": None,
    "anthropic": "https://api.anthropic.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "ollama": "http://localhost:11434/v1",
}

PROVIDER_HEADERS = {
    "anthropic": {"anthropic-version": "2023-06-01"},
}


class AIService:
    def __init__(self, settings: ApiSettings):
        self.settings = settings
        self._session_tokens = 0

        api_key = encryption.decrypt(settings.api_key_enc) if settings.api_key_enc else "ollama"
        base_url = settings.base_url or PROVIDER_BASE_URLS.get(settings.provider)
        extra_headers = PROVIDER_HEADERS.get(settings.provider, {})

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=extra_headers if extra_headers else None,
        )
        self.model = settings.model_name or "gpt-4o-mini"

    async def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
        )
        usage = response.usage
        if usage:
            self._session_tokens += usage.total_tokens
            token_counter.add(
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )
        return response.choices[0].message.content or ""

    async def score_job(self, jd_text: str, profile_text: str) -> float:
        """Returns 0.0–1.0 match score. Only called when ai_scorer_enabled=True."""
        system = (
            "You are a job matching assistant. Given a job description and a candidate profile, "
            "return only a JSON object like {\"score\": 0.85} where score is 0.0 to 1.0 indicating "
            "how well the candidate matches the role. No other output."
        )
        user = f"Job Description:\n{jd_text[:3000]}\n\nCandidate Profile:\n{profile_text[:2000]}"
        try:
            import json
            raw = await self.complete(system, user, max_tokens=20)
            data = json.loads(raw.strip())
            return float(data.get("score", 0.0))
        except Exception as e:
            logger.warning(f"[ai_service] score_job failed: {e}")
            return 0.0

    @property
    def session_tokens(self) -> int:
        return self._session_tokens
