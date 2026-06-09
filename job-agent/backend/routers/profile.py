import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Document, UserProfile
from backend.schemas import DocumentSchema, UserProfileSchema
from backend.services.document_service import parse_document

router = APIRouter(prefix="/api/profile", tags=["profile"])

UPLOAD_ROOT = Path(__file__).resolve().parent.parent / "uploads"


@router.get("", response_model=UserProfileSchema)
async def get_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile))
    profile = result.scalars().first()
    if not profile:
        profile = UserProfile()
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return _serialize_profile(profile)


@router.put("", response_model=UserProfileSchema)
async def upsert_profile(data: UserProfileSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserProfile))
    profile = result.scalars().first()
    if not profile:
        profile = UserProfile()
        db.add(profile)

    for field in ["name", "email", "phone", "location", "target_salary_min",
                  "target_salary_max", "tone_preference"]:
        val = getattr(data, field)
        if val is not None:
            setattr(profile, field, val)

    for json_field in ["target_roles", "work_types", "industries",
                       "blacklist_keywords", "whitelist_companies"]:
        val = getattr(data, json_field)
        if val is not None:
            setattr(profile, json_field, json.dumps(val))

    await db.commit()
    await db.refresh(profile)
    return _serialize_profile(profile)


@router.get("/documents", response_model=list[DocumentSchema])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    return result.scalars().all()


@router.post("/documents/upload", response_model=DocumentSchema)
async def upload_document(
    file: UploadFile = File(...),
    type: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if type not in ("resume", "cover_letter"):
        raise HTTPException(400, "type must be 'resume' or 'cover_letter'")

    dest_dir = UPLOAD_ROOT / ("resumes" if type == "resume" else "cover_letters")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / file.filename

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    parsed = parse_document(str(dest))

    doc = Document(
        type=type,
        filename=file.filename,
        filepath=str(dest.relative_to(Path(__file__).resolve().parent.parent)),
        parsed_text=parsed,
        is_active=False,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Document not found")
    Path(doc.filepath).unlink(missing_ok=True)
    await db.delete(doc)
    await db.commit()
    return {"ok": True}


@router.put("/documents/{doc_id}/activate")
async def activate_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(404, "Document not found")

    # deactivate others of same type
    all_result = await db.execute(select(Document).where(Document.type == doc.type))
    for d in all_result.scalars().all():
        d.is_active = False

    doc.is_active = True
    await db.commit()
    return {"ok": True}


def _serialize_profile(p: UserProfile) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "email": p.email,
        "phone": p.phone,
        "location": p.location,
        "target_roles": json.loads(p.target_roles) if p.target_roles else [],
        "work_types": json.loads(p.work_types) if p.work_types else [],
        "industries": json.loads(p.industries) if p.industries else [],
        "blacklist_keywords": json.loads(p.blacklist_keywords) if p.blacklist_keywords else [],
        "whitelist_companies": json.loads(p.whitelist_companies) if p.whitelist_companies else [],
        "target_salary_min": p.target_salary_min,
        "target_salary_max": p.target_salary_max,
        "tone_preference": p.tone_preference,
    }
