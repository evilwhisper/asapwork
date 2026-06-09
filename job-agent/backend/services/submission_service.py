import asyncio
import logging
import random
import re
import smtplib
from collections import deque
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Rate limiter ─────────────────────────────────────────────────

class _SubmissionRateLimiter:
    """
    Process-level rate limiter.
    Enforces max_per_hour and min_gap_seconds across all submission methods.
    """
    def __init__(self):
        self._history: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def check(self, max_per_hour: int = 10, min_gap_seconds: int = 180) -> tuple[bool, str]:
        """Returns (allowed, reason). Caller must still await the random pre-submit delay."""
        async with self._lock:
            now = datetime.utcnow().timestamp()
            cutoff = now - 3600
            while self._history and self._history[0] < cutoff:
                self._history.popleft()

            if len(self._history) >= max_per_hour:
                return False, f"Rate limit: {max_per_hour} submissions/hour reached"

            if self._history and (now - self._history[-1]) < min_gap_seconds:
                remaining = int(min_gap_seconds - (now - self._history[-1]))
                return False, f"Rate limit: minimum gap not met ({remaining}s remaining)"

            self._history.append(now)
            return True, "ok"


rate_limiter = _SubmissionRateLimiter()


# ── CAPTCHA detection ────────────────────────────────────────────

async def _has_captcha(page) -> bool:
    """Return True if a CAPTCHA iframe is visible on the page."""
    try:
        frames = page.frames
        for frame in frames:
            url = frame.url
            if "recaptcha" in url or "hcaptcha" in url or "captcha" in url:
                return True
        # Also check for visible CAPTCHA elements
        captcha_el = await page.query_selector(
            'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], '
            '.g-recaptcha, .h-captcha, #captcha'
        )
        return captcha_el is not None
    except Exception:
        return False


def _flag_captcha(application) -> None:
    application.status = "failed"
    application.notes = "CAPTCHA encountered — open the job URL manually and apply there."


# ── Email submission ─────────────────────────────────────────────

async def submit_by_email(application, job, profile: dict, smtp_settings) -> bool:
    """Submit via email. Returns True on success."""
    email_match = re.search(r"[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}", job.description or "")
    to_email = email_match.group(0) if email_match else None

    if not to_email:
        application.status = "failed"
        application.notes = "No application email found in job description"
        logger.warning(f"[submission] No email found in JD for job {job.id}")
        return False

    from backend.config import encryption
    smtp_pass = encryption.decrypt(smtp_settings.smtp_pass_enc) if smtp_settings.smtp_pass_enc else ""

    msg = MIMEMultipart()
    msg["From"] = smtp_settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = f"Application for {job.title} — {profile.get('name', '')}"
    msg.attach(MIMEText(application.cover_letter or "", "plain"))

    if application.resume_version:
        resume_path = Path(application.resume_version)
        if resume_path.exists():
            with resume_path.open("rb") as f:
                part = MIMEApplication(f.read(), Name=resume_path.name)
                part["Content-Disposition"] = f'attachment; filename="{resume_path.name}"'
                msg.attach(part)

    try:
        with smtplib.SMTP(smtp_settings.smtp_host, smtp_settings.smtp_port or 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_settings.smtp_user, smtp_pass)
            server.send_message(msg)

        application.status = "submitted"
        application.submitted_at = datetime.utcnow()
        application.submission_method = "email"
        logger.info(f"[submission] Email sent for job {job.id} → {to_email}")
        return True

    except Exception as e:
        application.status = "failed"
        application.notes = f"Email error: {e}"
        logger.error(f"[submission] Email failed for job {job.id}: {e}")
        return False


# ── Seek form submission ─────────────────────────────────────────

