
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  MapPin,
  Briefcase,
  GraduationCap,
  Bookmark,
  RotateCcw,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";

import Header from "../components/Header";
import CompanyLogo from "../components/CompanyLogo";
import Footer from "../components/Footer";
import { getJobs, getCompanies } from "../api/jobs";
import { getFavorites, toggleFavorite } from "../utils/favorites";

const PAGE_SIZE = 20;

const LOCATIONS = [
  { code: "US", name: "United States" },
  { code: "AU", name: "Australia" },
  { code: "GB", name: "United Kingdom" },
  { code: "DE", name: "Germany" },
  { code: "SG", name: "Singapore" },
  { code: "CN", name: "China" },
  { code: "JP", name: "Japan" },
  { code: "KR", name: "South Korea" },
  { code: "CA", name: "Canada" },
];

const getSkillName = (skill) =>
  typeof skill === "string" ? skill : skill?.name || "Skill";

const formatDate = (value) => {
  if (!value) return "Date not available";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return date.toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
};

const getExperienceText = (job) => {
  if (job.level || job.seniority) {
    return job.level || job.seniority;
  }

  const min = job.experienceMinYears ?? job.experience_min_years;
  const max = job.experienceMaxYears ?? job.experience_max_years;

  if (min != null && max != null) return `${min}–${max} years`;
  if (min != null) return `${min}+ years`;

  return "Not specified";
};

const getRemoteType = (job) => {
  const value = job.remoteType ?? job.remote_type;

  if (!value) return "Not specified";

  const normalized = String(value).trim().toLowerCase();

  if (normalized === "remote") return "Remote";
  if (normalized === "hybrid") return "Hybrid";
  if (normalized === "onsite" || normalized === "on-site") {
    return "On-site";
  }

  return "Not specified";
};

const getLocationText = (job) => {
  const city = job.city;
  const region = job.stateRegion ?? job.state_region;
  const countryCode = job.countryCode ?? job.country_code;

  const countryName =
    LOCATIONS.find(
      (item) => item.code === String(countryCode || "").toUpperCase()
    )?.name || countryCode;

  const structured = [city, region, countryName]
    .filter((value) => value != null && String(value).trim() !== "")
    .join(", ");

  return structured || job.location || "Location not specified";
};

