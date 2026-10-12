import React from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import Header from "../components/Header";
import Footer from "../components/Footer";

export default function About() {
  const { hash } = useLocation();
  if (hash === "#favorites") return <Navigate to="/saved" replace />;
  return <div className="app-shell"><Header /><main className="container-xl information-page py-5">
    <h1>About AV Job Profiles</h1><p>We collect autonomous vehicle job advertisements to help students explore careers and help UWA identify skills for its AV curriculum.</p>
    <section><h2>Two ways to use the project</h2><p><Link to="/jobs">Jobs</Link> lets you search published AV-related roles and save opportunities in this browser.
      <Link to="/clusters"> Insights</Link> explains skill groups and compares available dated snapshots.</p></section>
    <section><h2>Where the information comes from</h2><p>Company recruitment sources are collected and standardised, then analysed for AV relevance and skills. The website reads a published database snapshot, not the live recruitment sites.</p>
      <p>Extracted skills, summaries and provisional cluster names may contain errors. Check the original advertisement before making an application or a curriculum decision.</p></section>
    <section><h2>Saved jobs and privacy</h2><p>Your <Link to="/saved">saved jobs</Link> are stored locally in this browser. They are not a user account and are not synchronised across devices. Company icons may load from external image services.</p></section>
    <section><h2>Project source and documentation</h2><p><a href="https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles" target="_blank" rel="noopener noreferrer">View the repository on GitHub</a> for the pipeline, database guide, tests and project records.</p></section>
  </main><Footer /></div>;
}
