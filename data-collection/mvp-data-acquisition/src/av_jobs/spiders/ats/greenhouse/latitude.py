"""Latitude AI careers spider."""

from .base import GreenhouseSpider


class LatitudeSpider(GreenhouseSpider):
    """Collect all currently listed jobs from Latitude AI's Greenhouse board."""

    name = "latitude"
    company = "Latitude (Ford)"
    board_token = "latitude"
