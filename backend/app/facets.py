"""MVP-sized, release-scoped faceted search over immutable published data."""
from collections import Counter, defaultdict
import unicodedata

from app.salary import salary_from_row, matches_salary
from app.locations import project_location, canonical_location


def normal(value):
    return "".join(char for char in unicodedata.normalize("NFKD", str(value or "").casefold())
                   if not unicodedata.combining(char))


def counted_options(groups, by_count=False):
    """Count jobs, not spelling variants, using the same matching normalization."""
    counts, spellings = Counter(), defaultdict(set)
    for values in groups:
        unique = set()
        for value in values:
            if value:
                key = normal(value)
                unique.add(key)
                spellings[key].add(value)
        counts.update(unique)
    result = [{"value": min(spellings[key], key=lambda s: (s.isupper(), s.islower(), s)), "count": count}
              for key, count in counts.items()]
    return sorted(result, key=lambda item: ((-item["count"] if by_count else 0), normal(item["value"])))


class FacetIndex:
    def __init__(self, rows, skill_rows):
        self.rows = {(row["dashboard_release_id"], row["job_id"]): project_location(row) for row in rows}
        self.skills = defaultdict(set)
        self.skill_types = defaultdict(set)
        for item in skill_rows:
            key = (item["dashboard_release_id"], item["job_id"])
            if key in self.rows and item["skill_name"]:
                self.skills[key].add(item["skill_name"])
                self.skill_types[normal(item["skill_name"])].add(item.get("skill_type") or "unknown")
        self.salaries = {key: salary_from_row(row) for key, row in self.rows.items()}
        self.search_text = {key: [normal(row.get(field)) for field in
                            ("advertised_job_title", "generic_job_title", "company_name", "location_raw")]
                            + [normal(name) for name in self.skills[key]] for key, row in self.rows.items()}

    def options(self, filters):
        masks = {}
        columns = {"company": "company_name", "country": "country_code", "state_region": "state_region",
                   "city": "city", "remote_type": "remote_type", "seniority": "seniority_code"}
        for field, column in columns.items():
            if filters.get(field):
                masks[field] = {key for key, row in self.rows.items() if normal(row.get(column)) == normal(
                    canonical_location(row.get("country_code"), field, filters[field]) if field in {"state_region", "city"} else filters[field])}
        if filters.get("search"):
            query = normal(filters["search"].strip())
            masks["search"] = {key for key, texts in self.search_text.items() if any(query in text for text in texts)}
        if filters.get("skill"):
            masks["skill"] = {key for key in self.rows if any(normal(name) == normal(filters["skill"]) for name in self.skills[key])}
        if filters.get("posted_after"):
            since = str(filters["posted_after"])
            masks["posted_after"] = {key for key, row in self.rows.items()
                if row.get("date_posted") and str(row["date_posted"])[:10] >= since}
        if filters.get("has_salary") is not None:
            def provided(row):
                return bool(str(row.get("salary_raw") or "").strip()) or row.get("salary_min") is not None or row.get("salary_max") is not None
            masks["has_salary"] = {key for key, row in self.rows.items() if provided(row) == filters["has_salary"]}
        for field in ("salary_currency", "salary_period", "salary_min", "salary_max"):
            if filters.get(field) is not None:
                argument = {"salary_currency": "currency", "salary_period": "period", "salary_min": "minimum", "salary_max": "maximum"}[field]
                masks[field] = {key for key, salary in self.salaries.items() if matches_salary(salary, **{argument: filters[field]})}

        def matching(exclude=()):
            result = set(self.rows)
            for field, mask in masks.items():
                if field not in exclude: result.intersection_update(mask)
            return result

        result = {"total": len(matching())}
        # Ignore a selector's own value so it remains possible to change it.
        # Parent location selectors also ignore children that they reset in the UI.
        for field, column in columns.items():
            exclude = {field}
            if field == "country": exclude.update(("state_region", "city"))
            if field == "state_region": exclude.add("city")
            result[field] = counted_options((self.rows[key].get(column),) for key in matching(exclude))
        result["skill"] = counted_options((self.skills[key] for key in matching({"skill"})), by_count=True)
        result["skillTypes"] = {item["value"]: sorted(self.skill_types[normal(item["value"])]) for item in result["skill"]}
        units = Counter()
        for key in matching({"salary_currency", "salary_period", "salary_min", "salary_max"}):
            salary = self.salaries[key]
            if salary.currency and salary.period and (salary.minimum is not None or salary.maximum is not None):
                units[(salary.currency, salary.period)] += 1
        result["salary_units"] = [{"value": f"{currency}/{period}", "count": count} for (currency, period), count in sorted(units.items())]
        available = Counter()
        dates = []
        for key in matching({"has_salary"}):
            row = self.rows[key]
            known = bool(str(row.get("salary_raw") or "").strip()) or row.get("salary_min") is not None or row.get("salary_max") is not None
            available["true" if known else "false"] += 1
        for key in matching({"posted_after"}):
            if self.rows[key].get("date_posted"): dates.append(str(self.rows[key]["date_posted"])[:10])
        result["has_salary"] = [{"value": value, "count": count} for value, count in sorted(available.items())]
        result["posted_range"] = {"minimum": min(dates) if dates else None, "maximum": max(dates) if dates else None}
        return result
