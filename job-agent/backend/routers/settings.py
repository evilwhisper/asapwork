import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.config import encryption
from backend.database import get_db
from backend.models import ApiSettings, ScraperConfig
from backend.schemas import ApiSettingsSchema, ScraperConfigSchema, TestConnectionResponse
from backend.services.token_counter import token_counter

router = APIRouter(prefix="/api/settings", tags=["settings"])

MASKED = "••••••••"


@router.get("/api", response_model=list[ApiSettingsSchema])
async def get_api_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiSettings))
    settings = result.scalars().all()
    return [_mask_keys(s) for s in settings]


@router.post("/api", response_model=ApiSettingsSchema)
async def upsert_api_settings(data: ApiSettingsSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiSettings).where(ApiSettings.provider == data.provider))
    s = result.scalars().first()
    if not s:
        s = ApiSettings(provider=data.provider)
        db.add(s)

    if data.api_key and data.api_key != MASKED:
        s.api_key_enc = encryption.encrypt(data.api_key)
    if data.smtp_pass and data.smtp_pass != MASKED:
        s.smtp_pass_enc = encryption.encrypt(data.smtp_pass)

    for field in ["base_url", "model_name", "is_active", "ai_scorer_enabled",
                  "smtp_host", "smtp_port", "smtp_user", "notify_email",
                  "max_submissions_per_hour", "min_gap_minutes", "auto_submit",
                  "auto_approve_threshold"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(s, field, val)

    await db.commit()
    await db.refresh(s)
    return _mask_keys(s)


@router.delete("/api/{settings_id}")
async def delete_api_settings(settings_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiSettings).where(ApiSettings.id == settings_id))
    s = result.scalars().first()
    if not s:
        raise HTTPException(404, "Settings not found")
    await db.delete(s)
    await db.commit()
    return {"ok": True}


@router.post("/api/{settings_id}/test", response_model=TestConnectionResponse)
async def test_connection(settings_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiSettings).where(ApiSettings.id == settings_id))
    s = result.scalars().first()
    if not s:
        raise HTTPException(404, "Settings not found")
    if not s.api_key_enc and s.provider != "ollama":
        return TestConnectionResponse(success=False, message="No API key stored for this provider", latency_ms=0)

    from backend.services.ai_service import AIService
    service = AIService(s)
    start = time.monotonic()
    try:
        await service.complete("You are a test assistant.", "Reply with the word OK only.", max_tokens=5)
        latency = int((time.monotonic() - start) * 1000)
        return TestConnectionResponse(success=True, message="Connection successful", latency_ms=latency)
    except Exception as e:
        latency = int((time.monotonic() - start) * 1000)
        return TestConnectionResponse(success=False, message=str(e), latency_ms=latency)


@router.get("/tokens")
async def get_token_usage():
    return token_counter.snapshot()


@router.delete("/tokens")
async def reset_token_usage():
    token_counter.reset()
    return {"ok": True}


@router.get("/scrapers", response_model=list[ScraperConfigSchema])
async def get_scraper_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScraperConfig))
    configs = result.scalars().all()
    # Ensure all sources exist
    sources = {c.source for c in configs}
    for source in ["seek", "indeed_au", "linkedin_au", "jora"]:
        if source not in sources:
            db.add(ScraperConfig(source=source))
    await db.commit()
    result = await db.execute(select(ScraperConfig))
    return result.scalars().all()


@router.put("/scrapers/{source}", response_model=ScraperConfigSchema)
async def update_scraper_config(source: str, data: ScraperConfigSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScraperConfig).where(ScraperConfig.source == source))
    config = result.scalars().first()
    if not config:
        config = ScraperConfig(source=source)
        db.add(config)

    config.enabled = data.enabled
    if data.keywords is not None:
        config.keywords = json.dumps(data.keywords)
    if data.location is not None:
        config.location = data.location
    if data.schedule_hours is not None:
        config.schedule_hours = data.schedule_hours
    if data.linkedin_session_cookie and data.linkedin_session_cookie != MASKED:
        config.linkedin_session_cookie = encryption.encrypt(data.linkedin_session_cookie)

    await db.commit()
    await db.refresh(config)

    # Hot-reload the scheduler job so the change takes effect without a restart
    try:
        from backend.scheduler import reschedule_source
        reschedule_source(source, config.schedule_hours, config.enabled)
    except Exception as e:
        logger.warning(f"[settings] Could not reschedule {source}: {e}")

    return config


def _mask_keys(s: ApiSettings) -> dict:
    return {
        "id": s.id,
        "provider": s.provider,
        "api_key": MASKED if s.api_key_enc else None,
        "base_url": s.base_url,
        "model_name": s.model_name,
        "is_active": s.is_active,
        "ai_scorer_enabled": s.ai_scorer_enabled,
        "smtp_host": s.smtp_host,
        "smtp_port": s.smtp_port,
        "smtp_user": s.smtp_user,
        "smtp_pass": MASKED if s.smtp_pass_enc else None,
        "notify_email": s.notify_email,
        "max_submissions_per_hour": s.max_submissions_per_hour,
        "min_gap_minutes": s.min_gap_minutes,
        "auto_submit": s.auto_submit,
        "auto_approve_threshold": s.auto_approve_threshold,
    }
