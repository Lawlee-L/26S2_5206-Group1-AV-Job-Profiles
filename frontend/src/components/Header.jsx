import React from "react";
import { NavLink, Link } from "react-router-dom";
import { Bot } from "lucide-react";

export default function Header({
  buttonText = "View Jobs",
  buttonTo = "/jobs",
}) {
  return (
    <header className="site-header">
      {/* LOGO / BRAND */}
      <Link className="brand" to="/">
        <span className="brand-icon">
          <Bot size={18} />
        </span>

        <span>AV Job Tracker</span>
      </Link>

      {/* NAVIGATION */}
      <nav className="nav-links">
        <NavLink
          to="/"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Home
        </NavLink>

        <NavLink
          to="/jobs"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          Jobs
        </NavLink>

        <NavLink
          to="/about"
          className={({ isActive }) =>
            isActive ? "active" : ""
          }
        >
          About
        </NavLink>

        {/* Help page will be connected next */}
        <a href="#insights">
          Help
        </a>

        {/* Terms page will be connected later */}
        <a href="#terms">
          Terms and Conditions
        </a>
      </nav>

      {/* RIGHT BUTTON */}
      <Link
        className="nav-cta"
        to={buttonTo}
      >
        {buttonText}
      </Link>
    </header>
  );
}