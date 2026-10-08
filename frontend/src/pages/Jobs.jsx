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

import {
  getJobs,
  getCompanies,
} from "../api/jobs";

import {
  getFavorites,
  toggleFavorite,
} from "../utils/favorites";

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

  const [favorites, setFavorites] = useState(
    () => getFavorites()
  );

  // =========================================
  // LOAD COMPANIES
  // =========================================

  useEffect(() => {
    let cancelled = false;

    async function loadCompanies() {
      try {
        const result = await getCompanies();

        if (!cancelled) {
          setCompanies(result);
        }
      } catch (err) {
        console.error(
          "Failed to load companies:",
          err
        );
      }
    }

    loadCompanies();

    return () => {
      cancelled = true;
    };
  }, []);

  // =========================================
  // LOAD JOBS
  // =========================================

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      try {
        setLoading(true);
        setError("");

        const result = await getJobs({
          page,
          pageSize: 20,
          q: search,
          company,
          country,
          remoteType,
          seniority,
        });

        if (!cancelled) {
          setJobs(result.data || []);
          setPagination(
            result.pagination || null
          );
        }
      } catch (err) {
        console.error(
          "Failed to load jobs:",
          err
        );

        if (!cancelled) {
          setJobs([]);
          setPagination(null);

          setError(
            "Unable to load jobs. Please make sure the backend is running."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(
      loadJobs,
      search ? 300 : 0
    );

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [
    search,
    page,
    company,
    country,
    remoteType,
    seniority,
  ]);

  // =========================================
  // SEARCH
  // =========================================

  const handleSearchChange = (event) => {
    setSearch(event.target.value);
    setPage(1);
  };

  // =========================================
  // FILTERS
  // =========================================

  const handleCountryChange = (event) => {
    setCountry(event.target.value);
    setPage(1);
  };

  const handleSeniorityChange = (event) => {
    setSeniority(event.target.value);
    setPage(1);
  };

  const handleRemoteTypeChange = (event) => {
    setRemoteType(event.target.value);
    setPage(1);
  };

  const handleCompanyChange = (event) => {
    setCompany(event.target.value);
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

  const hasActiveFilters =
    search ||
    country ||
    seniority ||
    remoteType ||
    company;

  // =========================================
  // FAVORITES
  // =========================================

  const getFavoriteId = (job) =>
    job.sourceKey || job.id;

  const isJobSaved = (job) => {
    const jobId = getFavoriteId(job);

    return favorites.some(
      (item) =>
        String(
          item.sourceKey || item.id
        ) === String(jobId)
    );
  };

  const handleSaveJob = (
    event,
    job
  ) => {
    event.preventDefault();
    event.stopPropagation();

    const favoriteJob = {
      ...job,
      id: job.sourceKey || job.id,
    };

    toggleFavorite(favoriteJob);

    setFavorites(getFavorites());
  };

  // =========================================
  // HELPERS
  // =========================================

  const getSkillName = (skill) => {
    if (typeof skill === "string") {
      return skill;
    }

    return skill?.name || "Skill";
  };

  const formatDate = (dateValue) => {
    if (!dateValue) {
      return "Date not available";
    }

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
      return dateValue;
    }

    return date.toLocaleDateString(
      "en-AU",
      {
        day: "numeric",
        month: "short",
        year: "numeric",
      }
    );
  };

  const getExperienceText = (job) => {
    if (job.level) {
      return job.level;
    }

    if (
      job.experienceMinYears != null &&
      job.experienceMaxYears != null
    ) {
      return `${job.experienceMinYears}–${job.experienceMaxYears} years`;
    }

    if (
      job.experienceMinYears != null
    ) {
      return `${job.experienceMinYears}+ years`;
    }

    return "Not specified";
  };

  const getRemoteType = (job) => {
    return (
      job.remoteType ||
      job.type ||
      "Not specified"
    );
  };

  // =========================================
  // PAGINATION
  // =========================================

  const totalJobs =
    pagination?.total ??
    pagination?.totalItems ??
    pagination?.total_count ??
    jobs.length;

  const totalPages =
    pagination?.totalPages ??
    pagination?.pages ??
    pagination?.total_pages ??
    Math.max(
      1,
      Math.ceil(totalJobs / 20)
    );

  const currentPage =
    pagination?.page ?? page;

  const goToPage = (newPage) => {
    if (
      newPage < 1 ||
      newPage > totalPages ||
      newPage === currentPage
    ) {
      return;
    }

    setPage(newPage);

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const getPageNumbers = () => {
    if (totalPages <= 5) {
      return Array.from(
        { length: totalPages },
        (_, index) => index + 1
      );
    }

    if (currentPage <= 3) {
      return [
        1,
        2,
        3,
        4,
        "...",
        totalPages,
      ];
    }

    if (
      currentPage >=
      totalPages - 2
    ) {
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

        {/* HERO */}

        <section className="jobs-hero">
          <span className="jobs-hero-label">
            AV CAREER OPPORTUNITIES
          </span>

          <h1>Explore AV Jobs</h1>

          <p>
            Discover job opportunities
            across the autonomous vehicle
            industry. Search by job title,
            company, location, or technical
            skill.
          </p>

          <Link
            to="/about#favorites"
            className="hero-action-button"
          >
            View Saved Jobs
            <ChevronRight size={15} />
          </Link>
        </section>

        {/* =========================================
            SEARCH + FILTERS
        ========================================= */}

        <div className="jobs-filter-panel">

          <div className="jobs-search">
            <Search size={15} />

            <input
              type="text"
              placeholder="Search by job title, skills, or company"
              value={search}
              onChange={
                handleSearchChange
              }
            />
          </div>

          <div className="jobs-filter-row">

            {/* COUNTRY */}

            <div className="jobs-filter-item">
              <MapPin size={13} />

              <select
                value={country}
                onChange={
                  handleCountryChange
                }
                aria-label="Filter by location"
              >
                <option value="">
                  Location
                </option>

                <option value="United States">
                  United States
                </option>

                <option value="Germany">
                  Germany
                </option>

                <option value="Singapore">
                  Singapore
                </option>

                <option value="United Kingdom">
                  United Kingdom
                </option>

                <option value="China">
                  China
                </option>

                <option value="Japan">
                  Japan
                </option>

                <option value="South Korea">
                  South Korea
                </option>

                <option value="Canada">
                  Canada
                </option>
              </select>
            </div>

            {/* EXPERIENCE LEVEL */}

            <div className="jobs-filter-item">
              <GraduationCap
                size={13}
              />

              <select
                value={seniority}
                onChange={
                  handleSeniorityChange
                }
                aria-label="Filter by experience level"
              >
                <option value="">
                  Experience Level
                </option>

                <option value="intern">
                  Intern
                </option>

                <option value="entry">
                  Entry
                </option>

                <option value="junior">
                  Junior
                </option>

                <option value="mid">
                  Mid
                </option>

                <option value="senior">
                  Senior
                </option>

                <option value="lead">
                  Lead
                </option>

                <option value="manager">
                  Manager
                </option>
              </select>
            </div>

            {/* REMOTE TYPE */}

            <div className="jobs-filter-item">
              <Briefcase size={13} />

              <select
                value={remoteType}
                onChange={
                  handleRemoteTypeChange
                }
                aria-label="Filter by work type"
              >
                <option value="">
                  Work Type
                </option>

                <option value="remote">
                  Remote
                </option>

                <option value="hybrid">
                  Hybrid
                </option>

                <option value="onsite">
                  On-site
                </option>
              </select>
            </div>

            {/* COMPANY */}

            <div className="jobs-filter-item">
              <Briefcase size={13} />

              <select
                value={company}
                onChange={
                  handleCompanyChange
                }
                aria-label="Filter by company"
              >
                <option value="">
                  Company
                </option>

                {companies.map(
                  (companyItem) => (
                    <option
                      key={
                        companyItem.name
                      }
                      value={
                        companyItem.name
                      }
                    >
                      {companyItem.name} (
                      {
                        companyItem.jobCount
                      })
                    </option>
                  )
                )}

              </select>
            </div>

            {/* CLEAR FILTERS */}

            <button
              type="button"
              className="jobs-filter-button"
              onClick={clearFilters}
              disabled={
                !hasActiveFilters
              }
            >
              <RotateCcw size={13} />
              Clear
            </button>

          </div>
        </div>

        {/* =========================================
            RESULT COUNT
        ========================================= */}

        <div className="jobs-toolbar">

          <span>
            {loading
              ? "Loading jobs..."
              : `${totalJobs} ${
                  totalJobs === 1
                    ? "job"
                    : "jobs"
                } found`}
          </span>

          <div className="jobs-sort">
            <span>
              Showing latest published jobs
            </span>
          </div>

        </div>

        {/* =========================================
            LOADING
        ========================================= */}

        {loading && (
          <div className="jobs-no-results">
            <Briefcase size={24} />

            <h3>Loading jobs...</h3>

            <p>
              Getting the latest AV job
              opportunities.
            </p>
          </div>
        )}

        {/* =========================================
            ERROR
        ========================================= */}

        {!loading && error && (
          <div className="jobs-no-results">
            <Briefcase size={24} />

            <h3>
              Unable to load jobs
            </h3>

            <p>{error}</p>
          </div>
        )}

        {/* =========================================
            JOB LIST
        ========================================= */}

        {!loading &&
          !error &&
          jobs.length > 0 && (
            <div className="jobs-list-container">

              {jobs.map((job) => {
                const saved =
                  isJobSaved(job);

                const sourceKey =
                  job.sourceKey ||
                  job.id;

                return (
                  <Link
                    key={sourceKey}
                    to={`/jobs/${encodeURIComponent(
                      sourceKey
                    )}`}
                    className="jobs-list-item"
                  >

                    {/* LOGO */}

                    <div className="jobs-company-logo">
                      <CompanyLogo
                        company={
                          job.company ||
                          "Unknown company"
                        }
                      />
                    </div>

                    {/* CONTENT */}

                    <div className="jobs-list-content">

                      <h3>
                        {job.title ||
                          "Job title not available"}
                      </h3>

                      <strong>
                        {job.company ||
                          "Company not specified"}
                      </strong>

                      <div className="jobs-meta">

                        <span>
                          <MapPin
                            size={10}
                          />

                          {job.location ||
                            "Location not specified"}
                        </span>

                        <span className="jobs-dot">
                          •
                        </span>

                        <span>
                          <Briefcase
                            size={10}
                          />

                          {getRemoteType(
                            job
                          )}
                        </span>

                        <span className="jobs-dot">
                          •
                        </span>

                        <span>
                          <GraduationCap
                            size={10}
                          />

                          {getExperienceText(
                            job
                          )}
                        </span>

                      </div>

                      {/* SKILLS */}

                      <div className="jobs-skills">

                        {(job.skills || [])
                          .slice(0, 4)
                          .map(
                            (
                              skill,
                              index
                            ) => (
                              <span
                                key={`${getSkillName(
                                  skill
                                )}-${index}`}
                              >
                                {getSkillName(
                                  skill
                                )}
                              </span>
                            )
                          )}

                        {(job.skills || [])
                          .length > 4 && (
                          <span className="jobs-more">
                            ...
                          </span>
                        )}

                      </div>
                    </div>

                    {/* RIGHT */}

                    <div className="jobs-list-right">

                      <span>
                        {formatDate(
                          job.postedDate
                        )}
                      </span>

                      <button
                        type="button"
                        className={
                          saved
                            ? "job-bookmark-button saved"
                            : "job-bookmark-button"
                        }
                        aria-label={
                          saved
                            ? "Remove saved job"
                            : "Save job"
                        }
                        title={
                          saved
                            ? "Remove from favorites"
                            : "Save to favorites"
                        }
                        onClick={(
                          event
                        ) =>
                          handleSaveJob(
                            event,
                            job
                          )
                        }
                      >
                        <Bookmark
                          size={14}
                          fill={
                            saved
                              ? "currentColor"
                              : "none"
                          }
                        />
                      </button>

                    </div>

                  </Link>
                );
              })}

            </div>
          )}

        {/* =========================================
            NO RESULTS
        ========================================= */}

        {!loading &&
          !error &&
          jobs.length === 0 && (
            <div className="jobs-no-results">

              <Search size={24} />

              <h3>
                No jobs found
              </h3>

              <p>
                Try changing your search
                or filter options.
              </p>

              {hasActiveFilters && (
                <button
                  type="button"
                  className="jobs-filter-button"
                  onClick={
                    clearFilters
                  }
                >
                  <RotateCcw
                    size={13}
                  />
                  Clear Filters
                </button>
              )}

            </div>
          )}

        {/* =========================================
            PAGINATION
        ========================================= */}

        {!loading &&
          !error &&
          jobs.length > 0 &&
          totalPages > 1 && (
            <div className="jobs-pagination">

              <button
                type="button"
                aria-label="Previous page"
                disabled={
                  currentPage <= 1
                }
                onClick={() =>
                  goToPage(
                    currentPage - 1
                  )
                }
              >
                <ChevronLeft
                  size={14}
                />
              </button>

              {getPageNumbers().map(
                (
                  pageNumber,
                  index
                ) => {
                  if (
                    pageNumber === "..."
                  ) {
                    return (
                      <span
                        key={`ellipsis-${index}`}
                      >
                        ...
                      </span>
                    );
                  }

                  return (
                    <button
                      key={pageNumber}
                      type="button"
                      className={
                        currentPage ===
                        pageNumber
                          ? "active"
                          : ""
                      }
                      onClick={() =>
                        goToPage(
                          pageNumber
                        )
                      }
                    >
                      {pageNumber}
                    </button>
                  );
                }
              )}

              <button
                type="button"
                aria-label="Next page"
                disabled={
                  currentPage >=
                  totalPages
                }
                onClick={() =>
                  goToPage(
                    currentPage + 1
                  )
                }
              >
                <ChevronRight
                  size={14}
                />
              </button>

            </div>
          )}

      </main>

      <Footer />
    </div>
  );
}