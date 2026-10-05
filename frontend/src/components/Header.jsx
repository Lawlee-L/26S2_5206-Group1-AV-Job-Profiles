import React from "react";
import { NavLink, Link } from "react-router-dom";

export default function Header({
  buttonText = "View Jobs",
  buttonTo = "/jobs",
}) {
  return (
    <header className="site-header">
      {/* LOGO / BRAND */}
 <Link to="/" className="brand">
  <img
    src="/UWA.png"
    alt="The University of Western Australia"
    className="brand-logo"
  />
</Link>

      {/* NAVIGATION */}
      <nav className="nav-links">
        <NavLink
          to="/"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Home
        </NavLink>

        <NavLink
          to="/jobs"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Jobs
        </NavLink>

        <NavLink
          to="/about"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          About
        </NavLink>

        <NavLink
          to="/help"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Help
        </NavLink>

        <NavLink
          to="/terms"
          className={({ isActive }) => (isActive ? "active" : "")}
        >
          Terms and Conditions
        </NavLink>
      </nav>

      {/* RIGHT BUTTON */}
      <Link className="nav-cta" to={buttonTo}>
        {buttonText}
      </Link>
    </header>
  );
}