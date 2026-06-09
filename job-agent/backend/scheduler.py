import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")

# Per-source lock so two concurrent triggers never overlap for the same board
_scraping_locks: dict[str, asyncio.Lock] = {}


def _lock_for(source: str) -> asyncio.Lock:
    if source not in _scraping_locks:
        _scraping_locks[source] = asyncio.Lock()
    return _scraping_locks[source]


# ── Public entry points ──────────────────────────────────────────

async def run_scrape_cycle(source: str = "all") -> dict:
    """
    Run one scrape+match cycle.
    source="all"  → all enabled scrapers in sequence
    source="seek" → only that board
    Returns a summary dict for the endpoint response.
    """
    from backend.database import AsyncSessionLocal
    from backend.models import ApiSettings, ScraperConfig, UserProfile
    from backend.config import encryption

    summary: dict[str, dict] = {}

    async with AsyncSessionLocal() as db:
        # Resolve which configs to run
        q = select(ScraperConfig)
        if source != "all":
            q = q.where(ScraperConfig.source == source)
        q = q.where(ScraperConfig.enabled == True)
        result = await db.execute(q)
        configs = result.scalars().all()

        if not configs:
            logger.info(f"[scheduler] No enabled scrapers for source='{source}'")
            return {"ok": False, "reason": "no_enabled_scrapers", "sources": []}

        # Load profile and active AI settings once
        profile_r = await db.execute(select(UserProfile))
        profile = profile_r.scalars().first()

        api_r = await db.execute(
            select(ApiSettings).where(
                ApiSettings.is_active == True,
                ApiSettings.api_key_enc.isnot(None),
            )
        )
        api_settings = api_r.scalars().first()

        ai_service = None
        if api_settings:
            try:
                from backend.services.ai_service import AIService
                ai_service = AIService(api_settings)
            except Exception as e:
                logger.warning(f"[scheduler] Could not init AI service: {e}")

        for config in configs:
            result = await _run_single_source(db, config, profile, ai_service, encryption)
            summary[config.source] = result

    return {"ok": True, "sources": summary}


async def _run_single_source(db, config, profile, ai_service, encryption) -> dict:
    """Scrape one board, deduplicate, run matching pipeline. Returns per-source stats."""
    from backend.services.matching_service import run_matching_pipeline

    lock = _lock_for(config.source)
    if lock.locked():
        logger.info(f"[{config.source}] Already running — skipping this cycle")
        return {"skipped": True, "reason": "already_running"}

    async with lock:
        keywords = json.loads(config.keywords) if config.keywords else []
        location = config.location or "Australia"

        if not keywords:
            logger.warning(f"[{config.source}] No keywords — skipping")
            return {"skipped": True, "reason": "no_keywords"}

        scraper = _get_scraper(config.source)
        if not scraper:
            return {"skipped": True, "reason": "unknown_source"}

        try:
            logger.info(f"[{config.source}] Scraping — keywords={keywords}, location={location}")

            if config.source == "linkedin_au":
                cookie = _decrypt_cookie(config.linkedin_session_cookie, encryption)
                listings = await scraper.scrape(keywords, location, session_cookie=cookie)
            else:
                listings = await scraper.scrape(keywords, location)

            logger.info(f"[{config.source}] Fetched {len(listings)} raw listings")

            saved = await scraper.deduplicate_and_save(listings, db)
            logger.info(f"[{config.source}] Saved {len(saved)} new listings")

            queued = 0
            generated = 0
            if saved and profile:
                passed = await run_matching_pipeline(saved, profile, ai_service)
                queued = len(passed)
                await db.commit()
                logger.info(f"[{config.source}] {queued}/{len(saved)} passed matching")

                # Auto-generate applications for newly queued listings
                if passed:
                    generated = await _auto_generate_applications(db, passed, profile, api_settings, ai_service)
                    logger.info(f"[{config.source}] Auto-generated {generated} application(s)")

            config.last_run = datetime.utcnow()
            await db.commit()

            return {"fetched": len(listings), "saved": len(saved), "queued": queued, "generated": generated}

        except Exception as exc:
            logger.error(f"[{config.source}] Scrape error: {exc}", exc_info=True)
            return {"error": str(exc)}


