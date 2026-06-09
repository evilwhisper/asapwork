import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import JobListing

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class BaseScraper(ABC):
    source_name: str = ""

    def random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    @abstractmethod
    async def scrape(self, keywords: list[str], location: str) -> list[dict]:
        ...

    async def deduplicate_and_save(self, listings: list[dict], db: AsyncSession) -> list[JobListing]:
        cutoff = datetime.utcnow() - timedelta(days=30)
        saved = []

        for raw in listings:
            # Skip if older than 30 days
            posted = raw.get("posted_at")
            if posted and posted < cutoff:
                continue

            # Skip if already exists
            result = await db.execute(
                select(JobListing).where(
                    JobListing.source == self.source_name,
                    JobListing.external_id == raw["external_id"],
                )
            )
            if result.scalars().first():
                continue

            listing = JobListing(
                source=self.source_name,
                external_id=raw["external_id"],
                title=raw.get("title", ""),
                company=raw.get("company"),
                location=raw.get("location"),
                work_type=raw.get("work_type"),
                salary_text=raw.get("salary_text"),
                description=raw.get("description"),
                url=raw.get("url"),
                posted_at=raw.get("posted_at"),
                status="new",
            )
            db.add(listing)
            saved.append(listing)

        await db.commit()
        logger.info(f"[{self.source_name}] Saved {len(saved)} new listings")
        return saved

    async def _new_browser_context(self, playwright):
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=self.random_ua(),
            viewport={"width": 1920, "height": 1080},
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return browser, context
