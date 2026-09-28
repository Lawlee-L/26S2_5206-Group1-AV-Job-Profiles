import React from "react";
import { Bot } from "lucide-react";

export default function Footer() {
  return (
    <footer className="footer">
      <div>
        <div className="footer-brand">
          <span className="brand-icon light"><Bot size={17} /></span>
          <strong>AV Job Tracker</strong>
        </div>
        <p>Empowering the future of<br />Autonomous Vehicles.</p>
      </div>

      <div>
        <h4>Explore</h4>
        <a href="/jobs">Jobs</a>
        <a href="#companies">Companies</a>
        <a href="#insights">Insights</a>
        <a href="#about">About</a>
      </div>

      <div>
        <h4>Resources</h4>
        <a href="#skills">Skill Trends</a>
        <a href="#reports">Reports</a>
        <a href="#methodology">Methodology</a>
        <a href="#api">API</a>
      </div>

      <div>
        <h4>Contact</h4>
        <a href="mailto:team@avjobtracker.com">team@avjobtracker.com</a>
        <div className="socials">in &nbsp; ◉ &nbsp; ◌ &nbsp; ⌘</div>
      </div>

      <div className="copyright">© 2026 AV Job Tracker. All rights reserved.</div>
    </footer>
  );
}
