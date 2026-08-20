"""Avride careers spider."""

from .base import GreenhouseSpider


class AvrideSpider(GreenhouseSpider):
    """Collect all currently listed jobs from Avride's Greenhouse board."""

    name = "avride"
    company = "Avride"
    board_token = "avride"
