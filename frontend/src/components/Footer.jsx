import React from "react";
import { Link } from "react-router-dom";
import { Bot } from "lucide-react";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">

        {/* BRAND */}
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

        {/* EXPLORE */}
        <div className="footer-column">
          <h4>Explore</h4>

          <Link to="/jobs">Jobs</Link>
          <Link to="/about">About</Link>
          <Link to="/help">Help</Link>
          <Link to="/terms">Terms & Conditions</Link>
        </div>

        {/* RESOURCES */}
        <div className="footer-column">
          <h4>Resources</h4>

          <Link to="/jobs">Job Opportunities</Link>
          <Link to="/about">About the Platform</Link>
          <Link to="/help">Help Centre</Link>
        </div>

        {/* CONTACT */}
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
  );
}