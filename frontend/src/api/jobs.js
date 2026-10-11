const API_BASE_URL = (
    import.meta.env.VITE_API_BASE_URL ||
    "http://127.0.0.1:5000"
).replace(/\/+$/, "");

// Convert country names to two-letter country codes.
const COUNTRY_CODES = {
    "united states": "US",
    "united states of america": "US",
    usa: "US",
    australia: "AU",
    "united kingdom": "GB",
    uk: "GB",
    germany: "DE",
    singapore: "SG",
    china: "CN",
    japan: "JP",
    "south korea": "KR",
    canada: "CA",
};

// Normalize country values.
function normalizeCountry(country) {
    const value = String(country || "").trim();

    if (!value) {
        return "";
    }

    return (
        COUNTRY_CODES[value.toLowerCase()] ||
        value.toUpperCase()
    );
}

// Normalize work arrangement values.
function normalizeRemoteType(remoteType) {
    const value = String(remoteType || "")
        .trim()
        .toLowerCase();

    if (value === "on-site" || value === "on site") {
        return "onsite";
    }

    return value;
}

// Common API request function.
async function fetchJSON(endpoint) {
    let response;

    try {
        response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                Accept: "application/json",
            },
        });
    } catch {
        throw new Error(
            "Cannot connect to the backend. Please check that Flask is running."
        );
    }

    if (!response.ok) {
        let message = `Request failed (${response.status})`;

        try {
            const body = await response.json();
            message = body.error || body.message || message;
        } catch {
            // Keep the HTTP error if no JSON error is available.
        }

        throw new Error(message);
    }

    return response.json();
}

/**
 * Get jobs from the backend.
 *
 * Supported filters:
 * - Search
 * - Company
 * - Country
 * - State/Region
 * - City
 * - Work Arrangement
 * - Experience Level
 */
export async function getJobs({
    page = 1,
    pageSize = 20,
    q = "",
    company = "",
    country = "",
    stateRegion = "",
    city = "",
    remoteType = "",
    seniority = "",
} = {}) {
    const params = new URLSearchParams();

    params.set("page", String(page));
    params.set("page_size", String(pageSize));

    const searchValue = String(q || "").trim();
    const companyValue = String(company || "").trim();
    const countryValue = normalizeCountry(country);
    const regionValue = String(stateRegion || "").trim();
    const cityValue = String(city || "").trim();
    const remoteValue = normalizeRemoteType(remoteType);
    const seniorityValue = String(seniority || "").trim();

    // Search filter.
    if (searchValue) {
        params.set("q", searchValue);
    }

    // Company filter.
    if (companyValue) {
        params.set("company", companyValue);
    }

    // Location filter.
    if (countryValue) {
        params.set("country", countryValue);
    }

    // State/Region filter.
    // Backend requires a country when filtering by region.
    if (countryValue && regionValue) {
        params.set("state_region", regionValue);
    }

    // City filter.
    // Backend requires a country when filtering by city.
    if (countryValue && cityValue) {
        params.set("city", cityValue);
    }

    // Work Arrangement filter.
    // Valid values: remote, hybrid, onsite.
    if (remoteValue) {
        params.set("remote_type", remoteValue);
    }

    // Experience Level filter.
    if (seniorityValue) {
        params.set("seniority", seniorityValue);
    }

    return fetchJSON(`/api/jobs?${params.toString()}`);
}

/**
 * Get one job using its source key.
 */
export async function getJob(sourceKey) {
    if (sourceKey == null || sourceKey === "") {
        throw new Error("Job source key is required.");
    }

    return fetchJSON(
        `/api/jobs/${encodeURIComponent(String(sourceKey))}`
    );
}


export async function getCompanies() {
    const result = await fetchJSON("/api/companies");

    if (Array.isArray(result)) {
        return result;
    }

    if (result && Array.isArray(result.data)) {
        return result.data;
    }

    return [];
}

export async function getSkills() {
    const result = await fetchJSON("/api/skills");

    if (Array.isArray(result)) {
        return result;
    }

    if (result && Array.isArray(result.data)) {
        return result.data;
    }

    return [];
}