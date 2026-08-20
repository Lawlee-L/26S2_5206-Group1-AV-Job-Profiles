"""Aurora careers spider."""

from .base import AshbySpider


class AuroraSpider(AshbySpider):
    """Collect all currently listed jobs from Aurora's public Ashby board."""

    name = "aurora"
    company = "Aurora"
    board_token = "aurora-operations-inc"
