import React, { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, ChevronDown, ArrowUpRight } from "lucide-react";
import useInsights from "../hooks/useInsights";
import InsightChart from "../components/InsightChart";
import InsightsLayout, { InsightMetrics } from "../components/InsightsLayout";

export default function Clusters() {
  const { data, loading, error, retry } = useInsights();
  const [params, setParams] = useSearchParams();
  const query = params.get("search") || "";
  const mode = params.get("group") || "all";
  const sort = params.get("order") || "jobs";
  const rawLimit = Number(params.get("limit") || 18);
  const limit = Number.isInteger(rawLimit) && rawLimit > 0 ? Math.min(rawLimit, 500) : 18;
  const update = (key, value) => { const next = new URLSearchParams(params); next.delete("limit"); value ? next.set(key, value) : next.delete(key); setParams(next, { replace: true }); };
  const current = data?.current;
  const clusters = useMemo(() => (current?.clusters || []).filter(item =>
    (mode !== "grouped" || !item.isNoise) && (mode !== "unclustered" || item.isNoise) &&
    [item.name, String(item.number), ...item.topTerms, ...item.topSkills.map(skill => skill.name)].join(" ").toLowerCase().includes(query.trim().toLowerCase()))
    .sort((a, b) => sort === "name" ? a.name.localeCompare(b.name) || (a.number - b.number) : Number(a.isNoise) - Number(b.isNoise) || b.jobCount - a.jobCount), [current, query, mode, sort]);
  const topClusters = current?.clusters.filter(item => !item.isNoise).slice(0, 10) || [];
  const topSkills = current?.skills.filter(item => !(item.types || []).every(type => type === "qualification")).slice(0, 10) || [];
  const returnTo = `/clusters${params.size ? `?${params}` : ""}`;
  return <InsightsLayout title="Explore AV skill groups" subtitle="See the most requested skills, then explore jobs with similar skill needs." {...{ loading, error, retry }}>
    {current && <>
      <InsightMetrics items={[
        { label: "Active AV jobs", value: current.jobCount, note: current.snapshotDate || "Published snapshot" },
        { label: "Skill clusters", value: current.clusterCount, note: current.unclusteredJobs ? "Plus the unclustered group" : "No unclustered jobs" },
        { label: "Unclustered AV jobs", value: current.unclusteredJobs, note: "AV-related, but no clear group" },
        { label: "Companies", value: current.companyCount, note: "With active AV-related jobs" },
      ]} />
      <div className="analysis-caption"><span className="cluster-status provisional">Suggested names</span><span>Cluster names are provisional, not standard job titles.</span></div>
      <details className="analysis-method mb-3"><summary>How these counts and names are calculated</summary>
        <p>Counts include only active AV-related jobs in the published snapshot. Each skill counts once per job. Qualifications are excluded from the popular-skills chart.
          Names use cluster keywords; supplied names keep their recorded approval status. Different groups can share a broad name, so the cluster number identifies the group within this analysis only.</p>
        <p>Unclustered jobs remain AV-related. {current.jobsWithoutSkills} active job(s) have no extracted skills. Release: <code>{current.releaseKey || "Not published"}</code>.</p>
      </details>
      {current.jobCount ? <div className="insight-chart-grid mb-4">
        <InsightChart title="Largest skill clusters" description="Top 10 groups by active AV job count." horizontal
          labels={topClusters.map(item => `#${item.number} · ${item.name}`)} series={[{ name: "Active jobs", values: topClusters.map(item => item.jobCount) }]} />
        <InsightChart title="Most requested skills" description="Tools and domain skills extracted from active AV jobs." horizontal
          labels={topSkills.map(item => item.name)} series={[{ name: "Jobs requiring skill", values: topSkills.map(item => item.jobCount) }]} />
      </div> : <div className="alert alert-info">No active AV analysis has been published yet.</div>}
      <div className="cluster-directory-header"><div><h2>Browse skill groups</h2><p>Showing {Math.min(limit, clusters.length)} of {clusters.length} groups. Open a group for details.</p></div>
        <div className="cluster-controls"><label className="input-group"><span className="input-group-text"><Search size={16} /></span>
          <input className="form-control" aria-label="Search clusters and skills" value={query} onChange={event => update("search", event.target.value)} placeholder="Search a skill or group…" /></label>
          <select className="form-select" aria-label="Cluster grouping" value={mode} onChange={event => update("group", event.target.value)}>
            <option value="all">All groups</option><option value="grouped">Clustered only</option><option value="unclustered">Unclustered only</option></select>
          <select className="form-select" aria-label="Sort clusters" value={sort} onChange={event => update("order", event.target.value)}><option value="jobs">Most jobs</option><option value="name">Name A–Z</option></select>
        </div>
      </div>
      <div className="cluster-directory">{clusters.slice(0, limit).map(item => <details className={`cluster-card ${item.isNoise ? "noise-cluster" : ""}`} key={item.number}>
        <summary><div className="cluster-summary-row"><div className="cluster-card-title"><span className="cluster-id">{item.isNoise ? "UNCLUSTERED" : `GROUP #${item.number}`}</span><h3>{item.name}</h3>
          <span className={`cluster-status ${item.nameStatus === "provisional" ? "provisional" : ""}`}>{item.nameStatus === "provisional" ? "Provisional" : item.isNoise ? "Not grouped" : item.nameStatus}</span></div>
          <div className="cluster-card-count"><strong>{item.jobCount.toLocaleString()}</strong><span>jobs · {item.share}%</span></div><ChevronDown size={17} className="cluster-chevron" /></div>
          <div className="cluster-preview-skills">{item.topSkills.filter(skill => !(skill.types || []).includes("qualification")).slice(0, 3).map(skill => <span key={skill.name}>{skill.name}</span>)}</div>
        </summary>
        <div className="cluster-expanded"><h4>Top extracted skills & qualifications</h4><div className="cluster-skill-list">{item.topSkills.map(skill =>
          <Link to={`/jobs?skill=${encodeURIComponent(skill.name)}`} key={skill.name}>{skill.name}<strong>{skill.jobCount}</strong></Link>)}</div>
          <small>Skill links show all published jobs with that skill, not only this group.</small>
          <details className="mt-3"><summary>Cluster keywords</summary><p>{item.topTerms.join(" · ") || "No keywords available"}</p></details>
          <h4 className="mt-3">Example active jobs</h4><ul className="cluster-examples">{item.examples.map(job => <li key={job.sourceKey}>
            <Link to={`/jobs/${encodeURIComponent(job.sourceKey)}`} state={{ returnTo }}>{job.title}<ArrowUpRight size={14} /></Link><small>{job.company}</small></li>)}</ul>
        </div>
      </details>)}</div>
      {clusters.length > limit && <div className="text-center mt-4"><button className="btn btn-outline-primary" onClick={() => { const next = new URLSearchParams(params); next.set("limit", String(limit + 18)); setParams(next, { replace: true }); }}>Show more groups</button></div>}
      {!clusters.length && current.jobCount > 0 && <div className="alert alert-info mt-3">No groups match. Try another skill or clear the search.</div>}
    </>}
  </InsightsLayout>;
}
