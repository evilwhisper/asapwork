import logging
logger = logging.getLogger(__name__)

class LinkedInGlobalScraper:
    source_name = "linkedin_global"
    async def scrape(self, *args, **kwargs):
        logger.warning("[linkedin_global] Plugin not active in MVP")
        raise NotImplementedError("LinkedIn Global plugin not active in MVP")
