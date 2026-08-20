"""WeRide US careers spider."""

from .base import LeverSpider


class WeRideUsSpider(LeverSpider):
    """Collect WeRide's US jobs from its public Lever board."""

    name = "weride_us"
    company = "WeRide"
    board_token = "weride"