async def submit_seek(application, job, profile: dict) -> bool:
    """Fill and submit a Seek job application form using Playwright."""
    from playwright.async_api import async_playwright
    from backend.scrapers.base import USER_AGENTS

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        try:
            await page.goto(job.url, wait_until="domcontentloaded", timeout=30000)

            if await _has_captcha(page):
                _flag_captcha(application)
                return False

            # Find Apply button — try multiple selectors in priority order
            apply_btn = None
            for selector in [
                'a[data-automation="job-detail-apply"]',
                'a[data-automation="applyButton"]',
                'a:has-text("Apply for this job")',
                'button:has-text("Apply")',
                'a:has-text("Apply now")',
            ]:
                apply_btn = await page.query_selector(selector)
                if apply_btn:
                    break

            if not apply_btn:
                application.status = "failed"
                application.notes = "Could not find Apply button on page"
                return False

            # Human-like mouse movement before clicking
            box = await apply_btn.bounding_box()
            if box:
                await page.mouse.move(
                    box["x"] + box["width"] / 2 + random.uniform(-3, 3),
                    box["y"] + box["height"] / 2 + random.uniform(-3, 3),
                )
                await asyncio.sleep(random.uniform(0.3, 0.8))

            await apply_btn.click()
            await asyncio.sleep(random.uniform(1.5, 2.5))
            await page.wait_for_load_state("domcontentloaded", timeout=15000)

            if await _has_captcha(page):
                _flag_captcha(application)
                return False

            # Fill form fields with human-like delays
            async def fill(selectors: list[str], value: str) -> None:
                for sel in selectors:
                    el = await page.query_selector(sel)
                    if el:
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        await el.click()
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        await el.fill(value)
                        return

            await fill(
                ['input[name="name"]', 'input[placeholder*="name" i]', 'input[id*="name" i]'],
                profile.get("name", ""),
            )
            await fill(
                ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]'],
                profile.get("email", ""),
            )
            await fill(
                ['input[type="tel"]', 'input[name="phone"]', 'input[placeholder*="phone" i]'],
                profile.get("phone", ""),
            )
            await fill(
                ['textarea[name*="cover" i]', 'textarea[placeholder*="cover" i]', 'textarea[id*="cover" i]'],
                application.cover_letter or "",
            )

            # Resume upload
            if application.resume_version and Path(application.resume_version).exists():
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    await file_input.set_input_files(application.resume_version)
                    await asyncio.sleep(random.uniform(1.0, 2.0))

            await asyncio.sleep(random.uniform(1.0, 2.0))

            if await _has_captcha(page):
                _flag_captcha(application)
                return False

            # Submit
            submit_btn = None
            for selector in [
                'button[type="submit"]',
                'button:has-text("Submit application")',
                'button:has-text("Submit")',
                'button:has-text("Apply now")',
                'input[type="submit"]',
            ]:
                submit_btn = await page.query_selector(selector)
                if submit_btn:
                    break

            if not submit_btn:
                application.status = "failed"
                application.notes = "Could not find Submit button"
                return False

            url_before = page.url
            await submit_btn.click()

            try:
                await page.wait_for_load_state("domcontentloaded", timeout=12000)
            except Exception:
                pass

            await asyncio.sleep(random.uniform(1.5, 2.5))

            if await _has_captcha(page):
                _flag_captcha(application)
                return False

            # Detect success
            success_el = await page.query_selector(
                ':text("application has been submitted"), '
                ':text("successfully applied"), '
                ':text("thank you for applying"), '
                ':text("application received")'
            )
            url_changed = page.url != url_before and (
                "confirmation" in page.url or "success" in page.url or "thank" in page.url
            )

            if success_el or url_changed:
                application.status = "submitted"
                application.submitted_at = datetime.utcnow()
                application.submission_method = "seek_form"
                logger.info(f"[submission] Seek form submitted for job {job.id}")
                return True
            else:
                application.status = "failed"
                application.notes = "Submitted but could not confirm success — check manually"
                logger.warning(f"[submission] Seek submit unconfirmed for job {job.id}")
                return False

        except Exception as exc:
            application.status = "failed"
            application.notes = f"Seek submission error: {exc}"
            logger.error(f"[submission] Seek error for job {job.id}: {exc}", exc_info=True)
            return False
        finally:
            await browser.close()


# ── LinkedIn Easy Apply ──────────────────────────────────────────

