"""Explicit register of company spiders included in the implementation MVP."""

from __future__ import annotations

from dataclasses import dataclass

from .models import SourceName


@dataclass(frozen=True)
class SourceDefinition:
    """Stable metadata joining a spider to its investigation evidence."""

    spider: str
    company: str
    platform: SourceName
    region: str
    investigation_issue: int


# Public structured ATS sources verified on 20 August 2026. Each name maps to
# one concrete spider class in av_jobs.spiders. This is the implementation MVP,
# not evidence that the client approved all sixteen companies as the final scope.
MVP_SOURCES = (
    SourceDefinition("fortytwodot", "42dot", "ashby", "Global", 3),
    SourceDefinition("aurora", "Aurora", "ashby", "Global", 3),
    SourceDefinition("applied_intuition", "Applied Intuition", "ashby", "Global", 3),
    SourceDefinition("avride", "Avride", "greenhouse", "Global", 4),
    SourceDefinition("bot_auto", "Bot Auto", "greenhouse", "Global", 4),
    SourceDefinition("gatik", "Gatik", "greenhouse", "Global", 4),
    SourceDefinition("may_mobility", "May Mobility", "greenhouse", "Global", 4),
    SourceDefinition("kodiak", "Kodiak", "greenhouse", "Global", 9),
    SourceDefinition("latitude", "Latitude (Ford)", "greenhouse", "Global", 9),
    SourceDefinition("motional", "Motional", "greenhouse", "Global", 7),
    SourceDefinition("vay", "Vay", "greenhouse", "Global", 8),
    SourceDefinition("xpeng_us", "XPeng", "greenhouse", "US", 8),
    SourceDefinition("mobileye", "Mobileye", "lever", "Global", 7),
    SourceDefinition("weride_us", "WeRide", "lever", "US", 8),
    SourceDefinition("woven_by_toyota", "Woven by Toyota", "lever", "Global", 8),
    SourceDefinition("zoox", "Zoox", "lever", "Global", 8),
)

MVP_SPIDERS = tuple(source.spider for source in MVP_SOURCES)
SOURCE_BY_SPIDER = {source.spider: source for source in MVP_SOURCES}
