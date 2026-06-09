import logging
logger = logging.getLogger(__name__)

class IndeedIntlScraper:
    source_name = "indeed_intl"
    async def scrape(self, *args, **kwargs):
        logger.warning("[indeed_intl] Plugin not active in MVP")
        raise NotImplementedError("Indeed International plugin not active in MVP")
