"""Conservative parsing of job location text into structured fields."""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class ParsedLocation:
    city: Optional[str] = None
    state_region: Optional[str] = None
    country_code: Optional[str] = None
    remote_type: Optional[str] = None


COUNTRY_NAMES = {
    "germany": "DE",
    "united states": "US",
    "united states of america": "US",
    "us": "US",
    "usa": "US",
    "canada": "CA",
    "japan": "JP",
    "south korea": "KR",
    "china": "CN",
    "israel": "IL",
    "spain": "ES",
    "singapore": "SG",
    "uae": "AE",
    "united arab emirates": "AE",
    "sweden": "SE",
    "poland": "PL",
    "hungary": "HU",
    "vietnam": "VN",
    "mexico": "MX",
    "uk": "GB",
    "united kingdom": "GB",
    "austria": "AT",
    "australia": "AU",
    "india": "IN",
    "brazil": "BR",
    "netherlands": "NL",
}

JAPAN_PREFECTURES = {
    "hokkaido", "aomori", "iwate", "miyagi", "akita", "yamagata",
    "fukushima", "ibaraki", "tochigi", "gunma", "saitama", "chiba",
    "tokyo", "kanagawa", "niigata", "toyama", "ishikawa", "fukui",
    "yamanashi", "nagano", "gifu", "shizuoka", "aichi", "mie",
    "shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama",
    "tottori", "shimane", "okayama", "hiroshima", "yamaguchi",
    "tokushima", "kagawa", "ehime", "kochi", "fukuoka", "saga",
    "nagasaki", "kumamoto", "oita", "miyazaki", "kagoshima",
    "okinawa",
}

US_STATE_NAMES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}

CANADIAN_PROVINCE_CODES = {
    "AB", "BC", "MB", "NB", "NL", "NS", "NT",
    "NU", "ON", "PE", "QC", "SK", "YT",
}

CANADIAN_PROVINCE_NAMES = {
    "alberta": "AB",
    "british columbia": "BC",
    "manitoba": "MB",
    "new brunswick": "NB",
    "newfoundland and labrador": "NL",
    "nova scotia": "NS",
    "northwest territories": "NT",
    "nunavut": "NU",
    "ontario": "ON",
    "prince edward island": "PE",
    "quebec": "QC",
    "saskatchewan": "SK",
    "yukon": "YT",
}

CITY_COUNTRY_MAP = {
    "tokyo": "JP",
    "london": "GB",
    "beijing": "CN",
    "shanghai": "CN",
    "nanjing": "CN",
    "shenzhen": "CN",
    "chengdu": "CN",
    "suzhou": "CN",
    "hangzhou": "CN",
    "chongqing": "CN",
    "xi'an": "CN",
    "sunnyvale": "US",
    "ann arbor": "US",
    "detroit": "US",
    "stuttgart": "DE",
    "munich": "DE",
    "seoul": "KR",
    "stockholm": "SE",
    "gothenburg": "SE",
    "tel aviv": "IL",
    "dubai": "AE",
    "bangalore": "IN",
    "riyadh": "SA",
    "hong kong": "HK",
    "one-north": "SG",
    "kuala lumpur": "MY",
    "oklahoma city": "US",
}


def _extract_work_mode(value: str) -> Optional[str]:
    """Return a normalised work mode when explicitly stated."""
    lower = value.lower()

    if "hybrid" in lower:
        return "hybrid"

    if "onsite" in lower or "on-site" in lower:
        return "onsite"

    if "fully remote" in lower or re.search(r"\bremote\b", lower):
        return "remote"

    return None


def _remove_work_mode_suffix(value: str) -> str:
    """Remove work-mode text for location parsing only."""
    patterns = [
        r"\s*-\s*(?:hybrid|onsite|on-site|remote)\s*$",
        r"\s+remote\s*$",
        r"\s*\((?:fully\s+)?remote\)\s*$",
        r"\s*\(hybrid\)\s*$",
        r"\s*\(onsite\)\s*$",
    ]

    cleaned = value

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

    return cleaned


