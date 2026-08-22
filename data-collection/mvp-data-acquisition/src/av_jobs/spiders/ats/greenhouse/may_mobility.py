"""May Mobility careers spider."""

from .base import GreenhouseSpider


class MayMobilitySpider(GreenhouseSpider):
    """Collect jobs from May Mobility's public Greenhouse board."""

    name = "may_mobility"
    company = "May Mobility"
    board_token = "maymobility"
