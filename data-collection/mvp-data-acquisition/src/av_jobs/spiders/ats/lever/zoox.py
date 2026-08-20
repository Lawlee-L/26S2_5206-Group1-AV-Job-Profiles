"""Zoox careers spider."""

from .base import LeverSpider


class ZooxSpider(LeverSpider):
    """Collect all currently listed jobs from Zoox's public Lever board."""

    name = "zoox"
    company = "Zoox"
    board_token = "zoox"
