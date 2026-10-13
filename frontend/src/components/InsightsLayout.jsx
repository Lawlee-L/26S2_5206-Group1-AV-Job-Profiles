import React from "react";
import { NavLink } from "react-router-dom";
import { Layers3, ChartNoAxesCombined } from "lucide-react";
import Header from "./Header";
import Footer from "./Footer";

export default function InsightsLayout({ title, subtitle, loading, error, retry, children }) {
  return <div className="app-shell"><Header /><main className="container-xl insights-page py-4">
    <div className="career-heading"><span className="eyebrow">INDUSTRY INSIGHTS</span><h1>{title}</h1><p>{subtitle}</p></div>
    <nav className="insights-nav" aria-label="Analysis navigation">
      <NavLink to="/clusters"><Layers3 size={17} />Skill clusters</NavLink>
      <NavLink to="/trends"><ChartNoAxesCombined size={17} />Historical trends</NavLink>
    </nav>
    {loading ? <div className="insight-loading" role="status"><span className="spinner-border spinner-border-sm me-2" />Loading published analysis…</div> :
      error ? <div className="alert alert-danger" role="alert">{error}<button className="btn btn-outline-primary ms-3" onClick={retry}>Retry</button></div> : children}
  </main><Footer /></div>;
}

export function InsightMetrics({ items }) {
  return <div className={`insight-metrics metric-count-${items.length} mb-3`}>{items.map(({ label, value, note }) => <div className="card border-0" key={label}>
    <span className="metric-label">{label}</span><strong>{value == null ? "—" : value.toLocaleString()}</strong><small>{note}</small>
  </div>)}</div>;
}
