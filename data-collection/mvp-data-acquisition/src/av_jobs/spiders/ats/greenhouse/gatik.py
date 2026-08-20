"""Gatik careers spider."""

from .base import GreenhouseSpider


class GatikSpider(GreenhouseSpider):
    """Collect all currently listed jobs from Gatik's Greenhouse board."""

    name = "gatik"
    company = "Gatik"
    board_token = "gatikaiinc"
