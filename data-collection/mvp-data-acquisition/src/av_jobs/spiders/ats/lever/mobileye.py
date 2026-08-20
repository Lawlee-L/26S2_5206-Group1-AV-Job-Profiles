"""Mobileye careers spider."""

from .base import LeverSpider


class MobileyeSpider(LeverSpider):
    """Collect all currently listed jobs from Mobileye's EU Lever board."""

    name = "mobileye"
    company = "Mobileye"
    board_token = "mobileye"
    api_origin = "https://api.eu.lever.co"
