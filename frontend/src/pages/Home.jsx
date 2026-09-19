import React from "react";
import { Link } from "react-router-dom";
import {
  Bot,
  BriefcaseBusiness,
  BrainCircuit,
  Building2,
  History,
} from "lucide-react";

export default function Home() {
  const companies = [
    { name: "NVIDIA", className: "nvidia-logo" },
    { name: "mobileye", className: "mobileye-logo" },
    { name: "Motional", className: "motional-logo" },
    { name: "pony.ai", className: "pony-logo" },
    { name: "nuro", className: "nuro-logo" },
    { name: "Momenta", className: "momenta-logo" },
    { name: "Plus", className: "plus-logo" },
  ];

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

  const skills = [
    "Programming",
    "AI / Machine Learning",
    "Robotics",
    "Perception",
    "Planning",
    "Cloud / DevOps",
    "Data Science",
  ];

  return (
    <div className="website">
      {/* NAVIGATION */}
      <header className="navbar">
        <Link to="/" className="logo">
          <span className="logo-circle">
            <Bot size={16} />
          </span>
          <span>AV Job Tracker</span>
        </Link>

        <nav className="nav-menu">
          <Link className="active" to="/">
            Home
          </Link>

          <Link to="/jobs">Jobs</Link>

          <a href="#companies">Companies</a>

          <a href="#insights">Insights</a>

          <a href="#about">About</a>
        </nav>

        <Link to="/jobs" className="nav-button">
          View Jobs
        </Link>
      </header>

      {/* HERO */}
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
            A centralized platform for AV job opportunities, skill
            <br />
            demand insights, and industry trends.
          </p>

          <div className="hero-buttons">
            <Link to="/jobs" className="btn-primary">
              Browse Jobs
            </Link>

            <a href="#insights" className="btn-outline">
              View Insights
            </a>
          </div>
        </div>

        {/* Autonomous vehicle visual */}
        <div className="hero-image">
          <div className="sky-glow"></div>

          <div className="city-building building-one">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>

          <div className="city-building building-two">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>

          <div className="city-building building-three">
            <span></span>
            <span></span>
            <span></span>
            <span></span>
          </div>

          <div className="road"></div>

          <div className="sensor sensor-one"></div>
          <div className="sensor sensor-two"></div>
          <div className="sensor sensor-three"></div>

          <div className="av-car">
            <div className="car-lidar"></div>

            <div className="car-roof">
              <div className="car-window"></div>
            </div>

            <div className="car-body">
              <div className="head-light"></div>
            </div>

            <div className="wheel wheel-left"></div>
            <div className="wheel wheel-right"></div>
          </div>
        </div>
      </section>

      {/* OPPORTUNITIES */}
      <section className="home-section opportunities">
        <h2>Explore Opportunities in AV</h2>

        <div className="feature-grid">
          {features.map((feature) => (
            <div className="feature-card" key={feature.title}>
              <div className="feature-icon">{feature.icon}</div>

              <h3>{feature.title}</h3>

              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* COMPANIES */}
      <section
        className="home-section company-section"
        id="companies"
      >
        <h2>Top Companies Hiring</h2>

        <div className="company-grid">
          {companies.map((company) => (
            <div className="company-box" key={company.name}>
              <div className={`company-name ${company.className}`}>
                {company.name}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* MARKET */}
      <section className="market-section" id="insights">
        <h2>AV Job Market at a Glance</h2>

        <div className="market-stats">
          <div>
            <strong>2,500+</strong>
            <span>Active Jobs</span>
          </div>

          <div>
            <strong>100+</strong>
            <span>Companies</span>
          </div>

          <div>
            <strong>50+</strong>
            <span>Skills Tracked</span>
          </div>

          <div>
            <strong>7</strong>
            <span>Countries</span>
          </div>
        </div>
      </section>

      {/* SKILLS */}
      <section className="skills-section">
        <h2>Popular Skill Categories</h2>

        <div className="skill-list">
          {skills.map((skill) => (
            <span key={skill}>{skill}</span>
          ))}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="footer" id="about">
        <div className="footer-content">
          <div className="footer-about">
            <div className="footer-logo">
              <span>
                <Bot size={15} />
              </span>

              AV Job Tracker
            </div>

            <p>
              Empowering the future of
              <br />
              Autonomous Vehicles.
            </p>
          </div>

          <div className="footer-column">
            <h4>Explore</h4>
            <Link to="/jobs">Jobs</Link>
            <a href="#companies">Companies</a>
            <a href="#insights">Insights</a>
            <a href="#about">About</a>
          </div>

          <div className="footer-column">
            <h4>Resources</h4>
            <a href="#skills">Skill Trends</a>
            <a href="#reports">Reports</a>
            <a href="#methodology">Methodology</a>
            <a href="#api">API</a>
          </div>

          <div className="footer-column">
            <h4>Contact</h4>

            <a href="mailto:team@avjobtracker.com">
              team@avjobtracker.com
            </a>

            <div className="social-icons">
              <span>in</span>
              <span>◎</span>
              <span>◉</span>
              <span>⌘</span>
            </div>
          </div>
        </div>

        <div className="copyright">
          © 2026 AV Job Tracker. All rights reserved.
        </div>
      </footer>
    </div>
  );
}