export default function Jobs() {
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("");
  const [seniority, setSeniority] = useState("");
  const [remoteType, setRemoteType] = useState("");
  const [company, setCompany] = useState("");

  const [companies, setCompanies] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const [favorites, setFavorites] = useState(() => getFavorites());

  useEffect(() => {
    let cancelled = false;

    async function loadCompanies() {
      try {
        const result = await getCompanies();
        if (!cancelled) {
          setCompanies(Array.isArray(result) ? result : []);
        }
      } catch (err) {
        console.error("Failed to load companies:", err);
      }
    }

    loadCompanies();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      setLoading(true);
      setError("");

      try {
        const result = await getJobs({
          page,
          pageSize: PAGE_SIZE,
          q: search.trim(),
          company,
          country,
          remoteType,
          seniority,
        });

        if (cancelled) return;

        setJobs(Array.isArray(result?.data) ? result.data : []);
        setPagination(result?.pagination || null);
      } catch (err) {
        console.error("Failed to load jobs:", err);

        if (!cancelled) {
          setJobs([]);
          setPagination(null);
          setError(
            err?.message ||
              "Unable to load jobs. Please check that the backend is running."
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    const timer = setTimeout(loadJobs, search ? 300 : 0);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [search, page, company, country, remoteType, seniority]);

  const updateFilter = (setter) => (event) => {
    setter(event.target.value);
    setPage(1);
  };

  const clearFilters = () => {
    setSearch("");
    setCountry("");
    setSeniority("");
    setRemoteType("");
    setCompany("");
    setPage(1);
  };

  const hasActiveFilters = Boolean(
    search || country || seniority || remoteType || company
  );

  const getFavoriteId = (job) => job.sourceKey || job.id;

  const isJobSaved = (job) => {
    const id = getFavoriteId(job);
    return favorites.some(
      (item) => String(item.sourceKey || item.id) === String(id)
    );
  };

  const handleSaveJob = (event, job) => {
    event.preventDefault();
    event.stopPropagation();

    toggleFavorite({
      ...job,
      id: getFavoriteId(job),
    });

    setFavorites(getFavorites());
  };

  const totalJobs =
    pagination?.total ??
    pagination?.totalItems ??
    pagination?.total_count ??
    jobs.length;

  const totalPages =
    pagination?.totalPages ??
    pagination?.pages ??
    pagination?.total_pages ??
    Math.max(1, Math.ceil(totalJobs / PAGE_SIZE));

  const currentPage = pagination?.page ?? page;

  const goToPage = (newPage) => {
    if (
      newPage < 1 ||
      newPage > totalPages ||
      newPage === currentPage
    ) {
      return;
    }

    setPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const getPageNumbers = () => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    if (currentPage <= 3) {
      return [1, 2, 3, 4, "...", totalPages];
    }

    if (currentPage >= totalPages - 2) {
      return [
        1,
        "...",
        totalPages - 3,
        totalPages - 2,
        totalPages - 1,
        totalPages,
      ];
    }

    return [
      1,
      "...",
      currentPage - 1,
      currentPage,
      currentPage + 1,
      "...",
      totalPages,
    ];
  };

  return (
    <div className="app-shell">
      <Header />

      <main className="jobs-page">
        <section className="jobs-hero">
          <span className="jobs-hero-label">
            AV CAREER OPPORTUNITIES
          </span>

          <h1>Explore AV Jobs</h1>

          <p>
            Discover job opportunities across the autonomous vehicle
            industry. Search by job title, company, location, or
            technical skill.
          </p>

          <Link
            to="/about#favorites"
            className="hero-action-button"
          >
            View Saved Jobs
            <ChevronRight size={15} />
          </Link>
        </section>

        <div className="jobs-filter-panel">
          <div className="jobs-search">
            <Search size={15} />
            <input
              type="text"
              placeholder="Search by job title, skills, or company"
              value={search}
              onChange={updateFilter(setSearch)}
            />
          </div>

          <div className="jobs-filter-row">
            {/* LOCATION */}
            <div className="jobs-filter-item">
              <MapPin size={13} />
              <select
                value={country}
                onChange={updateFilter(setCountry)}
                aria-label="Filter by location"
              >
                <option value="">Location</option>
                {LOCATIONS.map((location) => (
                  <option
                    key={location.code}
                    value={location.code}
                  >
                    {location.name}
                  </option>
                ))}
              </select>
            </div>

            {/* EXPERIENCE LEVEL */}
            <div className="jobs-filter-item">
              <GraduationCap size={13} />
              <select
                value={seniority}
                onChange={updateFilter(setSeniority)}
                aria-label="Filter by experience level"
              >
                <option value="">Experience Level</option>
                <option value="intern">Intern</option>
                <option value="entry">Entry</option>
                <option value="junior">Junior</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="lead">Lead</option>
                <option value="manager">Manager</option>
              </select>
            </div>

            {/* WORK ARRANGEMENT */}
            <div className="jobs-filter-item">
              <Briefcase size={13} />
              <select
                value={remoteType}
                onChange={updateFilter(setRemoteType)}
                aria-label="Filter by work arrangement"
              >
                <option value="">Work Arrangement</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
              </select>
            </div>

            {/* COMPANY */}
            <div className="jobs-filter-item">
              <Briefcase size={13} />
              <select
                value={company}
                onChange={updateFilter(setCompany)}
                aria-label="Filter by company"
              >
                <option value="">Company</option>
                {companies.map((item) => {
                  const name =
                    typeof item === "string" ? item : item.name;
                  const count =
                    typeof item === "string" ? null : item.jobCount;

                  if (!name) return null;

                  return (
                    <option key={name} value={name}>
                      {name}
                      {count != null ? ` (${count})` : ""}
                    </option>
                  );
                })}
              </select>
            </div>

            <button
              type="button"
              className="jobs-filter-button"
              onClick={clearFilters}
              disabled={!hasActiveFilters}
            >
              <RotateCcw size={13} />
              Clear
            </button>
          </div>
        </div>

        <div className="jobs-toolbar">
          <span>
            {loading
              ? "Loading jobs..."
              : `${totalJobs} ${totalJobs === 1 ? "job" : "jobs"} found`}
          </span>

          <div className="jobs-sort">
            <span>Showing latest published jobs</span>
          </div>
        </div>

        {loading && (
          <div className="jobs-no-results">
            <Briefcase size={24} />
            <h3>Loading jobs...</h3>
            <p>Getting the latest AV job opportunities.</p>
          </div>
        )}

        {!loading && error && (
          <div className="jobs-no-results">
            <Briefcase size={24} />
            <h3>Unable to load jobs</h3>
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && jobs.length > 0 && (
          <div className="jobs-list-container">
            {jobs.map((job) => {
              const saved = isJobSaved(job);
              const sourceKey = getFavoriteId(job);

              return (
                <Link
                  key={sourceKey}
                  to={`/jobs/${encodeURIComponent(sourceKey)}`}
                  className="jobs-list-item"
                >
                  <div className="jobs-company-logo">
                    <CompanyLogo
                      company={job.company || "Unknown company"}
                    />
                  </div>

                  <div className="jobs-list-content">
                    <h3>
                      {job.title || "Job title not available"}
                    </h3>

                    <strong>
                      {job.company || "Company not specified"}
                    </strong>

                    <div className="jobs-meta">
                      <span>
                        <MapPin size={10} />
                        {getLocationText(job)}
                      </span>

                      <span className="jobs-dot">•</span>

                      <span>
                        <Briefcase size={10} />
                        {getRemoteType(job)}
                      </span>

                      <span className="jobs-dot">•</span>

                      <span>
                        <GraduationCap size={10} />
                        {getExperienceText(job)}
                      </span>
                    </div>

                    <div className="jobs-skills">
                      {(Array.isArray(job.skills) ? job.skills : [])
                        .slice(0, 4)
                        .map((skill, index) => (
                          <span key={`${getSkillName(skill)}-${index}`}>
                            {getSkillName(skill)}
                          </span>
                        ))}

                      {Array.isArray(job.skills) &&
                        job.skills.length > 4 && (
                          <span className="jobs-more">...</span>
                        )}
                    </div>
                  </div>

                  <div className="jobs-list-right">
                    <span>
                      {formatDate(job.postedDate || job.date)}
                    </span>

                    <button
                      type="button"
                      className={
                        saved
                          ? "job-bookmark-button saved"
                          : "job-bookmark-button"
                      }
                      aria-label={
                        saved ? "Remove saved job" : "Save job"
                      }
                      title={
                        saved
                          ? "Remove from favorites"
                          : "Save to favorites"
                      }
                      onClick={(event) =>
                        handleSaveJob(event, job)
                      }
                    >
                      <Bookmark
                        size={14}
                        fill={saved ? "currentColor" : "none"}
                      />
                    </button>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="jobs-no-results">
            <Search size={24} />
            <h3>No jobs found</h3>
            <p>Try changing your search or filter options.</p>

            {hasActiveFilters && (
              <button
                type="button"
                className="jobs-filter-button"
                onClick={clearFilters}
              >
                <RotateCcw size={13} />
                Clear Filters
              </button>
            )}
          </div>
        )}

        {!loading &&
          !error &&
          jobs.length > 0 &&
          totalPages > 1 && (
            <div className="jobs-pagination">
              <button
                type="button"
                aria-label="Previous page"
                disabled={currentPage <= 1}
                onClick={() => goToPage(currentPage - 1)}
              >
                <ChevronLeft size={14} />
              </button>

              {getPageNumbers().map((pageNumber, index) =>
                pageNumber === "..." ? (
                  <span key={`ellipsis-${index}`}>...</span>
                ) : (
                  <button
                    key={pageNumber}
                    type="button"
                    className={
                      currentPage === pageNumber ? "active" : ""
                    }
                    onClick={() => goToPage(pageNumber)}
                  >
                    {pageNumber}
                  </button>
                )
              )}

              <button
                type="button"
                aria-label="Next page"
                disabled={currentPage >= totalPages}
                onClick={() => goToPage(currentPage + 1)}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
      </main>

      <Footer />
    </div>
  );
}