async def _auto_generate_applications(db, listings, profile, api_settings, ai_service) -> int:
    """
    Create Application records for newly queued listings.
    Skips listings that already have an application.
    Returns count of applications created.
    """
    from pathlib import Path
    from backend.models import Application, Document
    from backend.services.document_service import generate_cover_letter, generate_tailored_resume_pdf
    from backend.routers.profile import _serialize_profile

    # Load active documents once
    docs_r = await db.execute(select(Document).where(Document.is_active == True))
    active_docs = docs_r.scalars().all()
    active_resume = next((d for d in active_docs if d.type == "resume"), None)
    cl_samples = [d.parsed_text for d in active_docs if d.type == "cover_letter" and d.parsed_text]

    profile_dict = _serialize_profile(profile)
    generated = 0

    for listing in listings:
        # Skip if an application already exists for this job
        existing_r = await db.execute(
            select(Application).where(Application.job_id == listing.id)
        )
        if existing_r.scalars().first():
            continue

        cover_letter_text = None
        resume_path = None
        notes = None

        if active_resume and ai_service:
            try:
                cover_letter_text = await generate_cover_letter(
                    jd_text=listing.description or listing.title,
                    profile=profile_dict,
                    cover_letter_samples=cl_samples,
                    ai_service=ai_service,
                    tone=profile.tone_preference or "professional",
                )
                if active_resume.parsed_text:
                    pdf_bytes = await generate_tailored_resume_pdf(
                        base_resume_text=active_resume.parsed_text,
                        jd_text=listing.description or listing.title,
                        profile=profile_dict,
                        ai_service=ai_service,
                    )
                    upload_dir = Path(__file__).resolve().parent / "uploads" / "generated"
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(
                        dir=upload_dir, suffix="_resume.pdf", delete=False
                    )
                    tmp.write(pdf_bytes)
                    tmp.close()
                    resume_path = tmp.name
            except Exception as exc:
                logger.warning(f"[scheduler] Auto-gen failed for job {listing.id}: {exc}")
                notes = f"Auto-generation error: {exc}"
        elif not active_resume:
            notes = "No active resume — upload one in Profile."
        elif not ai_service:
            notes = "No active AI provider — add an API key in Settings."

        status = "pending"
        # Auto-approve if threshold set and score qualifies
        if (
            api_settings
            and api_settings.auto_approve_threshold is not None
            and listing.match_score is not None
            and listing.match_score >= api_settings.auto_approve_threshold
        ):
            status = "approved"

        app = Application(
            job_id=listing.id,
            cover_letter=cover_letter_text,
            resume_version=resume_path,
            status=status,
            notes=notes,
        )
        db.add(app)
        generated += 1

    if generated:
        await db.commit()

        # Rename temp resume files to use real application IDs
        apps_r = await db.execute(
            select(Application).where(
                Application.resume_version.isnot(None),
                Application.resume_version.like("%_resume.pdf"),
            )
        )
        for app in apps_r.scalars().all():
            if app.resume_version:
                old_path = Path(app.resume_version)
                if old_path.exists() and not old_path.name.startswith(str(app.id)):
                    new_path = old_path.parent / f"{app.id}_resume.pdf"
                    try:
                        old_path.rename(new_path)
                        app.resume_version = str(new_path)
                    except Exception:
                        pass
        await db.commit()

    return generated


# ── Scheduler setup ──────────────────────────────────────────────

async def setup_scheduler() -> None:
    """
    Called once from FastAPI lifespan after DB tables exist.
    Reads scraper_config rows and registers one IntervalTrigger job per enabled source.
    Also registers the daily email digest cron.
    """
    from backend.database import AsyncSessionLocal
    from backend.models import ScraperConfig

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ScraperConfig).where(ScraperConfig.enabled == True)
        )
        configs = result.scalars().all()

    for cfg in configs:
        _register_job(cfg.source, cfg.schedule_hours)

    # Daily digest at 08:00 UTC
    scheduler.add_job(
        _daily_digest_job,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_digest",
        replace_existing=True,
        max_instances=1,
    )

    logger.info(f"[scheduler] Registered {len(configs)} scraper job(s) + daily digest")


def reschedule_source(source: str, hours: int, enabled: bool) -> None:
    """
    Called by the settings router when a scraper config is updated via the UI.
    Adds, replaces, or removes the job for that source without a full restart.
    """
    job_id = f"scrape_{source}"
    if enabled:
        _register_job(source, hours)
    else:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
            logger.info(f"[scheduler] Removed job for {source}")


def _register_job(source: str, hours: int) -> None:
    job_id = f"scrape_{source}"
    scheduler.add_job(
        run_scrape_cycle,
        trigger=IntervalTrigger(hours=max(hours, 1)),
        args=[source],
        id=job_id,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    logger.info(f"[scheduler] Job registered: {source} every {hours}h (id={job_id})")


async def _daily_digest_job() -> None:
    """Send daily summary email via SMTP."""
    from backend.database import AsyncSessionLocal
    from backend.routers.notifications import send_daily_digest
    async with AsyncSessionLocal() as db:
        sent = await send_daily_digest(db)
    logger.info(f"[scheduler] Daily digest {'sent' if sent else 'skipped (no SMTP config)'}")


# ── Helpers ──────────────────────────────────────────────────────

def _get_scraper(source: str):
    try:
        if source == "seek":
            from backend.scrapers.seek import SeekScraper
            return SeekScraper()
        if source == "indeed_au":
            from backend.scrapers.indeed_au import IndeedAUScraper
            return IndeedAUScraper()
        if source == "linkedin_au":
            from backend.scrapers.linkedin_au import LinkedInAUScraper
            return LinkedInAUScraper()
        if source == "jora":
            from backend.scrapers.jora import JoraScraper
            return JoraScraper()
    except ImportError as e:
        logger.error(f"[scheduler] Cannot import scraper for {source}: {e}")
        return None
    logger.warning(f"[scheduler] Unknown source: {source}")
    return None


def _decrypt_cookie(encrypted: Optional[str], encryption) -> str:
    if not encrypted:
        return ""
    try:
        return encryption.decrypt(encrypted)
    except Exception as e:
        logger.warning(f"[scheduler] Cookie decrypt failed: {e}")
        return ""
