import React from "react";
import { Link } from "react-router-dom";
import { Github, ArrowUpRight } from "lucide-react";

export default function Footer() {
  return <footer className="footer product-footer"><div className="footer-inner">
    <span>UWA CITS5206 · Group 1 · AV Job Profiles</span>
    <nav aria-label="Project information"><Link to="/about">About</Link><Link to="/help">Help</Link><Link to="/terms">Terms & Conditions</Link>
      <a href="https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles" target="_blank" rel="noopener noreferrer"><Github size={16} />Project on GitHub<ArrowUpRight size={13} /></a>
    </nav>
  </div></footer>;
}
