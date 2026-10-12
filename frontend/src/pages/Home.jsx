import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BriefcaseBusiness, ChartNoAxesCombined } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyLogo from "../components/CompanyLogo";
import { getJobs, getCompanies, getFacets, getLocations } from "../api/jobs";

export default function Home() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setError("");
    Promise.all([getJobs({ page: 1, pageSize: 1 }), getCompanies(), getFacets(), getLocations()])
      .then(([jobs, companies, facets, locations]) => {
        if (!cancelled) setData({ jobs: jobs.pagination?.total ?? 0, companies, skills: (facets.skill || [])
          .filter(item => !(facets.skillTypes?.[item.value] || []).includes("qualification")).slice(0, 8),
          countries: new Set(locations.locations.map(item => item.countryCode).filter(Boolean)).size,
          date: facets.snapshotDate });
      }).catch(() => { if (!cancelled) setError("Live data is unavailable. Start the backend and check the published release."); });
    return () => { cancelled = true; };
  }, [attempt]);
  return <div className="app-shell"><Header /><main className="container-xl product-home">
    <section className="product-hero"><div><span className="eyebrow">AUTONOMOUS VEHICLE CAREERS</span>
      <h1>Discover Autonomous Vehicle Jobs.</h1><p>Find a role that matches your skills. Explore what AV employers need.</p>
      <div className="d-flex flex-wrap gap-2"><Link className="btn btn-primary" to="/jobs"><BriefcaseBusiness size={17} />Browse Jobs<ArrowRight size={16} /></Link>
        <Link className="btn btn-outline-primary" to="/clusters"><ChartNoAxesCombined size={17} />View Insights</Link></div>
    </div><img src="/av-car.png" alt="Autonomous vehicle in a smart city" /></section>
    {error && <div className="alert alert-warning" role="alert">{error}<button className="btn btn-sm btn-outline-primary ms-2" onClick={() => setAttempt(value => value + 1)}>Retry</button></div>}
    <div className="home-quick-stats"><span><strong>{data?.jobs.toLocaleString() ?? "—"}</strong> active AV jobs</span>
      <span><strong>{data?.companies.length ?? "—"}</strong> companies</span><span><strong>{data?.countries ?? "—"}</strong> known countries</span>
      <span className="data-freshness">Dataset: {data?.date || "Version unavailable"}</span></div>
    <section className="home-skill-section"><h2>Popular skills in the published jobs</h2><p>Select a skill to find matching opportunities.</p>
      <div className="home-skills">{data?.skills.map(skill => <Link to={`/jobs?skill=${encodeURIComponent(skill.value)}`} key={skill.value}>
        {skill.value}<span>{skill.count.toLocaleString()}</span><ArrowRight size={13} /></Link>)}</div>
    </section>
    <section className="company-section"><div className="section-heading"><h2>Featured AV Companies</h2><Link to="/jobs">Explore all jobs<ArrowRight size={14} /></Link></div>
      <div className="company-grid">{data?.companies.slice(0, 6).map(company => <Link key={company.name} to={`/jobs?company=${encodeURIComponent(company.name)}`} className="company-box">
        <CompanyLogo company={company.name} /><span className="featured-company-name">{company.name}</span><small>{company.jobCount.toLocaleString()} active jobs</small></Link>)}</div>
    </section>
    <p className="home-data-note">Listings reflect a dated snapshot, not a live vacancy check. Confirm availability on the original company website before applying.</p>
  </main><Footer /></div>;
}
