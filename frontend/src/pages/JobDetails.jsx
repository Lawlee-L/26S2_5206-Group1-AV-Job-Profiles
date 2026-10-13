import React, { useEffect, useState } from "react";
import { Link, useParams, useLocation } from "react-router-dom";
import { ArrowLeft, Bookmark, ExternalLink, MapPin } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyLogo from "../components/CompanyLogo";
import { getJob } from "../api/jobs";
import { locationText, workArrangement, salaryText, compactText, groupedSkills } from "../utils/jobDisplay";
import { getFavorites, toggleFavorite } from "../utils/favorites";

const formatDate = value => value ? new Date(value).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" }) : "Not available";
const levelText = value => value ? value.replaceAll("_", " ").replace(/^./, letter => letter.toUpperCase()) : "";
export function safePostingUrl(value) {
  try { const url = new URL(value); return ["https:", "http:"].includes(url.protocol) ? url.href : ""; } catch { return ""; }
}
function experienceText(job) {
  const years = job.experienceMinYears != null && job.experienceMaxYears != null ? `${job.experienceMinYears}–${job.experienceMaxYears} years` :
    job.experienceMinYears != null ? `${job.experienceMinYears}+ years` : job.experienceMaxYears != null ? `Up to ${job.experienceMaxYears} years` : "";
  return [levelText(job.level || job.seniority), years].filter(Boolean).join(" · ");
}

export default function JobDetails() {
  const { id } = useParams();
  const route = useLocation();
  const candidate = route.state?.returnTo;
  const backTo = typeof candidate === "string" && /^\/(jobs|clusters|saved)(\?|$)/.test(candidate) ? candidate : `/jobs${route.search}`;
  const backLabel = backTo.startsWith("/saved") ? "Back to saved jobs" : backTo.startsWith("/clusters") ? "Back to insights" : "Back to Jobs";
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [favorites, setFavorites] = useState(getFavorites);
  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError(""); setJob(null);
    getJob(id).then(result => { if (!cancelled) setJob(result.data || null); })
      .catch(() => { if (!cancelled) setError("The job could not be loaded or is no longer in the published dataset. Check its original posting if you saved a copy."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id, attempt]);
  const key = job?.sourceKey || job?.id;
  const saved = favorites.some(item => String(item.sourceKey || item.id) === String(key));
  const sourceUrl = safePostingUrl(job?.jobUrl);
  const skillGroups = groupedSkills(job?.skills);
  const description = job?.descriptionDisplay || job?.description || "";
  const summary = job?.roleSummary || compactText(description, 500);
  const salaryKnown = job && (job.salaryMin != null || job.salaryMax != null || job.salary || job.salaryDisplay);
  const workKnown = ["remote", "hybrid", "onsite"].includes(job?.remoteType);
  const missing = job ? [!salaryKnown && "salary", !workKnown && "work arrangement"].filter(Boolean) : [];
  return <div className="app-shell"><Header /><main className="job-details-page product-detail">
    <Link to={backTo} className="job-details-back"><ArrowLeft size={15} />{backLabel}</Link>
    {loading ? <p role="status">Loading job…</p> : error || !job ? <section className="empty-state card border-0 p-4" role="alert">
      <h1 className="h4">Job not found</h1><p>{error || "This job is unavailable."}</p><button className="btn btn-outline-primary align-self-start" onClick={() => setAttempt(value => value + 1)}>Retry</button>
    </section> : <>
      <section className="job-details-header">
        <div className="job-details-main"><div className="job-details-logo"><CompanyLogo company={job.company} /></div>
          <div className="job-details-title"><strong>{job.company}</strong><h1>{job.title || "Job title not available"}</h1>
            <div className="job-details-meta"><MapPin size={16} />{locationText(job)}</div></div></div>
        <div className="job-details-actions">{sourceUrl ? <a className="btn btn-primary" href={sourceUrl} target="_blank" rel="noopener noreferrer">Apply Now<ExternalLink size={15} /></a> : <span className="small text-secondary">Original posting unavailable</span>}
          <button className="btn btn-outline-primary" onClick={() => { toggleFavorite({ ...job, id: key }); setFavorites(getFavorites()); }}>
            <Bookmark size={15} fill={saved ? "currentColor" : "none"} />{saved ? "Saved" : "Save Job"}</button></div>
        <dl className="detail-facts">
          {job.postedDate && <div><dt>Posted Date</dt><dd>{formatDate(job.postedDate)}</dd></div>}
          {salaryKnown && <div><dt>Salary</dt><dd>{salaryText(job)}</dd></div>}
          {experienceText(job) && <div><dt>Experience</dt><dd>{experienceText(job)}</dd></div>}
          {workKnown && <div><dt>Work Arrangement</dt><dd>{workArrangement(job)}</dd></div>}
        </dl>
        {missing.length > 0 && <p className="detail-missing">Not stated by the source: {missing.join(", ")}.</p>}
      </section>
      <section className="job-description-card"><h2>Job Description</h2>
        <p>{summary || "No job description is available for this role."}</p>
        {job.roleSummary && <p className="extraction-note">Automatically prepared summary. The original advertisement is the authoritative source.</p>}
        {description && <details className="source-field-details p-3 mb-3"><summary>Full job description</summary><p className="source-body">{description}</p></details>}
        {(job.responsibilities || []).length > 0 && <><h3>Responsibilities</h3><ul>{job.responsibilities.map((text, index) => <li key={index}>{text}</li>)}</ul></>}
        {(job.requirements || []).length > 0 && <><h3>Requirements</h3><ul>{job.requirements.map((text, index) => <li key={index}>{text}</li>)}</ul></>}
        <h3>Extracted Skills</h3><p className="extraction-note">Automatically extracted from the posting; not a separate list of employer-preferred skills.</p>
        {Object.entries(skillGroups).map(([group, names]) => names.length > 0 && <div className="detail-skill-group" key={group}><h4>{group}</h4><div className="job-details-skills">
          {names.map(name => <Link to={`/jobs?skill=${encodeURIComponent(name)}`} key={name}>{name}</Link>)}</div></div>)}
        {!job.skills?.length && <p>No skills information available.</p>}
      </section>
      <details className="source-field-details detail-source p-3"><summary>Data source and original fields</summary>
        <p>Published snapshot, not a live vacancy check. Confirm availability on the original recruitment website before applying.</p>
        <dl className="source-facts">{job.lastSeenDate && <><dt>Last seen in collection</dt><dd>{formatDate(job.lastSeenDate)}</dd></>}
          <dt>Recruitment platform</dt><dd>{job.platform || "Not available"}</dd><dt>Internal record ID</dt><dd>{job.jobId || key}</dd></dl>
        {(job.locationDisplay || job.location) && <details><summary>Full location information from the source</summary><p className="source-body">{job.locationDisplay || job.location}</p></details>}
        {(job.salaryDisplay || job.salary) && <details><summary>Full salary information from the source</summary><p className="source-body">{job.salaryDisplay || job.salary}</p></details>}
      </details>
    </>}
  </main><Footer /></div>;
}
