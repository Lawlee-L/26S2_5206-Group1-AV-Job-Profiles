"""Woven by Toyota careers spider."""

from .base import LeverSpider


class WovenByToyotaSpider(LeverSpider):
    """Collect jobs from Woven by Toyota's public Lever board."""

    name = "woven_by_toyota"
    company = "Woven by Toyota"
    board_token = "woven-by-toyota"
