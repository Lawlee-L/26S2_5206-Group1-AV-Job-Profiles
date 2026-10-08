import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ArrowLeft,
  MapPin,
  Briefcase,
  GraduationCap,
  CalendarDays,
  DollarSign,
  Bookmark,
  ExternalLink,
} from "lucide-react";

import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyLogo from "../components/CompanyLogo";

import { getJob } from "../api/jobs";

import {
  getFavorites,
  toggleFavorite,
} from "../utils/favorites";

export default function JobDetails() {
  const { id } = useParams();

  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [favorites, setFavorites] = useState(
    () => getFavorites()
  );

  // =========================================
  // LOAD REAL JOB FROM BACKEND
  // =========================================

  useEffect(() => {
    let cancelled = false;

    async function loadJob() {
      try {
        setLoading(true);
        setError("");

        // React Router gives us the encoded sourceKey.
        const sourceKey = decodeURIComponent(id);

        const result = await getJob(sourceKey);

        if (!cancelled) {
          setJob(result.data || null);
        }
      } catch (err) {
        console.error("Failed to load job:", err);

        if (!cancelled) {
          setJob(null);
          setError(
            "The job could not be loaded or is no longer available."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadJob();

    return () => {
      cancelled = true;
    };
  }, [id]);

  // =========================================
  // HELPERS
  // =========================================

  const formatDate = (dateValue) => {
    if (!dateValue) {
      return "Date not available";
    }

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
      return dateValue;
    }

    return date.toLocaleDateString("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const getSkillName = (skill) => {
    if (typeof skill === "string") {
      return skill;
    }

    return skill?.name || "Skill";
  };

  const getExperienceText = (jobData) => {
    if (
      jobData.experienceMinYears != null &&
      jobData.experienceMaxYears != null
    ) {
      return `${jobData.experienceMinYears}–${jobData.experienceMaxYears} years`;
    }

    if (jobData.experienceMinYears != null) {
      return `${jobData.experienceMinYears}+ years`;
    }

    if (jobData.experienceMaxYears != null) {
      return `Up to ${jobData.experienceMaxYears} years`;
    }

    if (jobData.level) {
      return jobData.level;
    }

    return "Not specified";
  };

  const getEmploymentType = (jobData) => {
    return (
      jobData.type ||
      jobData.employmentType ||
      jobData.remoteType ||
      "Not specified"
    );
  };

  const getEducation = (jobData) => {
    if (jobData.education) {
      return jobData.education;
    }

    const qualification = (jobData.skills || []).find(
      (skill) =>
        typeof skill === "object" &&
        skill.type === "qualification"
    );

    return qualification?.name || "Not specified";
  };

  const isSaved = () => {
    if (!job) {
      return false;
    }

    const jobId = job.sourceKey || job.id;

    return favorites.some(
      (item) =>
        String(item.sourceKey || item.id) ===
        String(jobId)
    );
  };

  const handleSaveJob = () => {
    if (!job) {
      return;
    }

    const favoriteJob = {
      ...job,
      id: job.sourceKey || job.id,
    };

    toggleFavorite(favoriteJob);

    setFavorites(getFavorites());
  };

  // =========================================
  // LOADING
  // =========================================

  if (loading) {
    return (
      <div className="app-shell">
        <Header />

        <main className="job-details-page">
          <Link
            to="/jobs"
            className="job-details-back"
          >
            <ArrowLeft size={13} />
            Back to Jobs
          </Link>

          <section className="job-details-header">
            <h1>Loading job...</h1>

            <p>
              Getting the latest job information.
            </p>
          </section>
        </main>

        <Footer />
      </div>
    );
  }

  // =========================================
  // ERROR / NOT FOUND
  // =========================================

  if (error || !job) {
    return (
      <div className="app-shell">
        <Header />

        <main className="job-details-page">
          <Link
            to="/jobs"
            className="job-details-back"
          >
            <ArrowLeft size={13} />
            Back to Jobs
          </Link>

          <section className="job-details-header">
            <h1>Job not found</h1>

            <p>
              {error ||
                "The job you are looking for is no longer available or does not exist."}
            </p>
          </section>
        </main>

        <Footer />
      </div>
    );
  }

  const saved = isSaved();

  // =========================================
  // MAIN PAGE
  // =========================================

  return (
    <div className="app-shell">
      <Header />

      <main className="job-details-page">

        {/* BACK BUTTON */}

        <Link
          to="/jobs"
          className="job-details-back"
        >
          <ArrowLeft size={13} />
          Back to Jobs
        </Link>

        {/* =========================================
            TOP JOB CARD
        ========================================= */}

        <section className="job-details-header">

          <div className="job-details-main">

            <div className="job-details-logo">
              <CompanyLogo
                company={
                  job.company ||
                  "Unknown company"
                }
              />
            </div>

            <div className="job-details-title">

              <h1>
                {job.title ||
                  "Job title not available"}
              </h1>

              <strong>
                {job.company ||
                  "Company not specified"}
              </strong>

              <div className="job-details-meta">

                <span>
                  <MapPin size={11} />

                  {job.location ||
                    "Location not specified"}
                </span>

                <span>•</span>

                <span>
                  <Briefcase size={11} />

                  {getEmploymentType(job)}
                </span>

                <span>•</span>

                <span>
                  <GraduationCap size={11} />

                  {job.level ||
                    "Not specified"}
                </span>

              </div>
            </div>
          </div>

          {/* BUTTONS */}

          <div className="job-details-actions">

            {job.jobUrl ? (
              <a
                href={job.jobUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="apply-job-button"
              >
                Apply Now
              </a>
            ) : (
              <button
                type="button"
                className="apply-job-button"
                disabled
              >
                Apply Now
              </button>
            )}

            <button
              type="button"
              className={
                saved
                  ? "save-job-button saved"
                  : "save-job-button"
              }
              onClick={handleSaveJob}
            >
              <Bookmark
                size={14}
                fill={
                  saved
                    ? "currentColor"
                    : "none"
                }
              />

              {saved
                ? "Saved"
                : "Save Job"}
            </button>

          </div>

          {/* =========================================
              JOB SUMMARY
          ========================================= */}

          <div className="job-summary">

            <div className="job-summary-item">
              <CalendarDays size={19} />

              <div>
                <span>Posted Date</span>

                <strong>
                  {formatDate(
                    job.postedDate
                  )}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <DollarSign size={19} />

              <div>
                <span>Salary</span>

                <strong>
                  {job.salary ||
                    "Salary not available"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <GraduationCap size={19} />

              <div>
                <span>Experience</span>

                <strong>
                  {getExperienceText(job)}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <Briefcase size={19} />

              <div>
                <span>Employment Type</span>

                <strong>
                  {getEmploymentType(job)}
                </strong>
              </div>
            </div>

          </div>
        </section>

        {/* =========================================
            MAIN CONTENT
        ========================================= */}

        <div className="job-details-layout">

          {/* LEFT */}

          <section className="job-description-card">

            <h2>Job Description</h2>

            <p>
              {job.description ||
                job.roleSummary ||
                "No job description is currently available."}
            </p>

            {/* RESPONSIBILITIES */}

            {job.responsibilities &&
              job.responsibilities.length > 0 && (
                <>
                  <h3>Responsibilities</h3>

                  <ul>
                    {job.responsibilities.map(
                      (
                        responsibility,
                        index
                      ) => (
                        <li
                          key={`responsibility-${index}`}
                        >
                          {responsibility}
                        </li>
                      )
                    )}
                  </ul>
                </>
              )}

            {/* REQUIREMENTS */}

            {job.requirements &&
              job.requirements.length > 0 && (
                <>
                  <h3>Requirements</h3>

                  <ul>
                    {job.requirements.map(
                      (
                        requirement,
                        index
                      ) => (
                        <li
                          key={`requirement-${index}`}
                        >
                          {requirement}
                        </li>
                      )
                    )}
                  </ul>
                </>
              )}

            {/* SKILLS */}

            <h3>Preferred Skills</h3>

            {job.skills &&
            job.skills.length > 0 ? (
              <div className="job-details-skills">

                {job.skills.map(
                  (skill, index) => (
                    <span
                      key={`${getSkillName(
                        skill
                      )}-${index}`}
                    >
                      {getSkillName(skill)}
                    </span>
                  )
                )}

              </div>
            ) : (
              <p>
                No skills information available.
              </p>
            )}

          </section>

          {/* =========================================
              RIGHT SIDEBAR
          ========================================= */}

          <aside className="job-details-sidebar">

            <div className="job-side-card">

              <h2>
                About{" "}
                {job.company ||
                  "this company"}
              </h2>

              <p>
                Learn more about{" "}
                {job.company ||
                  "this company"}{" "}
                and its autonomous vehicle
                opportunities.
              </p>

            </div>

            <div className="job-side-card">

              <h2>Job Details</h2>

              <div className="job-detail-field">
                <span>Job ID</span>

                <strong>
                  {job.jobId ||
                    "Not specified"}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Location</span>

                <strong>
                  {job.location ||
                    "Not specified"}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Experience Level</span>

                <strong>
                  {job.level ||
                    "Not specified"}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Education</span>

                <strong>
                  {getEducation(job)}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Employment Type</span>

                <strong>
                  {getEmploymentType(job)}
                </strong>
              </div>

              {job.platform && (
                <div className="job-detail-field">
                  <span>Platform</span>

                  <strong>
                    {job.platform}
                  </strong>
                </div>
              )}

            </div>
          </aside>
        </div>

        {/* =========================================
            ORIGINAL JOB
        ========================================= */}

        <section className="original-job-card">

          <h2>Original Job Posting</h2>

          <p>
            View the original job posting
            {job.company
              ? ` from ${job.company}`
              : ""}.
          </p>

          {job.jobUrl ? (
            <a
              href={job.jobUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="original-job-button"
            >
              View Original Job
              <ExternalLink size={13} />
            </a>
          ) : (
            <button
              type="button"
              disabled
            >
              Original Job Link Unavailable
            </button>
          )}

        </section>

      </main>

      <Footer />
    </div>
  );
}