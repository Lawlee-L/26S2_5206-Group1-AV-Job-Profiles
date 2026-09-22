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

export default function Jobs() {
  const [search, setSearch] = useState("");

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
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <div className="jobs-filter-row">
            <button className="jobs-filter-item">
              <MapPin size={13} />

              <span>Location</span>

              <ChevronDown size={12} />
            </button>

            <button className="jobs-filter-item">
              <GraduationCap size={13} />

              <span>Experience Level</span>

              <ChevronDown size={12} />
            </button>

            <button className="jobs-filter-item">
              <Briefcase size={13} />

              <span>Employment Type</span>

              <ChevronDown size={12} />
            </button>

            <button className="jobs-filter-item">
              <Briefcase size={13} />

              <span>Company</span>

              <ChevronDown size={12} />
            </button>

            <button className="jobs-filter-button">
              <SlidersHorizontal size={13} />
              Filters
            </button>
          </div>
        </div>

        {/* RESULT COUNT */}
        <div className="jobs-toolbar">
          <span>1,234 jobs found</span>

          <div className="jobs-sort">
            <span>Sort by:</span>

            <button>
              Most Recent
              <ChevronDown size={11} />
            </button>
          </div>
        </div>

        {/* JOB LIST */}
        <div className="jobs-list-container">
          {filteredJobs.map((job) => (
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
                  {job.skills.slice(0, 4).map((skill) => (
                    <span key={skill}>{skill}</span>
                  ))}

                  {job.skills.length > 4 && (
                    <span className="jobs-more">...</span>
                  )}
                </div>
              </div>

              {/* RIGHT */}
              <div className="jobs-list-right">
                <span>{job.postedDate}</span>

                <button
                  type="button"
                  aria-label="Save job"
                  onClick={(event) => {
                    event.preventDefault();
                  }}
                >
                  <Bookmark size={14} />
                </button>
              </div>
            </Link>
          ))}
        </div>

        {/* PAGINATION */}
        <div className="jobs-pagination">
          <button className="active">1</button>

          <button>2</button>

          <button>3</button>

          <span>...</span>

          <button>41</button>

          <button>
            <ChevronRight size={14} />
          </button>
        </div>
      </main>
    </div>
  );
}