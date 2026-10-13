from collections import defaultdict
from app.locations import canonical_location, location_variants, location_predicate, aggregate_locations
from app.facets import FacetIndex
from app.repositories.jobs import JobRepository


def test_aliases_are_explicit_and_country_scoped():
    assert canonical_location("CA", "state_region", "ON") == "Ontario"
    assert canonical_location("US", "state_region", "ON") == "ON"
    assert canonical_location("CN", "city", "Guangzhou City") == "Guangzhou"
    assert canonical_location("US", "city", "Guangzhou City") == "Guangzhou City"
    assert canonical_location("SE", "city", "Göteborg") == "Gothenburg"
    assert canonical_location("JP", "city", "Chuo City") == "Chuo City"
    assert canonical_location("CN", "city", "Hangzhou City - Binjiang District") == "Hangzhou City - Binjiang District"


def test_group_counts_preserve_all_jobs_and_match_selected_aliases():
    rows = [dict(dashboard_release_id=1, job_id=i, country_code="CA", state_region=region, city="Toronto") for i, region in enumerate(("ON", "Ontario"), 1)]
    index = FacetIndex(rows, [])
    assert index.options({"country": "CA"})["state_region"] == [{"value": "Ontario", "count": 2}]
    assert index.options({"country": "CA", "state_region": "ON"})["total"] == 2
    assert index.options({"state_region": "ON"})["total"] == 2
    grouped = aggregate_locations([dict(country_code="CA", state_region=region, city="Toronto", job_count=count) for region, count in (("ON", 3), ("Ontario", 2))])
    assert grouped == [dict(countryCode="CA", stateRegion="Ontario", city="Toronto", jobCount=5)]


def test_sql_matching_uses_bound_aliases_and_keeps_other_filters():
    _, where, params = JobRepository()._build_filters(search=None, company="Company", country="CN", state_region=None, city="Guangzhou", remote_type="hybrid", seniority=None)
    assert "j.city IN (%s,%s)" in where
    assert params == ["Company", "CN", "Guangzhou", "Guangzhou City", "hybrid"]
    sql, params = location_predicate(None, "state_region", "Ontario")
    assert "j.country_code = %s" in sql and "CA" in params and "ON" in params
    assert location_variants(None, "city", "Boston") == ("Boston",)
    hostile = "x' OR 1=1"
    sql, params = location_predicate("CN", "city", hostile)
    assert hostile not in sql and params == [hostile]


def test_read_projection_keeps_original_fields_and_never_mutates_input():
    row = defaultdict(lambda: None, country_code="CA", state_region="ON", city="Toronto", location_raw="Toronto, ON")
    result = JobRepository._job_to_api(row, [])
    assert result["stateRegion"] == "Ontario"
    assert result["locationSourceFields"]["stateRegion"] == "ON"
    assert result["location"] == "Toronto, ON"
    assert row["state_region"] == "ON"
