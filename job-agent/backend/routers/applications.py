import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models import Application, ApiSettings, Document, JobListing, UserProfile
from backend.schemas import ApplicationSchema

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationSchema])
async def list_applications(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Application)
    if status:
        q = q.where(Application.status == status)
    q = q.order_by(Application.created_at.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def application_stats(db: AsyncSession = Depends(get_db)):
    counts = {}
    for s in ["pending", "approved", "rejected", "submitted", "failed"]:
        n = (await db.execute(select(func.count()).select_from(Application).where(Application.status == s))).scalar()
        counts[s] = n
    return counts


@router.get("/{app_id}", response_model=ApplicationSchema)
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.post("/generate/{job_id}", response_model=ApplicationSchema)
async def generate_application(job_id: int, db: AsyncSession = Depends(get_db)):
    job_result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = job_result.scalars().first()
    if not job:
        raise HTTPException(404, "Job not found")

    # Load profile
    profile_result = await db.execute(select(UserProfile))
    profile = profile_result.scalars().first()
    if not profile:
        raise HTTPException(400, "Complete your profile before generating applications")

    # Load active API settings
    api_result = await db.execute(
        select(ApiSettings).where(ApiSettings.is_active == True, ApiSettings.api_key_enc.isnot(None))
    )
    api_settings = api_result.scalars().first()

    # Load active documents
    docs_result = await db.execute(select(Document).where(Document.is_active == True))
    active_docs = docs_result.scalars().all()
    active_resume = next((d for d in active_docs if d.type == "resume"), None)
    cover_letter_samples = [d.parsed_text for d in active_docs if d.type == "cover_letter" and d.parsed_text]

    cover_letter_text = None
    resume_path = None
    notes = None

    if not active_resume:
        notes = "No active resume found — upload and activate a resume in Profile."
    elif not api_settings:
        notes = "No active AI provider — add an API key in Settings to generate cover letters."
    else:
        try:
            from backend.services.ai_service import AIService
            from backend.services.document_service import generate_cover_letter, generate_tailored_resume_pdf
            from backend.routers.profile import _serialize_profile

            ai = AIService(api_settings)
            profile_dict = _serialize_profile(profile)
            jd_text = job.description or job.title

            cover_letter_text = await generate_cover_letter(
                jd_text=jd_text,
                profile=profile_dict,
                cover_letter_samples=cover_letter_samples,
                ai_service=ai,
                tone=profile.tone_preference or "professional",
            )

            if active_resume.parsed_text:
                pdf_bytes = await generate_tailored_resume_pdf(
                    base_resume_text=active_resume.parsed_text,
                    jd_text=jd_text,
                    profile=profile_dict,
                    ai_service=ai,
                )
                upload_dir = Path(__file__).resolve().parent.parent / "uploads" / "generated"
                upload_dir.mkdir(parents=True, exist_ok=True)
                # Temporary ID — will update after commit
                import tempfile, os
                tmp = tempfile.NamedTemporaryFile(dir=upload_dir, suffix="_resume.pdf", delete=False)
                tmp.write(pdf_bytes)
                tmp.close()
                resume_path = tmp.name

        except Exception as e:
            notes = f"Generation error: {e}"

    app = Application(
        job_id=job_id,
        status="pending",
        cover_letter=cover_letter_text,
        resume_version=resume_path,
        notes=notes,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)

    # Rename generated resume to use real application ID
    if resume_path and Path(resume_path).exists():
        final_path = Path(resume_path).parent / f"{app.id}_resume.pdf"
        Path(resume_path).rename(final_path)
        app.resume_version = str(final_path)
        await db.commit()

    return app


@router.put("/{app_id}/approve")
async def approve_application(app_id: int, db: AsyncSession = Depends(get_db)):
    import asyncio
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")
    app.status = "approved"
    await db.commit()

    # If auto_submit is on, trigger submission in the background immediately
    api_r = await db.execute(select(ApiSettings).where(ApiSettings.auto_submit == True))
    if api_r.scalars().first():
        asyncio.create_task(_submit_in_background(app.id))

    return {"ok": True}


@router.put("/{app_id}/reject")
async def reject_application(app_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")
    app.status = "rejected"
    await db.commit()
    return {"ok": True}


@router.put("/{app_id}", response_model=ApplicationSchema)
async def update_application(app_id: int, data: ApplicationSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")
    if data.cover_letter is not None:
        app.cover_letter = data.cover_letter
    if data.notes is not None:
        app.notes = data.notes
    await db.commit()
    await db.refresh(app)
    return app


@router.get("/{app_id}/resume")
async def download_resume(app_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalars().first()
    if not app or not app.resume_version:
        raise HTTPException(404, "Resume not found")
    path = Path(app.resume_version)
    if not path.exists():
        raise HTTPException(404, "Resume file not found on disk")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.post("/{app_id}/submit")
async def submit_application_endpoint(app_id: int, db: AsyncSession = Depends(get_db)):
    import asyncio
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalars().first()
    if not app:
        raise HTTPException(404, "Application not found")
    if app.status not in ("approved", "failed"):
        raise HTTPException(400, f"Cannot submit application with status '{app.status}'")

    asyncio.create_task(_submit_in_background(app_id))
    return {"ok": True, "message": "Submission started in background"}


async def _submit_in_background(app_id: int) -> None:
    """Run submission service for an approved application outside a request context."""
    import logging
    _log = logging.getLogger(__name__)
    try:
        from backend.database import AsyncSessionLocal
        from backend.models import Application, JobListing, UserProfile
        from backend.services.submission_service import submit_application
        from backend.routers.profile import _serialize_profile

        async with AsyncSessionLocal() as db:
            app_r = await db.execute(select(Application).where(Application.id == app_id))
            app = app_r.scalars().first()
            if not app:
                return

            job_r = await db.execute(select(JobListing).where(JobListing.id == app.job_id))
            job = job_r.scalars().first()
            if not job:
                return

            profile_r = await db.execute(select(UserProfile))
            profile = profile_r.scalars().first()
            profile_dict = _serialize_profile(profile) if profile else {}

            await submit_application(app, job, profile_dict, db)
            await db.commit()
            _log.info(f"[applications] Submission complete for app {app_id}: status={app.status}")
    except Exception as exc:
        _log.error(f"[applications] Background submission failed for app {app_id}: {exc}", exc_info=True)
