const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:5000";

function jobParams({
    page = 1,
    pageSize = 20,
    q = "",
    company = "",
    country = "",
    stateRegion = "", city = "", skill = "", postedAfter = "", hasSalary = "", sort = "newest",
    remoteType = "",
    seniority = "",
    salaryCurrency = "", salaryPeriod = "", salaryMin = "", salaryMax = "",
} = {}) {
    const params = new URLSearchParams();

    params.set("page", String(page));
    params.set("page_size", String(pageSize));

    if (q.trim()) {
        params.set("q", q.trim());
    }

    if (company) {
        params.set("company", company);
    }

    if (country) {
        params.set("country", country);
    }

    if (remoteType) {
        params.set("remote_type", remoteType);
    }

    if (seniority) {
        params.set("seniority", seniority);
    }

    Object.entries({ state_region: stateRegion, city, skill, posted_after: postedAfter, has_salary: hasSalary, sort,
        salary_currency: salaryCurrency, salary_period: salaryPeriod, salary_min: salaryMin, salary_max: salaryMax })
      .forEach(([key, value]) => { if (value !== "" && value != null) params.set(key, String(value)); });

    return params;
}

export async function getJobs(options = {}, { signal } = {}) {
    const params = jobParams(options);
    const response = await fetch(
        `${API_BASE_URL}/api/jobs?${params.toString()}`, { signal }
    );

    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || `Request failed (${response.status}). Please try again.`);
    }

    return response.json();
}

export async function getFacets(options = {}, { signal } = {}) {
    const params = jobParams(options);
    params.delete("page"); params.delete("page_size"); params.delete("sort");
    const response = await fetch(`${API_BASE_URL}/api/job-facets?${params}`, { signal });
    if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || "Filter options could not be updated. Please retry.");
    }
    return (await response.json()).data;
}

export async function getJob(sourceKey) {
    const response = await fetch(
        `${API_BASE_URL}/api/jobs/${encodeURIComponent(
      sourceKey
    )}`
    );

    if (!response.ok) {
        throw new Error("Failed to load job details");
    }

    return response.json();
}

export async function getCompanies() {
    const response = await fetch(
        `${API_BASE_URL}/api/companies`
    );

    if (!response.ok) {
        throw new Error("Failed to load companies");
    }

    const result = await response.json();

    return result.data || [];
}

export async function getSkills() {
    const response = await fetch(
        `${API_BASE_URL}/api/skills`
    );

    if (!response.ok) {
        throw new Error("Failed to load skills");
    }

    const result = await response.json();

    return result.data || [];
}

export async function getLocations() {
    const response = await fetch(`${API_BASE_URL}/api/locations`);
    if (!response.ok) throw new Error("Failed to load location options");
    return (await response.json()).data || { locations: [], workArrangements: [] };
}

export async function getSalaryOptions() {
    const response = await fetch(`${API_BASE_URL}/api/salary-options`);
    if (!response.ok) throw new Error("Failed to load salary options");
    return (await response.json()).data || { options: [] };
}
