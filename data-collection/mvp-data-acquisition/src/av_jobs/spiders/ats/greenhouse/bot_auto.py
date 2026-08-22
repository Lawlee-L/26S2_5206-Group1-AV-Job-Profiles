"""Bot Auto careers spider."""

from .base import GreenhouseSpider


class BotAutoSpider(GreenhouseSpider):
    """Collect all currently listed jobs from Bot Auto's Greenhouse board."""

    name = "bot_auto"
    company = "Bot Auto"
    board_token = "botauto"
