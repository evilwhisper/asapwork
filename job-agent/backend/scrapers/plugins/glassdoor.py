import logging
logger = logging.getLogger(__name__)

class GlassdoorScraper:
    source_name = "glassdoor"
    async def scrape(self, *args, **kwargs):
        logger.warning("[glassdoor] Plugin not active in MVP")
        raise NotImplementedError("Glassdoor plugin not active in MVP")
