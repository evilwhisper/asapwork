from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import Application, JobListing
from backend.schemas import JobListingSchema

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListingSchema])
async def list_jobs(
    status: str | None = Query(None),
    source: str | None = Query(None),
    min_score: float | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(JobListing)
    if status:
        q = q.where(JobListing.status == status)
    if source:
        q = q.where(JobListing.source == source)
    if min_score is not None:
        q = q.where(JobListing.match_score >= min_score)
    if search:
        term = f"%{search}%"
        q = q.where(JobListing.title.ilike(term) | JobListing.company.ilike(term))
    q = q.order_by(JobListing.scraped_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def job_stats(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).select_from(JobListing))).scalar()
    queued = (await db.execute(select(func.count()).select_from(JobListing).where(JobListing.status == "queued"))).scalar()
    applied = (await db.execute(select(func.count()).select_from(JobListing).where(JobListing.status == "applied"))).scalar()
    submitted = (await db.execute(select(func.count()).select_from(Application).where(Application.status == "submitted"))).scalar()
    failed = (await db.execute(select(func.count()).select_from(Application).where(Application.status == "failed"))).scalar()
    return {"total": total, "queued": queued, "applied": applied, "submitted": submitted, "failed": failed}


@router.get("/{job_id}", response_model=JobListingSchema)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.put("/{job_id}/skip")
async def skip_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(404, "Job not found")
    job.status = "skipped"
    await db.commit()
    return {"ok": True}


@router.post("/{job_id}/queue")
async def queue_job(job_id: int, db: AsyncSession = Depends(get_db)):
    import asyncio
    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(404, "Job not found")
    job.status = "queued"
    await db.commit()
    # Auto-generate application in the background so the UI response is instant
    asyncio.create_task(_generate_for_job(job_id))
    return {"ok": True}


async def _generate_for_job(job_id: int) -> None:
    """Background task: generate an application for a manually queued job."""
    try:
        from backend.database import AsyncSessionLocal
        from backend.models import ApiSettings, JobListing, UserProfile
        from backend.scheduler import _auto_generate_applications
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            job_r = await db.execute(select(JobListing).where(JobListing.id == job_id))
            job = job_r.scalars().first()
            if not job:
                return

            profile_r = await db.execute(select(UserProfile))
            profile = profile_r.scalars().first()
            if not profile:
                return

            api_r = await db.execute(
                select(ApiSettings).where(
                    ApiSettings.is_active == True,
                    ApiSettings.api_key_enc.isnot(None),
                )
            )
            api_settings = api_r.scalars().first()

            ai_service = None
            if api_settings:
                from backend.services.ai_service import AIService
                from backend.config import encryption
                ai_service = AIService(api_settings)

            await _auto_generate_applications(db, [job], profile, api_settings, ai_service)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"[jobs] Background generation failed for job {job_id}: {exc}")


@router.post("/scrape-now")
async def scrape_now(
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from backend.scheduler import run_scrape_cycle
    import asyncio

    # Confirm at least one scraper is enabled before accepting the trigger
    from backend.models import ScraperConfig
    q = select(ScraperConfig).where(ScraperConfig.enabled == True)
    if source:
        q = q.where(ScraperConfig.source == source)
    result = await db.execute(q)
    if not result.scalars().first():
        raise HTTPException(400, "No enabled scrapers configured. Enable at least one board in Settings first.")

    target = source or "all"
    asyncio.create_task(run_scrape_cycle(target))
    return {"ok": True, "message": f"Scrape triggered for '{target}' — results appear within ~60s"}
