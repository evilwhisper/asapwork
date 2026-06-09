import asyncio
import logging
import random
from urllib.parse import quote_plus
from backend.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class SeekScraper(BaseScraper):
    source_name = "seek"

    async def scrape(self, keywords: list[str], location: str) -> list[dict]:
        from playwright.async_api import async_playwright
        kw = quote_plus(" ".join(keywords))
        loc = quote_plus(location)
        url = f"https://www.seek.com.au/jobs?keywords={kw}&location={loc}"
        listings = []

        async with async_playwright() as p:
            browser, context = await self._new_browser_context(p)
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector('article[data-card-type="JobCard"]', timeout=15000)

                cards = await page.query_selector_all('article[data-card-type="JobCard"]')
                for card in cards:
                    try:
                        title_el = await card.query_selector('a[data-automation="jobTitle"]')
                        title = await title_el.inner_text() if title_el else ""
                        href = await title_el.get_attribute("href") if title_el else ""
                        job_url = f"https://www.seek.com.au{href}" if href else ""
                        external_id = href.split("/")[-1].split("?")[0] if href else ""

                        company_el = await card.query_selector('a[data-automation="jobCompany"]')
                        company = await company_el.inner_text() if company_el else ""

                        location_el = await card.query_selector('a[data-automation="jobLocation"]')
                        location_text = await location_el.inner_text() if location_el else ""

                        salary_el = await card.query_selector('span[data-automation="jobSalary"]')
                        salary_text = await salary_el.inner_text() if salary_el else ""

                        listing = {
                            "external_id": external_id,
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_text.strip(),
                            "salary_text": salary_text.strip(),
                            "url": job_url,
                            "source": self.source_name,
                        }

                        # Fetch full description
                        if job_url:
                            await asyncio.sleep(random.uniform(2, 5))
                            desc = await self._fetch_description(context, job_url)
                            listing["description"] = desc

                        listings.append(listing)
                        await asyncio.sleep(random.uniform(2, 5))
                    except Exception as e:
                        logger.warning(f"[seek] Card parse error: {e}")
                        continue
            finally:
                await browser.close()

        return listings

    async def _fetch_description(self, context, url: str) -> str:
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            el = await page.query_selector('[data-automation="jobAdDetails"]')
            text = await el.inner_text() if el else ""
            await page.close()
            return text.strip()
        except Exception as e:
            logger.warning(f"[seek] Description fetch failed for {url}: {e}")
            return ""
