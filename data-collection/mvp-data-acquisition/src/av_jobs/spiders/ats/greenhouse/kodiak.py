"""Kodiak careers spider."""

from .base import GreenhouseSpider


class KodiakSpider(GreenhouseSpider):
    """Collect all currently listed jobs from Kodiak's Greenhouse board."""

    name = "kodiak"
    company = "Kodiak"
    board_token = "kodiak"
