import React from "react";

import {
  Link,
  useParams,
} from "react-router-dom";

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
import CompanyLogo from "../components/CompanyLogo";
import { jobs } from "../data/jobs";

export default function JobDetails() {
  const { id } = useParams();

  /*
    Frontend-only temporary lookup.

    Later your teammates can replace this with
    the real job object from their backend/database.
  */

  const job =
    jobs.find(
      (item) => String(item.id) === String(id)
    ) || jobs[0];

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

        {/* ==========================
            TOP JOB CARD
        ========================== */}

        <section className="job-details-header">
          <div className="job-details-main">
            <div className="job-details-logo">
              <CompanyLogo
                company={job.company}
              />
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
            <button className="apply-job-button">
              Apply Now
            </button>

            <button className="save-job-button">
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
                  {job.postedDate ||
                    "Aug 20, 2026"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <DollarSign size={19} />

              <div>
                <span>Salary</span>

                <strong>
                  {job.salary ||
                    "$150,000 - $200,000 per year"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <GraduationCap size={19} />

              <div>
                <span>Experience</span>

                <strong>
                  {job.experience || "5+ years"}
                </strong>
              </div>
            </div>

            <div className="job-summary-item">
              <Briefcase size={19} />

              <div>
                <span>Employment Type</span>

                <strong>{job.type}</strong>
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
              NVIDIA is seeking a Senior Perception
              Software Engineer to join our Autonomous
              Machines team. You will work on developing
              cutting-edge perception systems for
              self-driving vehicles.
            </p>

            <h3>Responsibilities</h3>

            <ul>
              <li>
                Design and implement perception
                algorithms for AV systems
              </li>

              <li>
                Work with LiDAR, camera, and radar data
              </li>

              <li>
                Optimize performance for real-time
                systems
              </li>

              <li>
                Collaborate with cross-functional teams
              </li>
            </ul>

            <h3>Requirements</h3>

            <ul>
              <li>
                5+ years of experience in C++ software
                development
              </li>

              <li>
                Strong knowledge of computer vision and
                deep learning
              </li>

              <li>
                Experience with LiDAR data processing
              </li>

              <li>
                Bachelor's or Master's degree in
                Computer Science or related field
              </li>
            </ul>

            <h3>Preferred Skills</h3>

            <div className="job-details-skills">
              {(job.skills || [
                "C++",
                "Python",
                "CUDA",
                "Computer Vision",
              ]).map((skill) => (
                <span key={skill}>
                  {skill}
                </span>
              ))}

              <span>Deep Learning</span>
              <span>LiDAR</span>
              <span>ROS2</span>
            </div>
          </section>

          {/* RIGHT SIDEBAR */}

          <aside className="job-details-sidebar">
            {/* ABOUT */}

            <div className="job-side-card">
              <h2>
                About {job.company}
              </h2>

              <p>
                NVIDIA is a global leader in accelerated
                computing. Our work in AI and autonomous
                machines is transforming the future.
              </p>

              <a href="#company">
                View Company Page
                <span>→</span>
              </a>
            </div>

            {/* DETAILS */}

            <div className="job-side-card">
              <h2>Job Details</h2>

              <div className="job-detail-field">
                <span>Job ID</span>

                <strong>
                  NVIDIA-123456
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Location</span>

                <strong>
                  {job.location}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>
                  Experience Level
                </span>

                <strong>
                  {job.level}
                </strong>
              </div>

              <div className="job-detail-field">
                <span>Education</span>

                <strong>
                  Bachelor's or Master's degree
                </strong>
              </div>

              <div className="job-detail-field">
                <span>
                  Employment Type
                </span>

                <strong>
                  {job.type}
                </strong>
              </div>
            </div>
          </aside>
        </div>

        {/* ==========================
            ORIGINAL JOB
        ========================== */}

        <section className="original-job-card">
          <h2>
            Original Job Posting
          </h2>

          <p>
            View the original job posting on{" "}
            {job.company}'s careers page.
          </p>

          <button>
            View Original Job

            <ExternalLink size={13} />
          </button>
        </section>
      </main>
    </div>
  );
}