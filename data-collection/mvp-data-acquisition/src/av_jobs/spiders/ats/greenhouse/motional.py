"""Motional careers spider."""

from .base import GreenhouseSpider


class MotionalSpider(GreenhouseSpider):
    """Collect all currently listed jobs from Motional's Greenhouse board."""

    name = "motional"
    company = "Motional"
    board_token = "motional"
