import React from "react";
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
import { getJobById } from "../data/jobs";

export default function JobDetails() {
  const { id } = useParams();

  // Get the selected job using its ID
  const job = getJobById(id);

  // Handle invalid job ID
  if (!job) {
    return (
      <div className="app-shell">
        <Header />

        <main className="job-details-page">
          <Link to="/jobs" className="job-details-back">
            <ArrowLeft size={13} />
            Back to Jobs
          </Link>

          <section className="job-details-header">
            <h1>Job not found</h1>
            <p>
              The job you are looking for is no longer available
              or does not exist.
            </p>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Header />

      <main className="job-details-page">
        {/* BACK BUTTON */}
        <Link to="/jobs" className="job-details-back">
          <ArrowLeft size={13} />
          Back to Jobs
        </Link>

        {/* ==========================
            TOP JOB CARD
        ========================== */}
        <section className="job-details-header">
          <div className="job-details-main">
            <div className="job-details-logo">
              <CompanyLogo company={job.company} />
            </div>

            <div className="job-details-title">
              <h1>{job.title}</h1>

              <strong>{job.company}</strong>

              <div className="job-details-meta">
                <span>
                  <MapPin size={11} />
                  {job.location}
                </span>

                <span>•</span>

                <span>
                  <Briefcase size={11} />
                  {job.type}
                </span>

                <span>•</span>

                <span>
                  <GraduationCap size={11} />
                  {job.level}
                </span>
              </div>
            </div>
          </div>

          {/* BUTTONS */}
          <div className="job-details-actions">
            <a
              href={job.originalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="apply-job-button"
            >
              Apply Now
            </a>

            <button
              type="button"
              className="save-job-button"
            >
              <Bookmark size={14} />
              Save Job
            </button>
          </div>

          {/* JOB SUMMARY */}
          <div className="job-summary">
            <div className="job-summary-item">
              <CalendarDays size={19} />

              <div>
                <span>Posted Date</span>
                <strong>
                  {job.date || "Date not available"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <DollarSign size={19} />

              <div>
                <span>Salary</span>
                <strong>
                  {job.salary || "Salary not available"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <GraduationCap size={19} />

              <div>
                <span>Experience</span>
                <strong>
                  {job.experience || "Not specified"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <Briefcase size={19} />

              <div>
                <span>Employment Type</span>
                <strong>
                  {job.type || "Not specified"}
                </strong>
              </div>
            </div>
          </div>
        </section>

        {/* ==========================
            MAIN CONTENT
        ========================== */}
        <div className="job-details-layout">
          {/* LEFT */}
          <section className="job-description-card">
            <h2>Job Description</h2>

            <p>
              {job.description ||
                "No job description is currently available."}
            </p>

            <h3>Responsibilities</h3>

            <ul>
              {job.responsibilities?.map((responsibility) => (
                <li key={responsibility}>
                  {responsibility}
                </li>
              ))}
            </ul>

            <h3>Requirements</h3>

            <ul>
              {job.requirements?.map((requirement) => (
                <li key={requirement}>
                  {requirement}
                </li>
              ))}
            </ul>

            <h3>Preferred Skills</h3>

            <div className="job-details-skills">
              {job.skills?.map((skill) => (
                <span key={skill}>
                  {skill}
                </span>
              ))}
            </div>
          </section>

          {/* RIGHT SIDEBAR */}
          <aside className="job-details-sidebar">
            <div className="job-side-card">
              <h2>About {job.company}</h2>

              <p>
                Learn more about {job.company} and its
                autonomous vehicle opportunities.
              </p>
            </div>

            <div className="job-side-card">
              <h2>Job Details</h2>

              <div className="job-detail-field">
                <span>Job ID</span>
                <strong>{job.id}</strong>
              </div>

              <div className="job-detail-field">
                <span>Location</span>
                <strong>{job.location}</strong>
              </div>

              <div className="job-detail-field">
                <span>Experience Level</span>
                <strong>{job.level}</strong>
              </div>

              <div className="job-detail-field">
                <span>Education</span>
                <strong>
                  {job.education || "Not specified"}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Employment Type</span>
                <strong>{job.type}</strong>
              </div>
            </div>
          </aside>
        </div>

        {/* ==========================
            ORIGINAL JOB
        ========================== */}
        <section className="original-job-card">
          <h2>Original Job Posting</h2>

          <p>
            View the original job posting on{" "}
            {job.company}'s careers page.
          </p>

          {job.originalUrl && job.originalUrl !== "#" ? (
            <a
              href={job.originalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="original-job-button"
            >
              View Original Job
              <ExternalLink size={13} />
            </a>
          ) : (
            <button type="button" disabled>
              Original Job Link Unavailable
            </button>
          )}
        </section>
            {/* FOOTER */}
         
      </main>
      <Footer />
    </div>
  );
}