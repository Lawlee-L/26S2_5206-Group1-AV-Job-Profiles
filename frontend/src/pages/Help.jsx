import React from "react";
import { Link } from "react-router-dom";

import {
  Search,
  Bookmark,
  Briefcase,
  ExternalLink,
  HelpCircle,
  ArrowRight,
} from "lucide-react";

import Header from "../components/Header";
import Footer from "../components/Footer";

export default function Help() {
  return (
    <div className="app-shell">
      <Header />

      <main className="help-page">
        {/* HERO */}
        <section className="help-hero">
          <span className="help-label">HELP CENTRE</span>

          <h1>How can we help?</h1>

          <p>
            Learn how to search, explore, and save autonomous
            vehicle job opportunities using AV Job Tracker.
                  </p>
                  <Link to="/jobs" className="hero-action-button">
  Browse Jobs
  <ArrowRight size={15} />
</Link>
        </section>

        {/* HELP CARDS */}
        <section className="help-section">
          <div className="help-heading">
            <h2>Using AV Job Tracker</h2>

            <p>
              Everything you need to get started with the platform.
            </p>
          </div>

          <div className="help-grid">
            <div className="help-card">
              <Search size={22} />

              <h3>Search for Jobs</h3>

              <p>
                Visit the Jobs page and search by job title,
                company, location, or skill.
              </p>

              <Link to="/jobs">
                Browse Jobs <ArrowRight size={13} />
              </Link>
            </div>

            <div className="help-card">
              <Briefcase size={22} />

              <h3>View Job Details</h3>

              <p>
                Select a job to view information such as its
                description, location, skills, experience level,
                and posting date.
              </p>
            </div>

            <div className="help-card">
              <Bookmark size={22} />

              <h3>Save Jobs</h3>

              <p>
                Click the bookmark icon on a job to save it. Your
                saved jobs can be viewed in the Favorites section
                on the About page.
              </p>

              <Link to="/about">
                View Favorites <ArrowRight size={13} />
              </Link>
            </div>

            <div className="help-card">
              <ExternalLink size={22} />

              <h3>Original Job Posting</h3>

              <p>
                When an original source is available, use the
                original job link to visit the company's job
                posting before applying.
              </p>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="help-faq">
          <div className="help-heading">
            <span className="help-label">
              FREQUENTLY ASKED QUESTIONS
            </span>

            <h2>Common Questions</h2>
          </div>

          <div className="faq-list">
            <div className="faq-item">
              <h3>What is AV Job Tracker?</h3>

              <p>
                AV Job Tracker is a platform for exploring job
                opportunities across the autonomous vehicle
                industry.
              </p>
            </div>

            <div className="faq-item">
              <h3>How do I save a job?</h3>

              <p>
                Click the bookmark icon next to a job. The job
                will then appear in your saved Favorites section.
              </p>
            </div>

            <div className="faq-item">
              <h3>Can I apply directly through AV Job Tracker?</h3>

              <p>
                AV Job Tracker helps you discover opportunities.
                Where available, the original job posting link
                takes you to the company's website to continue
                the application process.
              </p>
            </div>

            <div className="faq-item">
              <h3>Why is some job information unavailable?</h3>

              <p>
                The information available depends on the original
                job posting. Some companies may not provide
                salary, experience, education, or other details.
              </p>
            </div>

            <div className="faq-item">
              <h3>Are all listed jobs still available?</h3>

              <p>
                Job advertisements can change or expire. Always
                check the original company posting for the latest
                information.
              </p>
            </div>
          </div>
        </section>

        {/* NEED HELP */}
        <section className="help-contact">
          <HelpCircle size={28} />

          <div>
            <h2>Need more help?</h2>

            <p>
              Explore the About page to learn more about AV Job
              Tracker and how job information is presented.
            </p>
          </div>

          <Link to="/about">
            About AV Job Tracker
            <ArrowRight size={14} />
          </Link>
              </section>
              
          </main>
              {/* FOOTER */}
               <Footer />
    </div>
  );
}