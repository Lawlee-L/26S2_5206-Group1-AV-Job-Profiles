import React from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Briefcase,
  ExternalLink,
  Database,
  ShieldCheck,
  AlertCircle,
  ArrowRight,
} from "lucide-react";

import Header from "../components/Header";
import Footer from "../components/Footer";
export default function Terms() {
  return (
    <div className="app-shell">
      <Header />

      <main className="terms-page">
        {/* HERO */}
        <section className="terms-hero">
          <span className="terms-label">
            TERMS AND CONDITIONS
          </span>

          <h1>Terms and Conditions</h1>

          <p>
            Please read these terms before using AV Job Tracker.
            The platform is designed to help users discover and
            explore opportunities in the autonomous vehicle
            industry.
          </p>

          <span className="terms-updated">
            Last updated: October 2026
          </span>

          <Link to="/help" className="hero-action-button">
  Go to Help
  <ArrowRight size={15} />
</Link>
        </section>

        {/* INTRO */}
        <section className="terms-content">
          <div className="terms-intro">
            <FileText size={24} />

            <div>
              <h2>Using AV Job Tracker</h2>

              <p>
                By using AV Job Tracker, you agree to use the
                information provided on this platform responsibly
                and for legitimate job-search, research, and
                career exploration purposes.
              </p>
            </div>
          </div>

          {/* TERM 1 */}
          <div className="terms-card">
            <div className="terms-card-icon">
              <Briefcase size={20} />
            </div>

            <div>
              <span>01</span>

              <h2>Job Information</h2>

              <p>
                AV Job Tracker presents job information collected
                from publicly available job advertisements and
                company career sources.
              </p>

              <p>
                Job information may change, expire, or become
                unavailable. Users should verify important
                information with the original employer before
                applying for a position.
              </p>
            </div>
          </div>

          {/* TERM 2 */}
          <div className="terms-card">
            <div className="terms-card-icon">
              <ExternalLink size={20} />
            </div>

            <div>
              <span>02</span>

              <h2>External Websites</h2>

              <p>
                AV Job Tracker may provide links to external
                company websites and original job advertisements.
                These websites are operated independently from
                AV Job Tracker.
              </p>

              <p>
                We are not responsible for the availability,
                content, privacy practices, or accuracy of
                external websites.
              </p>
            </div>
          </div>

          {/* TERM 3 */}
          <div className="terms-card">
            <div className="terms-card-icon">
              <Database size={20} />
            </div>

            <div>
              <span>03</span>

              <h2>Accuracy of Information</h2>

              <p>
                We aim to present job information in a clear and
                useful format, but we cannot guarantee that every
                listing is complete, current, or error-free.
              </p>

              <p>
                Salary, experience, employment type, education,
                location, and skill information may not be
                available for every job.
              </p>
            </div>
          </div>

          {/* TERM 4 */}
          <div className="terms-card">
            <div className="terms-card-icon">
              <ShieldCheck size={20} />
            </div>

            <div>
              <span>04</span>

              <h2>Saved Jobs</h2>

              <p>
                The Favorites feature allows users to save job
                listings in their browser for convenient access.
                Saved jobs may be lost if browser storage is
                cleared or unavailable.
              </p>
            </div>
          </div>

          {/* TERM 5 */}
          <div className="terms-card">
            <div className="terms-card-icon">
              <AlertCircle size={20} />
            </div>

            <div>
              <span>05</span>

              <h2>No Guarantee of Employment</h2>

              <p>
                AV Job Tracker is an information and job discovery
                platform. Displaying a job opportunity does not
                guarantee an interview, employment offer, or
                successful application.
              </p>
            </div>
          </div>

          {/* TERM 6 */}
          <div className="terms-card">
            <div className="terms-card-icon">
              <FileText size={20} />
            </div>

            <div>
              <span>06</span>

              <h2>Changes to These Terms</h2>

              <p>
                These terms may be updated when the platform,
                features, or data sources change. The latest
                version will be displayed on this page.
              </p>
            </div>
          </div>
        </section>

        {/* BOTTOM */}
        <section className="terms-help">
          <div>
            <h2>Have a question?</h2>

            <p>
              Visit the Help page for more information about
              using AV Job Tracker.
            </p>
          </div>

          <Link to="/help">
            Visit Help
            <ArrowRight size={14} />
          </Link>
        </section>
      </main>
      <Footer />
    </div>
  );
}