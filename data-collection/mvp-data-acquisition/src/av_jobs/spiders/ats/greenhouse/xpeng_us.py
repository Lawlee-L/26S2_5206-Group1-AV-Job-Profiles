"""XPeng US careers spider."""

from .base import GreenhouseSpider


class XpengUsSpider(GreenhouseSpider):
    """Collect XPeng's US jobs from its public Greenhouse board."""

    name = "xpeng_us"
    company = "XPeng"
    board_token = "xpengmotors"
