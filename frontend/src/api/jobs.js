const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:5000";

export async function getJobs({
    page = 1,
    pageSize = 20,
    q = "",
    company = "",
    country = "",
    remoteType = "",
    seniority = "",
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

    const response = await fetch(
        `${API_BASE_URL}/api/jobs?${params.toString()}`
    );

    if (!response.ok) {
        throw new Error("Failed to load jobs");
    }

    return response.json();
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