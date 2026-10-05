import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  Bookmark,
  MapPin,
  Briefcase,
  ArrowRight,
  Search,
  Building2,
  ExternalLink,
} from "lucide-react";

import Header from "../components/Header";
import CompanyLogo from "../components/CompanyLogo";

import {
  getFavorites,
  removeFavorite,
} from "../utils/favorites";

export default function About() {
  const [favorites, setFavorites] = useState([]);

  useEffect(() => {
    setFavorites(getFavorites());
  }, []);

  const handleRemoveFavorite = (jobId) => {
    removeFavorite(jobId);
    setFavorites(getFavorites());
  };

  return (
    <div className="app-shell">
      <Header />

      <main className="about-page">
        {/* ABOUT HERO */}
        <section className="about-hero">
          <span className="about-label">
            ABOUT THE PLATFORM
          </span>

          <h1>About AV Job Tracker</h1>

          <p>
            AV Job Tracker helps students, professionals, and
            researchers explore career opportunities across the
            autonomous vehicle industry in one convenient place.
          </p>

          <Link to="/jobs" className="about-primary-button">
            Explore Jobs
            <ArrowRight size={15} />
          </Link>
        </section>

        {/* ABOUT INFORMATION */}
        <section className="about-section">
          <div className="about-section-heading">
            <h2>What is AV Job Tracker?</h2>

            <p>
              The platform brings autonomous vehicle job
              opportunities together and makes it easier to
              explore companies, job roles, locations, and
              required skills.
            </p>
          </div>

          <div className="about-feature-grid">
            <div className="about-feature-card">
              <Search size={24} />

              <h3>Search Opportunities</h3>

              <p>
                Search jobs by title, company, location, and
                technical skills.
              </p>
            </div>

            <div className="about-feature-card">
              <Building2 size={24} />

              <h3>Explore AV Companies</h3>

              <p>
                Discover opportunities from companies working
                across autonomous driving and mobility.
              </p>
            </div>

            <div className="about-feature-card">
              <Bookmark size={24} />

              <h3>Save Favorites</h3>

              <p>
                Bookmark interesting jobs so you can quickly
                return to them later.
              </p>
            </div>

            <div className="about-feature-card">
              <ExternalLink size={24} />

              <h3>Original Job Sources</h3>

              <p>
                Visit the original company job posting when a
                source link is available.
              </p>
            </div>
          </div>
        </section>

        {/* FAVORITES */}
        <section className="favorites-section">
          <div className="favorites-heading">
            <div>
              <span className="about-label">
                SAVED OPPORTUNITIES
              </span>

              <h2>My Favorites</h2>

              <p>
                Jobs you save from the Jobs page will appear
                here.
              </p>
            </div>

            <span className="favorites-count">
              {favorites.length} saved
            </span>
          </div>

          {favorites.length === 0 ? (
            <div className="favorites-empty">
              <Bookmark size={30} />

              <h3>No saved jobs yet</h3>

              <p>
                Browse available jobs and use the bookmark
                button to save opportunities you're interested
                in.
              </p>

              <Link
                to="/jobs"
                className="about-primary-button"
              >
                Browse Jobs
                <ArrowRight size={15} />
              </Link>
            </div>
          ) : (
            <div className="favorites-list">
              {favorites.map((job) => (
                <div
                  key={job.id}
                  className="favorite-job-card"
                >
                  <div className="favorite-job-logo">
                    <CompanyLogo
                      company={job.company}
                    />
                  </div>

                  <div className="favorite-job-content">
                    <h3>{job.title}</h3>

                    <strong>{job.company}</strong>

                    <div className="favorite-job-meta">
                      <span>
                        <MapPin size={12} />
                        {job.location}
                      </span>

                      <span>
                        <Briefcase size={12} />
                        {job.type}
                      </span>
                    </div>

                    <div className="favorite-job-skills">
                      {(job.skills || [])
                        .slice(0, 4)
                        .map((skill) => (
                          <span key={skill}>
                            {skill}
                          </span>
                        ))}
                    </div>
                  </div>

                  <div className="favorite-job-actions">
                    <span className="favorite-job-date">
                      {job.date ||
                        "Date not available"}
                    </span>

                    <Link
                      to={`/jobs/${job.id}`}
                      className="favorite-view-button"
                    >
                      View Details
                    </Link>

                    <button
                      type="button"
                      className="favorite-remove-button"
                      onClick={() =>
                        handleRemoveFavorite(job.id)
                      }
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* DATA INFORMATION */}
        <section className="about-data-section">
          <h2>About the Job Information</h2>

          <p>
            AV Job Tracker presents job information from
            autonomous vehicle companies in a consistent and
            searchable format. Information may include job
            titles, companies, locations, required skills,
            experience levels, posting dates, and links to
            original job advertisements.
          </p>

          <p>
            Job listings can change or expire over time.
            Where available, users should check the original
            company posting for the latest information before
            applying.
          </p>
        </section>
      </main>
    </div>
  );
}