def _country_from_city(city: str) -> Optional[str]:
    value = city.strip().lower()

    # Remove trailing district/zone detail first.
    value = re.sub(
        r"\s*-\s*.+(?:district|zone|new area)$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()

    # Prefer the exact city name first, because "City" can be part of
    # the actual name (for example, "Oklahoma City").
    country_code = CITY_COUNTRY_MAP.get(value)

    if country_code:
        return country_code

    # Some source values use "City" as a formatting suffix,
    # for example "Nanjing City".
    value_without_suffix = re.sub(
        r"\s+city$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()

    return CITY_COUNTRY_MAP.get(value_without_suffix)


def parse_location(location: Optional[str]) -> ParsedLocation:
    """Parse a raw job location string conservatively."""
    if location is None:
        return ParsedLocation()

    location = location.strip()

    if not location:
        return ParsedLocation()

    # Long descriptive text needs separate conservative handling.
    # Some Japanese postings include an initial Tokyo assignment followed
    # by policy text mentioning possible remote/telework locations. That
    # policy text must not be interpreted as the job's remote_type.
    if "\n" in location:
        has_initial_assignment = re.search(
            r"(?:initial assignment|right after hiring)",
            location,
            flags=re.IGNORECASE,
        )

        has_tokyo_work_location = re.search(
            r"Shinagawa-ku,\s*Tokyo",
            location,
            flags=re.IGNORECASE,
        )

        if has_initial_assignment and has_tokyo_work_location:
            return ParsedLocation(country_code="JP")

        return ParsedLocation()

    remote_type = _extract_work_mode(location)

    # Pipe-separated entries represent multiple locations.
    if "|" in location:
        segments = [segment.strip() for segment in location.split("|")]
        countries = set()

        for segment in segments:
            parsed = parse_location(segment)
            if parsed.country_code:
                countries.add(parsed.country_code)

        if len(countries) == 1:
            return ParsedLocation(
                country_code=next(iter(countries)),
                remote_type=remote_type,
            )

        return ParsedLocation(remote_type=remote_type)

    # Semicolon-separated entries may represent multiple locations.
    # Keep only the country when every segment resolves to the same country.
    if ";" in location:
        segments = [
            segment.strip()
            for segment in location.split(";")
            if segment.strip()
        ]

        parsed_segments = [
            parse_location(segment)
            for segment in segments
        ]

        countries = {
            parsed.country_code
            for parsed in parsed_segments
            if parsed.country_code
        }

        all_resolved = all(
            parsed.country_code
            for parsed in parsed_segments
        )

        if all_resolved and len(countries) == 1:
            return ParsedLocation(
                country_code=next(iter(countries)),
                remote_type=remote_type,
            )

        return ParsedLocation(remote_type=remote_type)

    location_for_parsing = _remove_work_mode_suffix(location)

    # Remove non-geographic office annotations used by some sources.
    location_for_parsing = re.sub(
        r"\s*\(HQ\)\s*$",
        "",
        location_for_parsing,
        flags=re.IGNORECASE,
    ).strip()
    parts = [
        part.strip()
        for part in location_for_parsing.split(",")
        if part.strip()
    ]

    # Multiple US locations in one string.
    # Examples:
    # "Kermit, TX or Odessa, TX"
    # "Ann Arbor, MI, Remote - US"
    # "Pittsburgh, PA or Remote"
    #
    # Only apply when at least one valid US state code is present and
    # there is no evidence of another country.
    state_codes_found = {
        match.upper()
        for match in re.findall(
            r"(?<![A-Za-z])([A-Za-z]{2})(?![A-Za-z])",
            location_for_parsing,
        )
        if match.upper() in US_STATE_CODES
    }

    if state_codes_found:
        lower_location = location_for_parsing.lower()

        non_us_country_mentioned = any(
            country_name in lower_location
            for country_name, country_code in COUNTRY_NAMES.items()
            if country_code != "US"
        )

        # Let the existing City, State parser handle simple two-part
        # locations so that city and state_region are preserved.
        simple_city_state = (
            len(parts) == 2
            and parts[1].upper() in US_STATE_CODES
        )

        if not non_us_country_mentioned and not simple_city_state:
            return ParsedLocation(
                country_code="US",
                remote_type=remote_type,
            )

    # US state-only or "State - detail" locations.
    # Examples: "Arizona", "California - LA", "Texas - Depot 2".
    state_detail_match = re.fullmatch(
        r"([A-Za-z ]+?)(?:\s*-\s*(.+))?",
        location_for_parsing,
    )

    if state_detail_match:
        state_name = state_detail_match.group(1).strip().lower()

        if state_name in US_STATE_NAMES:
            return ParsedLocation(
                state_region=US_STATE_NAMES[state_name],
                country_code="US",
                remote_type=remote_type,
            )

    # Well-known US geographic area without a city/state pair.
    if location_for_parsing.lower() == "san francisco bay area":
        return ParsedLocation(
            country_code="US",
            remote_type=remote_type,
        )

    # Washington, D.C. is a US location but is not in the 50-state mapping.
    if location_for_parsing.lower() in {"washington, d.c.", "washington, dc"}:
        return ParsedLocation(
            city="Washington",
            state_region="DC",
            country_code="US",
            remote_type=remote_type,
        )

    # Location list ending with an explicit remote country.
    # Example: "Fort Worth, Texas, Remote - US".
    trailing_remote_country = re.search(
        r"(?:^|,)\s*remote\s*(?:-|–)\s*([^,]+)\s*$",
        location_for_parsing,
        flags=re.IGNORECASE,
    )

    if trailing_remote_country:
        country_name = trailing_remote_country.group(1).strip()
        normalised_country = country_name.lower().replace(".", "")

        country_aliases = {
            "us": "US",
            "usa": "US",
            "united states": "US",
            "united states of america": "US",
        }

        country_code = (
            country_aliases.get(normalised_country)
            or COUNTRY_NAMES.get(country_name.lower())
        )

        if country_code:
            return ParsedLocation(
                country_code=country_code,
                remote_type="remote",
            )

    # Remote location with an explicit country.
    remote_country_match = re.fullmatch(
        r"remote\s*(?:-|–)?\s*\(?([^()]+)\)?",
        location_for_parsing,
        flags=re.IGNORECASE,
    )

    if remote_country_match:
        country_name = remote_country_match.group(1).strip()
        normalised_country = country_name.lower().replace(".", "")

        country_aliases = {
            "us": "US",
            "usa": "US",
            "united states": "US",
            "united states of america": "US",
        }

        country_code = (
            country_aliases.get(normalised_country)
            or COUNTRY_NAMES.get(country_name.lower())
        )

        if country_code:
            return ParsedLocation(
                country_code=country_code,
                remote_type="remote",
            )

    # Locations joined by "and".
    # Keep only the country when every part resolves to the same country.
    if re.search(r"\s+and\s+", location_for_parsing, flags=re.IGNORECASE):
        segments = [
            segment.strip()
            for segment in re.split(
                r"\s+and\s+",
                location_for_parsing,
                flags=re.IGNORECASE,
            )
            if segment.strip()
        ]

        parsed_segments = [
            parse_location(segment)
            for segment in segments
        ]

        countries = {
            parsed.country_code
            for parsed in parsed_segments
            if parsed.country_code
        }

        all_resolved = all(
            parsed.country_code
            for parsed in parsed_segments
        )

        if all_resolved and len(countries) == 1:
            return ParsedLocation(
                country_code=next(iter(countries)),
                remote_type=remote_type,
            )

        return ParsedLocation(remote_type=remote_type)

    # Country-only location.
    if len(parts) == 1:
        country_code = COUNTRY_NAMES.get(parts[0].lower())

        if country_code:
            return ParsedLocation(
                country_code=country_code,
                remote_type=remote_type,
            )

    # Country-first Chinese format.
    if parts and COUNTRY_NAMES.get(parts[0].lower()) == "CN":
        if len(parts) >= 3:
            return ParsedLocation(
                city=parts[2],
                state_region=parts[1],
                country_code="CN",
                remote_type=remote_type,
            )

        return ParsedLocation(
            country_code="CN",
            remote_type=remote_type,
        )

    # Explicit country at the end.
    if len(parts) >= 2:
        country_code = COUNTRY_NAMES.get(parts[-1].lower())

        if country_code:
            city = parts[0] or None
            state_region = parts[-2] if len(parts) >= 3 else None

            if country_code == "US" and state_region:
                state_region = US_STATE_NAMES.get(
                    state_region.lower(),
                    state_region,
                )

            return ParsedLocation(
                city=city,
                state_region=state_region,
                country_code=country_code,
                remote_type=remote_type,
            )

    # Standard Japanese city/prefecture format.
    if len(parts) == 2:
        prefecture = re.sub(
            r"\s+Prefecture$",
            "",
            parts[1],
            flags=re.IGNORECASE,
        ).strip()

        if prefecture.lower() in JAPAN_PREFECTURES:
            return ParsedLocation(
                city=parts[0],
                state_region=prefecture,
                country_code="JP",
                remote_type=remote_type,
            )

    # Standard two-part US full state-name format.
    if len(parts) == 2:
        state_code = US_STATE_NAMES.get(parts[1].lower())

        if state_code:
            return ParsedLocation(
                city=parts[0],
                state_region=state_code,
                country_code="US",
                remote_type=remote_type,
            )

    # Standard US state abbreviation.
    if len(parts) == 2 and parts[1].upper() in US_STATE_CODES:
        return ParsedLocation(
            city=parts[0],
            state_region=parts[1].upper(),
            country_code="US",
            remote_type=remote_type,
        )

    # Standard Canadian province abbreviation.
    if len(parts) == 2 and parts[1].upper() in CANADIAN_PROVINCE_CODES:
        return ParsedLocation(
            city=parts[0],
            state_region=parts[1].upper(),
            country_code="CA",
            remote_type=remote_type,
        )

    # Standard Canadian full province-name format.
    # Example: "Ajax, Ontario".
    if len(parts) == 2:
        province_code = CANADIAN_PROVINCE_NAMES.get(parts[1].lower())

        if province_code:
            return ParsedLocation(
                city=parts[0],
                state_region=province_code,
                country_code="CA",
                remote_type=remote_type,
            )

    # Multiple city/state pairs in the same country.
    if len(parts) >= 4 and len(parts) % 2 == 0:
        state_parts = [
            parts[index].upper()
            for index in range(1, len(parts), 2)
        ]

        if all(state in US_STATE_CODES for state in state_parts):
            return ParsedLocation(
                country_code="US",
                remote_type=remote_type,
            )

        if all(state in CANADIAN_PROVINCE_CODES for state in state_parts):
            return ParsedLocation(
                country_code="CA",
                remote_type=remote_type,
            )

    # Two-part location ending in a reliable known city.
    # Example: "Bangsar South, Kuala Lumpur".
    # Keep only the country because the first part may be a district,
    # neighbourhood, or office area rather than a city.
    if len(parts) == 2:
        country_code = _country_from_city(parts[1])

        if country_code:
            return ParsedLocation(
                country_code=country_code,
                remote_type=remote_type,
            )

    # Single known city.
    if len(parts) == 1:
        country_code = _country_from_city(parts[0])

        if country_code:
            return ParsedLocation(
                city=parts[0],
                country_code=country_code,
                remote_type=remote_type,
            )

    # Multiple cities that all map reliably to the same country.
    if len(parts) > 1:
        countries = [_country_from_city(part) for part in parts]

        if all(countries) and len(set(countries)) == 1:
            return ParsedLocation(
                country_code=countries[0],
                remote_type=remote_type,
            )

    return ParsedLocation(remote_type=remote_type)
