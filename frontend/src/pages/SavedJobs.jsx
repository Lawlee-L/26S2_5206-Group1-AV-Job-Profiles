import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, MapPin, X } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyLogo from "../components/CompanyLogo";
import { getFavorites, removeFavorite } from "../utils/favorites";
import { locationText, salaryText } from "../utils/jobDisplay";

export default function SavedJobs() {
  const [jobs, setJobs] = useState(getFavorites);
  return <div className="app-shell"><Header /><main className="jobs-page container-xl py-4 py-lg-5">
    <div className="career-heading"><h1>Saved jobs</h1><p>{jobs.length} saved in this browser. These are saved copies; check the latest posting before applying.</p></div>
    {!jobs.length ? <section className="empty-state card border-0 p-5 text-center"><Bookmark size={28} className="mx-auto mb-3" /><h2 className="h4">No saved jobs yet</h2>
      <p>Use the bookmark button on a job to save it here.</p><Link to="/jobs" className="btn btn-primary mx-auto">Browse Jobs</Link></section> :
      <div className="jobs-list-container">{jobs.map(job => { const key = job.sourceKey || job.id; return <article className="job-result card border-0" key={key}>
        <div className="job-result-logo"><CompanyLogo company={job.company} /></div><div className="job-result-content"><span className="job-company-name">{job.company}</span>
          <h2><Link className="job-title-link" to={`/jobs/${encodeURIComponent(key)}`} state={{ returnTo: "/saved" }}>{job.title}</Link></h2>
          <div className="job-result-meta"><span><MapPin size={15} />{locationText(job)}</span></div>
          {(job.salary || job.salaryMin != null || job.salaryMax != null) && <p className="job-salary-text">{salaryText(job)}</p>}</div>
        <div className="job-result-side"><button className="bookmark-control" aria-label={`Remove ${job.title} from saved jobs`} onClick={() => { removeFavorite(key); setJobs(getFavorites()); }}><X size={18} /></button></div>
      </article>; })}</div>}
  </main><Footer /></div>;
}
