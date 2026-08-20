"""Vay careers spider."""

from .base import GreenhouseSpider


class VaySpider(GreenhouseSpider):
    """Collect all currently listed jobs from Vay's Greenhouse board."""

    name = "vay"
    company = "Vay"
    board_token = "vay"
