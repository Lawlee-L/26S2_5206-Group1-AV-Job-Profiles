"""42dot careers spider."""

from .base import AshbySpider


class FortyTwoDotSpider(AshbySpider):
    """Collect all currently listed jobs from 42dot's public Ashby board."""

    name = "fortytwodot"
    company = "42dot"
    board_token = "42dot"
