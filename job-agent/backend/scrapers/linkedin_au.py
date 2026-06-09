import asyncio
import logging
import random
from urllib.parse import quote_plus
from backend.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInAUScraper(BaseScraper):
    source_name = "linkedin_au"

    async def scrape(self, keywords: list[str], location: str, session_cookie: str = "") -> list[dict]:
        from playwright.async_api import async_playwright
        kw = quote_plus(" ".join(keywords))
        loc = quote_plus(location)
        url = f"https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}&f_WT=2"
        listings = []

        async with async_playwright() as p:
            browser, context = await self._new_browser_context(p)
            try:
                if session_cookie:
                    await context.add_cookies([{
                        "name": "li_at",
                        "value": session_cookie,
                        "domain": ".linkedin.com",
                        "path": "/",
                    }])
                else:
                    logger.warning("[linkedin_au] No session cookie — results may be limited")

                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Detect cookie expiry / login redirect
                if "login" in page.url or "authwall" in page.url:
                    logger.warning("[linkedin_au] Cookie expired or invalid — login redirect detected")
                    return []

                await page.wait_for_selector(".jobs-search__results-list li", timeout=15000)
                cards = await page.query_selector_all(".jobs-search__results-list li")

                for card in cards:
                    try:
                        title_el = await card.query_selector("h3.base-search-card__title")
                        title = await title_el.inner_text() if title_el else ""

                        company_el = await card.query_selector("h4.base-search-card__subtitle")
                        company = await company_el.inner_text() if company_el else ""

                        location_el = await card.query_selector("span.job-search-card__location")
                        location_text = await location_el.inner_text() if location_el else ""

                        link_el = await card.query_selector("a.base-card__full-link")
                        job_url = await link_el.get_attribute("href") if link_el else ""
                        job_id = job_url.split("-")[-1].split("?")[0] if job_url else ""

                        listing = {
                            "external_id": job_id,
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_text.strip(),
                            "url": job_url,
                        }

                        if job_url:
                            await asyncio.sleep(random.uniform(4, 8))
                            desc = await self._fetch_description(context, job_url)
                            listing["description"] = desc

                        listings.append(listing)
                        await asyncio.sleep(random.uniform(4, 8))
                    except Exception as e:
                        logger.warning(f"[linkedin_au] Card parse error: {e}")
                        continue
            finally:
                await browser.close()

        return listings

    async def _fetch_description(self, context, url: str) -> str:
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            el = await page.query_selector(".description__text")
            text = await el.inner_text() if el else ""
            await page.close()
            return text.strip()
        except Exception as e:
            logger.warning(f"[linkedin_au] Description fetch failed: {e}")
            return ""
