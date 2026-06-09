import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_docx(filepath: str) -> str:
    import docx
    doc = docx.Document(filepath)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_pdf(filepath: str) -> str:
    import fitz
    doc = fitz.open(filepath)
    return "\n".join(page.get_text() for page in doc)


def parse_document(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".docx":
            return parse_docx(filepath)
        if ext == ".pdf":
            return parse_pdf(filepath)
        logger.warning(f"[document_service] Unsupported file type: {ext}")
        return ""
    except Exception as e:
        logger.error(f"[document_service] Failed to parse {filepath}: {e}")
        return ""


async def generate_cover_letter(
    jd_text: str,
    profile: dict,
    cover_letter_samples: list[str],
    ai_service,
    tone: str = "professional",
) -> str:
    samples_block = "\n\n---\n\n".join(cover_letter_samples[:2]) if cover_letter_samples else ""
    system = (
        f"You are an expert job application writer. Write in a {tone} style. "
        "Do not invent facts. Only use information from the candidate profile and their example cover letters. "
        "Write a complete, ready-to-send cover letter."
    )
    user = (
        f"Candidate Profile:\n{profile}\n\n"
        f"Example Cover Letters (for style reference):\n{samples_block}\n\n"
        f"Job Description:\n{jd_text[:4000]}"
    )
    return await ai_service.complete(system, user, max_tokens=800)


async def generate_tailored_resume_pdf(
    base_resume_text: str,
    jd_text: str,
    profile: dict,
    ai_service,
) -> bytes:
    system = (
        "You are a resume tailoring assistant. Identify the top 5 keywords from the job description "
        "that are missing from the resume. Suggest minimal, natural wording adjustments to existing bullet points "
        "to incorporate them. Never change job titles, dates, or employer names. "
        "Return JSON: {\"adjusted_resume\": \"<full resume text with adjustments applied>\"}"
    )
    user = f"Resume:\n{base_resume_text[:4000]}\n\nJob Description:\n{jd_text[:3000]}"

    import json
    raw = await ai_service.complete(system, user, max_tokens=2000)
    try:
        data = json.loads(raw.strip())
        tailored_text = data.get("adjusted_resume", base_resume_text)
    except Exception:
        tailored_text = base_resume_text

    return _render_resume_pdf(tailored_text, profile)


def _render_resume_pdf(text: str, profile: dict) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.units import cm
    import io

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    name = profile.get("name", "")
    if name:
        story.append(Paragraph(f"<b>{name}</b>", styles["Title"]))
        story.append(Spacer(1, 0.3*cm))

    for line in text.splitlines():
        if line.strip():
            story.append(Paragraph(line.strip(), styles["Normal"]))
        else:
            story.append(Spacer(1, 0.2*cm))

    doc.build(story)
    return buf.getvalue()
