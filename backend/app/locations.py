"""Conservative, country-scoped read projection; never rewrites frozen data."""
import unicodedata

VERSION = "location-aliases-v1"
# Region codes: Canada Post addressing guidelines. City names: explicit aliases,
# never a blanket rule that removes 'City' from arbitrary municipalities.
ALIASES = {
    ("CA", "state_region"): {
        "Ontario": ("Ontario", "ON"), "British Columbia": ("British Columbia", "BC"),
        "Quebec": ("Quebec", "Québec", "QC"), "Alberta": ("Alberta", "AB"),
    },
    ("CN", "city"): {
        "Guangzhou": ("Guangzhou", "Guangzhou City"),
        "Nanjing": ("Nanjing", "Nanjing City"), "Hangzhou": ("Hangzhou", "Hangzhou City"),
    },
    ("SE", "city"): {"Gothenburg": ("Gothenburg", "Göteborg", "Goteborg")},
    ("IN", "state_region"): {"Maharashtra": ("Maharashtra", "Maharastra")},
}


def _key(value):
    return "".join(char for char in unicodedata.normalize("NFKD", str(value or "").strip().casefold())
                   if not unicodedata.combining(char))


def canonical_location(country, field, value):
    if not value:
        return value
    for canonical, variants in ALIASES.get((str(country or "").upper(), field), {}).items():
        if _key(value) in {_key(item) for item in variants}:
            return canonical
    return value.strip()


def location_variants(country, field, value):
    canonical = canonical_location(country, field, value)
    return ALIASES.get((str(country or "").upper(), field), {}).get(canonical, (value,))


def location_predicate(country, field, value):
    """SQL parameters and facet masks follow the identical country-scoped rules."""
    if field not in {"state_region", "city"}:
        raise ValueError("Unsupported location field")
    if country:
        variants = location_variants(country, field, value)
        return (f"j.{field} = %s" if len(variants) == 1 else f"j.{field} IN ({','.join(['%s'] * len(variants))})"), list(variants)
    clauses, params = [f"j.{field} = %s"], [value]
    for (scope, kind), groups in ALIASES.items():
        if kind != field:
            continue
        variants = groups.get(canonical_location(scope, field, value))
        if variants:
            clauses.append(f"(j.country_code = %s AND j.{field} IN ({','.join(['%s'] * len(variants))}))")
            params.extend((scope, *variants))
    return ("(" + " OR ".join(clauses) + ")" if len(clauses) > 1 else clauses[0]), params


def project_location(row):
    result = row.copy()
    result.update({field: canonical_location(row.get("country_code"), field, row.get(field))
                   for field in ("state_region", "city")})
    return result


def aggregate_locations(rows):
    groups = {}
    for raw in rows:
        row = project_location(raw)
        key = (row.get("country_code"), row.get("state_region"), row.get("city"))
        groups[key] = groups.get(key, 0) + int(row["job_count"])
    return [{"countryCode": country, "stateRegion": region, "city": city, "jobCount": count}
            for (country, region, city), count in sorted(groups.items(), key=lambda item: tuple(str(v or "") for v in item[0]))]
