"""Applied Intuition careers spider."""

from .base import AshbySpider


class AppliedIntuitionSpider(AshbySpider):
    """Collect jobs from Applied Intuition's public Ashby board."""

    name = "applied_intuition"
    company = "Applied Intuition"
    board_token = "applied"
