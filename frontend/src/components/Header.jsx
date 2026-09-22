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
        <a href="#companies">About</a>
        <a href="#insights">Help</a>
        <a href="#about">Team And Conditions</a>
      </nav>

      <Link className="nav-cta" to={buttonTo}>{buttonText}</Link>
    </header>
  );
}
