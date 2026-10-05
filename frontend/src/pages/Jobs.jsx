import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  Search,
  MapPin,
  Briefcase,
  GraduationCap,
  Bookmark,
  SlidersHorizontal,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

import Header from "../components/Header";
import CompanyLogo from "../components/CompanyLogo";
import { jobs } from "../data/jobs";

import {
  getFavorites,
  toggleFavorite,
} from "../utils/favorites";

export default function Jobs() {
  const [search, setSearch] = useState("");

  // Load saved jobs from localStorage
  const [favorites, setFavorites] = useState(
    () => getFavorites()
  );

  // Search jobs
  const filteredJobs = useMemo(() => {
    const value = search.trim().toLowerCase();

    if (!value) {
      return jobs;
    }

    return jobs.filter((job) => {
      const searchableText = [
        job.title,
        job.company,
        job.location,
        ...(job.skills || []),
      ]
        .join(" ")
        .toLowerCase();

      return searchableText.includes(value);
    });
  }, [search]);

  // Check whether a job is saved
  const isJobSaved = (jobId) => {
    return favorites.some(
      (item) => String(item.id) === String(jobId)
    );
  };

  // Save or remove a job
  const handleSaveJob = (event, job) => {
    // Prevent opening the Job Details page
    event.preventDefault();
    event.stopPropagation();

    toggleFavorite(job);

    // Update UI immediately
    setFavorites(getFavorites());
  };

  return (
    <div className="app-shell">
      <Header />

      <main className="jobs-page">
        {/* PAGE TITLE */}
        <div className="page-heading">
          <h1>All Jobs</h1>

          <p>
            Explore the latest job opportunities in the autonomous
            vehicle industry.
          </p>
        </div>

        {/* SEARCH + FILTER AREA */}
        <div className="jobs-filter-panel">
          <div className="jobs-search">
            <Search size={15} />

            <input
              type="text"
              placeholder="Search by job title, skills, or company"
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
            />
          </div>

          <div className="jobs-filter-row">
            <button
              type="button"
              className="jobs-filter-item"
            >
              <MapPin size={13} />

              <span>Location</span>

              <ChevronDown size={12} />
            </button>

            <button
              type="button"
              className="jobs-filter-item"
            >
              <GraduationCap size={13} />

              <span>Experience Level</span>

              <ChevronDown size={12} />
            </button>

            <button
              type="button"
              className="jobs-filter-item"
            >
              <Briefcase size={13} />

              <span>Employment Type</span>

              <ChevronDown size={12} />
            </button>

            <button
              type="button"
              className="jobs-filter-item"
            >
              <Briefcase size={13} />

              <span>Company</span>

              <ChevronDown size={12} />
            </button>

            <button
              type="button"
              className="jobs-filter-button"
            >
              <SlidersHorizontal size={13} />
              Filters
            </button>
          </div>
        </div>

        {/* RESULT COUNT */}
        <div className="jobs-toolbar">
          <span>
            {filteredJobs.length}{" "}
            {filteredJobs.length === 1 ? "job" : "jobs"} found
          </span>

          <div className="jobs-sort">
            <span>Sort by:</span>

            <button type="button">
              Most Recent
              <ChevronDown size={11} />
            </button>
          </div>
        </div>

        {/* JOB LIST */}
        <div className="jobs-list-container">
          {filteredJobs.map((job) => {
            const saved = isJobSaved(job.id);

            return (
              <Link
                key={job.id}
                to={`/jobs/${job.id}`}
                className="jobs-list-item"
              >
                {/* COMPANY LOGO */}
                <div className="jobs-company-logo">
                  <CompanyLogo company={job.company} />
                </div>

                {/* JOB CONTENT */}
                <div className="jobs-list-content">
                  <h3>{job.title}</h3>

                  <strong>{job.company}</strong>

                  <div className="jobs-meta">
                    <span>
                      <MapPin size={10} />
                      {job.location}
                    </span>

                    <span className="jobs-dot">•</span>

                    <span>
                      <Briefcase size={10} />
                      {job.type}
                    </span>

                    <span className="jobs-dot">•</span>

                    <span>
                      <GraduationCap size={10} />
                      {job.level}
                    </span>
                  </div>

                  <div className="jobs-skills">
                    {(job.skills || [])
                      .slice(0, 4)
                      .map((skill) => (
                        <span key={skill}>
                          {skill}
                        </span>
                      ))}

                    {(job.skills || []).length > 4 && (
                      <span className="jobs-more">
                        ...
                      </span>
                    )}
                  </div>
                </div>

                {/* RIGHT SIDE */}
                <div className="jobs-list-right">
                  <span>
                    {job.date || "Date not available"}
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
                    onClick={(event) =>
                      handleSaveJob(event, job)
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

        {/* NO RESULTS */}
        {filteredJobs.length === 0 && (
          <div className="jobs-no-results">
            <h3>No jobs found</h3>

            <p>
              Try searching with a different job title,
              company, location, or skill.
            </p>
          </div>
        )}

        {/* PAGINATION */}
        <div className="jobs-pagination">
          <button type="button" className="active">
            1
          </button>

          <button type="button">2</button>

          <button type="button">3</button>

          <span>...</span>

          <button type="button">41</button>

          <button
            type="button"
            aria-label="Next page"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </main>
    </div>
  );
}