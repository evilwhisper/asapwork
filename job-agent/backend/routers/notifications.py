import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import encryption
from backend.database import get_db
from backend.models import ApiSettings, Application, JobListing

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("/test")
async def send_test_email(db: AsyncSession = Depends(get_db)):
    smtp = await _get_smtp(db)
    if not smtp:
        raise HTTPException(400, "No SMTP configuration found. Add SMTP settings in Settings first.")
    try:
        _send(smtp, smtp.notify_email or smtp.smtp_user, "Job Agent — Test Email",
              "<p>This is a test email from your <strong>Job Agent</strong>.</p>")
        return {"ok": True, "message": "Test email sent"}
    except Exception as e:
        raise HTTPException(500, f"Failed to send email: {e}")


async def send_daily_digest(db: AsyncSession) -> bool:
    """Send the daily summary email. Called by scheduler at 08:00."""
    smtp = await _get_smtp(db)
    if not smtp:
        return False

    since = datetime.utcnow() - timedelta(hours=24)

    jobs_found = (await db.execute(
        select(func.count()).select_from(JobListing)
        .where(JobListing.scraped_at >= since)
    )).scalar() or 0

    apps_generated = (await db.execute(
        select(func.count()).select_from(Application)
        .where(Application.created_at >= since)
    )).scalar() or 0

    apps_submitted = (await db.execute(
        select(func.count()).select_from(Application)
        .where(Application.status == "submitted", Application.submitted_at >= since)
    )).scalar() or 0

    apps_failed = (await db.execute(
        select(func.count()).select_from(Application)
        .where(Application.status == "failed", Application.created_at >= since)
    )).scalar() or 0

    apps_pending = (await db.execute(
        select(func.count()).select_from(Application)
        .where(Application.status == "pending")
    )).scalar() or 0

    html = f"""
<h2>Job Agent — Daily Digest</h2>
<p>Here's what happened in the last 24 hours:</p>
<table style="border-collapse:collapse;width:100%;max-width:400px">
  <tr><td style="padding:6px 12px;background:#f3f4f6"><strong>Jobs found</strong></td>
      <td style="padding:6px 12px">{jobs_found}</td></tr>
  <tr><td style="padding:6px 12px;background:#f3f4f6"><strong>Applications generated</strong></td>
      <td style="padding:6px 12px">{apps_generated}</td></tr>
  <tr><td style="padding:6px 12px;background:#f3f4f6"><strong>Submitted</strong></td>
      <td style="padding:6px 12px" style="color:green">{apps_submitted}</td></tr>
  <tr><td style="padding:6px 12px;background:#f3f4f6"><strong>Failed</strong></td>
      <td style="padding:6px 12px">{apps_failed}</td></tr>
  <tr><td style="padding:6px 12px;background:#f3f4f6"><strong>Awaiting approval</strong></td>
      <td style="padding:6px 12px">{apps_pending}</td></tr>
</table>
<p style="margin-top:16px;color:#6b7280;font-size:13px">
  Open <a href="http://localhost:5173">Job Agent</a> to review the queue.
</p>
"""
    try:
        to = smtp.notify_email or smtp.smtp_user
        _send(smtp, to, "Job Agent — Daily Digest", html)
        return True
    except Exception:
        return False


# ── Helpers ──────────────────────────────────────────────────────

async def _get_smtp(db: AsyncSession):
    result = await db.execute(
        select(ApiSettings).where(ApiSettings.smtp_host.isnot(None))
    )
    return result.scalars().first()


def _send(smtp_cfg: ApiSettings, to: str, subject: str, html: str) -> None:
    password = encryption.decrypt(smtp_cfg.smtp_pass_enc) if smtp_cfg.smtp_pass_enc else ""
    msg = MIMEMultipart("alternative")
    msg["From"] = smtp_cfg.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(smtp_cfg.smtp_host, smtp_cfg.smtp_port or 587, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_cfg.smtp_user, password)
        server.send_message(msg)
