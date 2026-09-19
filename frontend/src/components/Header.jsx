import React from "react";
import { NavLink, Link } from "react-router-dom";
import { Bot } from "lucide-react";

export default function Header({ buttonText = "View Jobs", buttonTo = "/jobs" }) {
  return (
    <header className="site-header">
      <Link className="brand" to="/">
        <span className="brand-icon"><Bot size={18} /></span>
        <span>AV Job Tracker</span>
      </Link>

      <nav className="nav-links">
        <NavLink to="/">Home</NavLink>
        <NavLink to="/jobs">Jobs</NavLink>
        <a href="#companies">Companies</a>
        <a href="#insights">Insights</a>
        <a href="#about">About</a>
      </nav>

      <Link className="nav-cta" to={buttonTo}>{buttonText}</Link>
    </header>
  );
}
