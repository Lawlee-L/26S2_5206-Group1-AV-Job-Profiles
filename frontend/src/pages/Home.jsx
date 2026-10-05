import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  BriefcaseBusiness,
  BrainCircuit,
  Building2,
  History,
} from "lucide-react";

import Header from "../components/Header";
import Footer from "../components/Footer";

import {
  getJobs,
  getCompanies,
  getSkills,
} from "../api/jobs";

export default function Home() {
  // =========================================
  // REAL MARKET STATISTICS
  // =========================================

  const [stats, setStats] = useState({
    jobs: null,
    companies: null,
    skills: null,
    countries: 7,
  });

  const [loadingStats, setLoadingStats] = useState(true);

  // =========================================
  // COMPANY CARDS
  // Keep original design / company selection
  // =========================================

  const companies = [
    {
      name: "NVIDIA",
      label: "NVIDIA",
      className: "nvidia-logo",
    },
    {
      name: "Mobileye",
      label: "mobileye",
      className: "mobileye-logo",
    },
    {
      name: "Motional",
      label: "Motional",
      className: "motional-logo",
    },
    {
      name: "Pony.AI",
      label: "pony.ai",
      className: "pony-logo",
    },
    {
      name: "Nuro",
      label: "nuro",
      className: "nuro-logo",
    },
    {
      name: "Momenta",
      label: "Momenta",
      className: "momenta-logo",
    },
    {
      name: "Plus AI",
      label: "Plus",
      className: "plus-logo",
    },
  ];

  // =========================================
  // FEATURES
  // =========================================

  const features = [
    {
      icon: <BriefcaseBusiness size={19} />,
      title: "Latest AV Jobs",
      description:
        "Find the newest job openings from top AV companies.",
    },
    {
      icon: <BrainCircuit size={19} />,
      title: "Skill Insights",
      description:
        "Discover the most in-demand skills in the autonomous vehicle industry.",
    },
    {
      icon: <Building2 size={19} />,
      title: "Company Insights",
      description:
        "Explore AV companies and their latest opportunities.",
    },
    {
      icon: <History size={19} />,
      title: "Historical Tracking",
      description:
        "Track job trends and market changes over time.",
    },
  ];

  // =========================================
  // POPULAR SKILL CATEGORIES
  // =========================================

  const skills = [
    "Programming",
    "AI / Machine Learning",
    "Robotics",
    "Perception",
    "Planning",
    "Cloud / DevOps",
    "Data Science",
  ];

  // =========================================
  // LOAD REAL DATA FROM BACKEND
  // =========================================

  useEffect(() => {
    let cancelled = false;

    async function loadMarketData() {
      try {
        setLoadingStats(true);

        const [
          jobsResult,
          companiesResult,
          skillsResult,
        ] = await Promise.all([
          getJobs({
            page: 1,
            pageSize: 1,
          }),

          getCompanies(),

          getSkills(),
        ]);

        if (cancelled) {
          return;
        }

        const pagination =
          jobsResult.pagination || {};

        const totalJobs =
          pagination.total ??
          pagination.totalItems ??
          pagination.total_count ??
          jobsResult.data?.length ??
          0;

        setStats({
          jobs: totalJobs,
          companies: companiesResult.length,
          skills: skillsResult.length,

          // Keep current project value until
          // we calculate it directly from DB.
          countries: 7,
        });
      } catch (error) {
        console.error(
          "Failed to load home page market data:",
          error
        );
      } finally {
        if (!cancelled) {
          setLoadingStats(false);
        }
      }
    }

    loadMarketData();

    return () => {
      cancelled = true;
    };
  }, []);

  // =========================================
  // NUMBER FORMAT
  // =========================================

  const formatNumber = (number) => {
    if (number == null) {
      return "—";
    }

    return number.toLocaleString("en-AU");
  };

  // =========================================
  // PAGE
  // =========================================

  return (
    <div className="website">

      {/* =====================================
          NAVIGATION
      ====================================== */}

      <Header />

      {/* =====================================
          HERO
      ====================================== */}

      <section className="hero-section">

        <div className="hero-content">

          <h1>
            Discover Autonomous
            <br />
            Vehicle Jobs.
            <br />
            Track Skills. Grow Your
            <br />
            Future.
          </h1>

          <p>
            A centralized platform for AV job opportunities,
            skill
            <br />
            demand insights, and industry trends.
          </p>

          <div className="hero-buttons">

            <Link
              to="/jobs"
              className="btn-primary"
            >
              Browse Jobs
            </Link>

            <a
              href="#insights"
              className="btn-outline"
            >
              View Insights
            </a>

          </div>

        </div>

        <div className="hero-image">

          <img
            src="/av-car.png"
            alt="Autonomous vehicle in a smart city"
            className="hero-car-image"
          />

        </div>

      </section>

      {/* =====================================
          OPPORTUNITIES
      ====================================== */}

      <section className="home-section opportunities">

        <h2>
          Explore Opportunities in AV
        </h2>

        <div className="feature-grid">

          {features.map((feature) => (

            <div
              className="feature-card"
              key={feature.title}
            >

              <div className="feature-icon">
                {feature.icon}
              </div>

              <h3>
                {feature.title}
              </h3>

              <p>
                {feature.description}
              </p>

            </div>

          ))}

        </div>

      </section>

      {/* =====================================
          COMPANIES
      ====================================== */}

      <section
        className="home-section company-section"
        id="companies"
      >

        <h2>
          Featured AV Companies
        </h2>

        <div className="company-grid">

          {companies.map((company) => (

            <Link
              key={company.name}
              to={`/jobs?company=${encodeURIComponent(
                company.name
              )}`}
              className="company-box"
              title={`View ${company.name} jobs`}
            >

              <div
                className={`company-name ${company.className}`}
              >
                {company.label}
              </div>

            </Link>

          ))}

        </div>

      </section>

      {/* =====================================
          MARKET STATISTICS
      ====================================== */}

      <section
        className="market-section"
        id="insights"
      >

        <h2>
          AV Job Market at a Glance
        </h2>

        <div className="market-stats">

          {/* ACTIVE JOBS */}

          <div>

            <strong>
              {loadingStats
                ? "—"
                : formatNumber(stats.jobs)}
            </strong>

            <span>
              Active Jobs
            </span>

          </div>

          {/* COMPANIES */}

          <div>

            <strong>
              {loadingStats
                ? "—"
                : formatNumber(stats.companies)}
            </strong>

            <span>
              Companies
            </span>

          </div>

          {/* SKILLS */}

          <div>

            <strong>
              {loadingStats
                ? "—"
                : formatNumber(stats.skills)}
            </strong>

            <span>
              Skills Tracked
            </span>

          </div>

          {/* COUNTRIES */}

          <div>

            <strong>
              10+
            </strong>

            <span>
              Countries
            </span>

          </div>

        </div>

      </section>

      {/* =====================================
          SKILL CATEGORIES
      ====================================== */}

      <section className="skills-section">

        <h2>
          Popular Skill Categories
        </h2>

        <div className="skill-list">

          {skills.map((skill) => (

            <span key={skill}>
              {skill}
            </span>

          ))}

        </div>

      </section>

      {/* =====================================
          FOOTER
      ====================================== */}

      <Footer />

    </div>
  );
}