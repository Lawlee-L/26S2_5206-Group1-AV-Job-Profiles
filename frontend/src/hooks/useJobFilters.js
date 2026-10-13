import { useSearchParams } from "react-router-dom";
import { useLayoutEffect, useRef } from "react";

export const FILTER_KEYS = ["q", "company", "country", "state_region", "city", "remote_type", "seniority",
  "skill", "posted_after", "has_salary", "salary_currency", "salary_period", "salary_min", "salary_max"];

export function useJobFilters() {
  const [params, setParams] = useSearchParams();
  const pending = useRef(params);
  useLayoutEffect(() => { pending.current = params; }, [params]);
  const filters = Object.fromEntries(FILTER_KEYS.map(key => [key, params.get(key) || ""]));
  const rawPage = Number(params.get("page") || 1);
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  const sort = params.get("sort") || "newest";
  function update(patch, resetPage = true) {
    // React Router does not queue multiple setSearchParams calls like setState.
    // Keep successive edits made before the next render from losing each other.
    const next = new URLSearchParams(pending.current);
    if (resetPage) next.delete("page");
    Object.entries(patch).forEach(([key, value]) => {
      if (value === "" || value == null || (key === "sort" && value === "newest") || (key === "page" && value === 1)) next.delete(key);
      else next.set(key, String(value));
    });
    pending.current = next;
    setParams(next, { replace: true });
  }
  const clear = () => { pending.current = new URLSearchParams(); setParams({}, { replace: true }); };
  return { filters, page, sort, params, update, clear };
}

export function apiFilters(filters) {
  return { q: filters.q, company: filters.company, country: filters.country, stateRegion: filters.state_region,
    city: filters.city, remoteType: filters.remote_type, seniority: filters.seniority, skill: filters.skill,
    postedAfter: filters.posted_after, hasSalary: filters.has_salary, salaryCurrency: filters.salary_currency,
    salaryPeriod: filters.salary_period, salaryMin: filters.salary_min, salaryMax: filters.salary_max };
}
