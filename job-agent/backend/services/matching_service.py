import json
import logging
import re
from backend.models import JobListing, UserProfile

logger = logging.getLogger(__name__)


def apply_blacklist(listing: JobListing, profile: UserProfile) -> bool:
    """Returns True if listing should be filtered out."""
    if not profile.blacklist_keywords:
        return False
    keywords = json.loads(profile.blacklist_keywords)
    text = f"{listing.title} {listing.description or ''}".lower()
    return any(kw.lower() in text for kw in keywords)


def apply_whitelist(listing: JobListing, profile: UserProfile) -> bool:
    """Returns True if listing should always surface (company on whitelist)."""
    if not profile.whitelist_companies or not listing.company:
        return False
    companies = json.loads(profile.whitelist_companies)
    return any(c.lower() in listing.company.lower() for c in companies)


def parse_au_salary(salary_text: str) -> tuple[int | None, int | None]:
    """Parse AU salary strings to (min, max) annual AUD. Returns (None, None) if unparseable."""
    if not salary_text:
        return None, None

    text = salary_text.lower().replace(",", "").replace(" ", "")
    HOURLY_SUFFIX = r"(?:/hr|/hour|perhour|p\.h\.)"
    ANNUAL_SUFFIX = r"(?:pa|/yr|/year|peryear|annual|p\.a\.)?"

    # Hourly range: $30-$40/hr or $30–$40/hour
    m = re.search(rf"\$?([\d.]+)(?:–|-)\$?([\d.]+){HOURLY_SUFFIX}", text)
    if m:
        return int(float(m.group(1)) * 2080), int(float(m.group(2)) * 2080)

    # Single hourly: $35/hr
    m = re.search(rf"\$?([\d.]+){HOURLY_SUFFIX}", text)
    if m:
        val = int(float(m.group(1)) * 2080)
        return val, val

    # Annual range: $80k-$90k, $80,000-$90,000, 80000-90000
    m = re.search(r"\$?([\d.]+)(k)?(?:–|-)\$?([\d.]+)(k)?", text)
    if m:
        lo = float(m.group(1)) * (1000 if m.group(2) else 1)
        hi = float(m.group(3)) * (1000 if m.group(4) else 1)
        return int(lo), int(hi)

    # Single annual value: $120k, $80,000, 90000 pa
    m = re.search(rf"\$?([\d.]+)(k)?{ANNUAL_SUFFIX}", text)
    if m:
        val = float(m.group(1)) * (1000 if m.group(2) else 1)
        return int(val), int(val)

    return None, None


def apply_salary_filter(listing: JobListing, profile: UserProfile) -> bool:
    """Returns True if listing should be filtered out (below salary floor)."""
    if not profile.target_salary_min or not listing.salary_text:
        return False  # can't filter what isn't stated

    _, salary_max = parse_au_salary(listing.salary_text)
    if salary_max is None:
        return False  # unknown salary — pass through

    return salary_max < profile.target_salary_min


async def run_matching_pipeline(
    listings: list[JobListing],
    profile: UserProfile,
    ai_service=None,
) -> list[JobListing]:
    passed = []
    for listing in listings:
        if apply_whitelist(listing, profile):
            listing.status = "queued"
            passed.append(listing)
            continue

        if apply_blacklist(listing, profile):
            listing.status = "skipped"
            continue

        if apply_salary_filter(listing, profile):
            listing.status = "skipped"
            continue

        if ai_service and ai_service.settings.ai_scorer_enabled:
            profile_text = f"{profile.name} targeting {profile.target_roles}"
            score = await ai_service.score_job(listing.description or listing.title, profile_text)
            listing.match_score = score

        listing.status = "queued"
        passed.append(listing)

    return passed
