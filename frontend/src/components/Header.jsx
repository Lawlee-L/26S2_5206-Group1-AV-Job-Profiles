import React, { useState } from "react";
import { Menu, X, Bookmark } from "lucide-react";
import { NavLink, Link, useLocation } from "react-router-dom";

export default function Header() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const insights = ["/clusters", "/trends"].includes(pathname);
  return <header className="site-header">
    <Link to="/" className="brand"><img src="/UWA.png" alt="The University of Western Australia" className="brand-logo" /></Link>
    <button type="button" className="btn btn-outline-primary mobile-menu-button" aria-label="Toggle navigation" aria-expanded={open}
      aria-controls="main-navigation" onClick={() => setOpen(!open)}>{open ? <X size={18} /> : <Menu size={18} />}</button>
    <nav id="main-navigation" className={`nav-links ${open ? "is-open" : ""}`} aria-label="Main navigation" onClick={() => setOpen(false)}>
      <NavLink to="/" end>Home</NavLink><NavLink to="/jobs">Jobs</NavLink>
      <Link to="/clusters" className={insights ? "active" : ""} aria-current={insights ? "page" : undefined}>Insights</Link>
      <NavLink to="/saved"><Bookmark size={15} />Saved Jobs</NavLink>
    </nav>
  </header>;
}