async def submit_linkedin_easy_apply(
    application, job, profile: dict, session_cookie: str
) -> bool:
    """Multi-step LinkedIn Easy Apply via Playwright."""
    from playwright.async_api import async_playwright
    from backend.scrapers.base import USER_AGENTS

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        if session_cookie:
            await context.add_cookies([{
                "name": "li_at",
                "value": session_cookie,
                "domain": ".linkedin.com",
                "path": "/",
            }])

        page = await context.new_page()

        try:
            await page.goto(job.url, wait_until="domcontentloaded", timeout=30000)

            # Detect expired cookie
            if "login" in page.url or "authwall" in page.url:
                application.status = "failed"
                application.notes = "LinkedIn cookie expired — paste a fresh li_at in Settings"
                return False

            if await _has_captcha(page):
                _flag_captcha(application)
                return False

            # Find Easy Apply button
            easy_apply = None
            for selector in [
                'button:has-text("Easy Apply")',
                '.jobs-apply-button',
                'button[data-control-name="jobdetails_topcard_inapply"]',
            ]:
                easy_apply = await page.query_selector(selector)
                if easy_apply:
                    break

            if not easy_apply:
                application.status = "failed"
                application.notes = "Easy Apply button not found — may not be an Easy Apply listing"
                return False

            await asyncio.sleep(random.uniform(0.5, 1.2))
            await easy_apply.click()
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # Walk through multi-step form (up to 10 steps)
            for step in range(10):
                if await _has_captcha(page):
                    _flag_captcha(application)
                    return False

                # Fill visible text inputs
                inputs = await page.query_selector_all('input[type="text"]:visible, input[type="tel"]:visible')
                for inp in inputs:
                    label_el = await page.query_selector(f'label[for="{await inp.get_attribute("id")}"]')
                    label_text = (await label_el.inner_text()).lower() if label_el else ""
                    current_val = await inp.input_value()
                    if current_val:
                        continue  # already filled
                    if "phone" in label_text:
                        await inp.fill(profile.get("phone", ""))
                    elif "city" in label_text or "location" in label_text:
                        await inp.fill(profile.get("location", ""))
                    elif "name" in label_text:
                        await inp.fill(profile.get("name", ""))
                    await asyncio.sleep(random.uniform(0.3, 0.8))

                # Fill cover letter textarea if present
                cl_area = await page.query_selector('textarea:visible')
                if cl_area:
                    current_val = await cl_area.input_value()
                    if not current_val and application.cover_letter:
                        await cl_area.fill(application.cover_letter)
                        await asyncio.sleep(random.uniform(0.5, 1.0))

                # Upload resume if file input visible
                if application.resume_version and Path(application.resume_version).exists():
                    file_input = await page.query_selector('input[type="file"]:visible')
                    if file_input:
                        await file_input.set_input_files(application.resume_version)
                        await asyncio.sleep(random.uniform(1.0, 2.0))

                # Answer work-authorisation questions (Yes to everything safe)
                radio_yes = await page.query_selector_all('label:has-text("Yes")')
                for r in radio_yes:
                    await r.click()
                    await asyncio.sleep(random.uniform(0.2, 0.5))

                await asyncio.sleep(random.uniform(0.8, 1.5))

                # Decide next action: Submit > Review > Next
                submit_btn = await page.query_selector('button:has-text("Submit application")')
                if submit_btn:
                    await submit_btn.click()
                    await asyncio.sleep(random.uniform(2.0, 3.0))

                    # Confirm submission
                    confirm_el = await page.query_selector(
                        ':text("application was sent"), :text("applied"), :text("thank you")'
                    )
                    if confirm_el or "post-apply" in page.url:
                        application.status = "submitted"
                        application.submitted_at = datetime.utcnow()
                        application.submission_method = "linkedin_easy_apply"
                        logger.info(f"[submission] LinkedIn Easy Apply submitted for job {job.id}")
                        return True
                    else:
                        application.status = "failed"
                        application.notes = "LinkedIn submitted but confirmation not detected"
                        return False

                review_btn = await page.query_selector('button:has-text("Review")')
                next_btn = await page.query_selector('button:has-text("Next")')
                btn = review_btn or next_btn
                if btn:
                    await btn.click()
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                else:
                    break  # No more navigation buttons — bail out

            application.status = "failed"
            application.notes = "LinkedIn Easy Apply: reached step limit without submitting"
            return False

        except Exception as exc:
            application.status = "failed"
            application.notes = f"LinkedIn Easy Apply error: {exc}"
            logger.error(f"[submission] LinkedIn error for job {job.id}: {exc}", exc_info=True)
            return False
        finally:
            await browser.close()


# ── Plugin stubs ─────────────────────────────────────────────────

async def submit_workday(application, job, profile: dict) -> bool:
    logger.warning("[submission] Workday plugin not active in MVP")
    raise NotImplementedError("Workday submission not active in MVP")


async def submit_greenhouse(application, job, profile: dict) -> bool:
    logger.warning("[submission] Greenhouse plugin not active in MVP")
    raise NotImplementedError("Greenhouse submission not active in MVP")


# ── Main dispatcher ──────────────────────────────────────────────

async def submit_application(application, job, profile: dict, db) -> bool:
    """
    Choose submission method and enforce rate limits.
    Priority: Seek form → LinkedIn Easy Apply → email fallback.
    """
    from sqlalchemy import select
    from backend.models import ApiSettings, ScraperConfig
    from backend.config import encryption

    # Load submission rate settings
    api_r = await db.execute(select(ApiSettings))
    all_settings = api_r.scalars().all()
    smtp_cfg = next((s for s in all_settings if s.smtp_host), None)
    rate_cfg = next((s for s in all_settings), None)

    max_per_hour = rate_cfg.max_submissions_per_hour if rate_cfg else 10
    min_gap_sec = (rate_cfg.min_gap_minutes if rate_cfg else 3) * 60

    allowed, reason = await rate_limiter.check(max_per_hour, min_gap_sec)
    if not allowed:
        application.status = "failed"
        application.notes = f"Rate limited: {reason}"
        logger.warning(f"[submission] Rate limited for job {job.id}: {reason}")
        return False

    # Random pre-submission delay (human-like)
    await asyncio.sleep(random.uniform(30, 120))

    try:
        if job.source == "seek":
            return await submit_seek(application, job, profile)

        if job.source == "linkedin_au":
            # Load encrypted cookie from scraper config
            cfg_r = await db.execute(
                select(ScraperConfig).where(ScraperConfig.source == "linkedin_au")
            )
            cfg = cfg_r.scalars().first()
            cookie = ""
            if cfg and cfg.linkedin_session_cookie:
                try:
                    cookie = encryption.decrypt(cfg.linkedin_session_cookie)
                except Exception:
                    pass
            return await submit_linkedin_easy_apply(application, job, profile, cookie)

    except NotImplementedError:
        pass
    except Exception as exc:
        logger.warning(f"[submission] Primary method failed for job {job.id}: {exc} — trying email")

    # Email fallback for all sources
    if smtp_cfg:
        return await submit_by_email(application, job, profile, smtp_cfg)

    application.status = "failed"
    application.notes = "No submission method available (no SMTP config and source-specific submission failed)"
    return False
