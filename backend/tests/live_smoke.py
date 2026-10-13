"""Optional read-only smoke test: python tests/live_smoke.py http://127.0.0.1:5000.

Run against an explicitly configured, published local database. No imports or writes.
"""
import json
import sys
import time
from urllib.parse import urlencode, quote
from urllib.request import urlopen


def run(base_url):
    def get(path, **params):
        started = time.perf_counter()
        url = f"{base_url.rstrip('/')}/api/{path}"
        if params:
            url += "?" + urlencode(params)
        with urlopen(url, timeout=30) as response:
            result = json.load(response)
        print(f"{path} {params}: HTTP 200, {time.perf_counter() - started:.2f}s")
        return result

    all_jobs = get("jobs")
    total = all_jobs["pagination"]["total"]
    assert total > 0, "Publish a nonempty release before running this test"
    insights = get("insights")["data"]
    current = insights["current"]
    assert current["jobCount"] == total
    assert sum(group["jobCount"] for group in current["clusters"]) == total
    assert sum(not group["isNoise"] for group in current["clusters"]) == current["clusterCount"]
    assert all(0 <= skill["jobCount"] <= total for skill in current["skills"])
    assert all(0 <= skill["share"] <= 100 for skill in current["skills"])
    for point in insights["history"]["points"]:
        assert point["avJobs"] is None or 0 <= point["avJobs"] <= point["activeJobs"]
        if point["avJobs"] is None:
            assert point["clusterCount"] is None
            assert point["unclusteredShare"] is None
    facets = get("job-facets")["data"]
    assert facets["total"] == total
    company = facets["company"][0]["value"]
    company_facets = get("job-facets", company=company)["data"]
    assert company_facets["total"] == get("jobs", company=company)["pagination"]["total"]
    # Every offered option must produce the same positive intersection in SQL.
    for field in ("country", "remote_type", "seniority", "skill"):
        for option in company_facets[field][:3]:
            result = get("jobs", company=company, **{field: option["value"]})
            assert result["pagination"]["total"] == option["count"] > 0
    for query in ("C++", "robotics", "10%", "_", "Cafe"):
        assert get("job-facets", q=query)["data"]["total"] == get("jobs", q=query)["pagination"]["total"]
    geo = get("locations")["data"]["locations"]
    assert geo, "No known locations in the published release"
    location = next((row for row in geo if row["city"]), geo[0])
    filters = {"country": location["countryCode"]}
    if location["stateRegion"]: filters["state_region"] = location["stateRegion"]
    if location["city"]: filters["city"] = location["city"]
    selected = get("jobs", **filters)
    assert selected["pagination"]["total"] > 0
    assert all(row["countryCode"] == filters["country"] for row in selected["data"])
    assert all(not filters.get("city") or row["city"] == filters["city"] for row in selected["data"])
    skill = get("skills")["data"][0]["name"]
    skilled = get("jobs", skill=skill, sort="title")
    assert skilled["pagination"]["total"] > 0
    assert all(any(item["name"] == skill for item in job["skills"]) for job in skilled["data"])
    assert get("jobs", q="Python")["pagination"]["total"] > 0
    get("jobs", q="robotics", skill="C++", sort="company")
    salary = get("jobs", has_salary="true")
    no_salary = get("jobs", has_salary="false")
    assert salary["pagination"]["total"] + no_salary["pagination"]["total"] == total
    pay_options = get("salary-options")["data"]
    for option in pay_options["options"]:
        pay = get("jobs", salary_currency=option["currency"], salary_period=option["period"])
        assert pay["pagination"]["total"] == option["jobCount"]
        row = pay["data"][0]
        assert row["salaryCurrency"] == option["currency"] and row["salaryPeriod"] == option["period"]
        amount = row["salaryMax"] if row["salaryMax"] is not None else row["salaryMin"]
        ranged = get("jobs", salary_currency=option["currency"], salary_period=option["period"], salary_min=amount, page_size=100)
        assert all(job["salaryMax"] is not None and job["salaryMax"] >= amount for job in ranged["data"])
    get("jobs", salary_currency="USD", salary_period="year", salary_min=100000, q="engineer", skill="C++")
    dated = get("jobs", posted_after="2026-09-01", sort="oldest")
    assert all(row["postedDate"] and row["postedDate"][:10] >= "2026-09-01" for row in dated["data"])
    for row in all_jobs["data"][:3]:
        detail = get("jobs/" + quote(row["sourceKey"], safe=""))["data"]
        assert detail["sourceKey"] == row["sourceKey"]
        assert "locationDisplay" in detail and "salaryDisplay" in detail
    print(f"PASS: published active AV jobs={total}; salary provided={salary['pagination']['total']}; no salary={no_salary['pagination']['total']}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000")
