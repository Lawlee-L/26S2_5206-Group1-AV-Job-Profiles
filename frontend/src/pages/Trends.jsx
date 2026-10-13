import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ChartNoAxesCombined } from "lucide-react";
import useInsights from "../hooks/useInsights";
import InsightChart from "../components/InsightChart";
import InsightsLayout, { InsightMetrics } from "../components/InsightsLayout";

export default function Trends() {
  const { data, loading, error, retry } = useInsights();
  const [chosen, setChosen] = useState(null);
  const [skillMetric, setSkillMetric] = useState("share");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const history = data?.history;
  const points = history?.points || [];
  const visible = points.filter(point => (!from || point.date >= from) && (!to || point.date <= to));
  const analysed = visible.filter(point => point.avJobs != null).length;
  const selected = chosen ?? (history?.skillSeries.slice(0, 3).map(item => item.name) || []);
  const labels = visible.map(point => point.date);
  const dates = new Set(labels);
  const toggle = name => setChosen(selected.includes(name) ? selected.filter(item => item !== name) : [...selected, name].slice(0, 5));
  return <InsightsLayout title="Skill demand over time" subtitle="Compare published AV analyses from matching dated collections." {...{ loading, error, retry }}>
    {history && <>
      <InsightMetrics items={[
        { label: "Current active AV jobs", value: data.current.jobCount, note: data.current.snapshotDate || "Published snapshot" },
        { label: "Analysed dates", value: history.classifiedVersionCount, note: "With a frozen published analysis" },
        { label: "Collected dates", value: points.length, note: `${points.length - history.classifiedVersionCount} awaiting published analysis` },
      ]} />
      <div className="analysis-caption">Snapshot comparison, not a measure of the whole AV labour market.</div>
      <details className="analysis-method mb-3"><summary>Comparison rules and limitations</summary><p>Missing classification is unknown, not zero. Company coverage, partial collection and changes to the analysis model can affect comparisons.
        Dates identify selected files, not exact crawl timestamps. Cluster numbers are local to a run; this page compares the number of populated groups, not matching cluster IDs.</p></details>
      {points.length > 1 && <div className="trend-range"><label>From<select className="form-select" aria-label="Trend start date" value={from} onChange={event => { setFrom(event.target.value); if (to && event.target.value > to) setTo(event.target.value); }}>
        <option value="">Earliest collection</option>{points.map(point => <option key={point.date} value={point.date}>{point.date}</option>)}</select></label>
        <label>To<select className="form-select" aria-label="Trend end date" value={to} onChange={event => { setTo(event.target.value); if (from && event.target.value && event.target.value < from) setFrom(event.target.value); }}>
          <option value="">Latest collection</option>{points.map(point => <option key={point.date} value={point.date}>{point.date}</option>)}</select></label></div>}
      {analysed < 2 && <section className="trend-empty card border-0" role="status"><ChartNoAxesCombined size={34} /><h2>Not enough history to show changes</h2>
        <p>Only {analysed} classified snapshot(s) available in this range. At least two are needed for skill and cluster trends.</p>
        <p>Nothing is estimated or filled in. Explore the current skill distribution while more matching classifications are prepared.</p>
        <Link to="/clusters" className="btn btn-primary">Explore current skill groups</Link></section>}
      {analysed >= 2 && <>
        <section className="skill-trend-controls card border-0 my-4"><div className="d-flex flex-wrap align-items-center justify-content-between gap-3"><div><h2>Compare skill demand</h2><p>Select up to five skills. Share adjusts for snapshot size.</p></div>
          <select className="form-select" aria-label="Skill trend measure" value={skillMetric} onChange={event => setSkillMetric(event.target.value)}><option value="share">Share of active AV jobs (%)</option><option value="jobCount">Number of active AV jobs</option></select></div>
          <div className="skill-trend-choices">{history.skillSeries.map(item => <label key={item.name} className={selected.includes(item.name) ? "selected" : ""}>
            <input type="checkbox" checked={selected.includes(item.name)} disabled={!selected.includes(item.name) && selected.length >= 5} onChange={() => toggle(item.name)} />{item.name}</label>)}</div>
        </section>
        {selected.length ? <InsightChart type="line" title="Skill demand across snapshots" description={skillMetric === "share" ? "Percentage of active AV jobs requiring each skill. Jobs may require several skills." : "Distinct active AV jobs requiring each skill."} percent={skillMetric === "share"}
          labels={labels} series={history.skillSeries.filter(item => selected.includes(item.name)).map(item => ({ name: item.name, values: item.values.filter(point => dates.has(point.date)).map(point => point[skillMetric]) }))} /> : <p className="alert alert-info">Select a skill to display its history.</p>}
        <div className="my-4"><InsightChart type="line" title="Number of skill clusters" description="Non-noise groups containing active AV jobs. Clustering settings can also affect the count."
          labels={labels} series={[{ name: "Skill clusters", values: visible.map(point => point.clusterCount) }]} /></div>
        <details className="analysis-method additional-analysis"><summary>Additional metrics: unclustered AV roles</summary>
          <InsightChart type="line" title="Unclustered AV roles" description="Active AV jobs not assigned to a clear skill group." percent
            labels={labels} series={[{ name: "Unclustered share", values: visible.map(point => point.unclusteredShare) }]} /></details>
      </>}
      {visible.length >= 2 && <details className="analysis-method additional-analysis"><summary>Collection coverage: all jobs versus AV-related jobs</summary>
        <InsightChart type="line" title="Active job coverage over time" description="All active collected jobs includes non-AV roles. Gaps indicate unavailable published classification."
          labels={labels} series={[{ name: "All active collected jobs", values: visible.map(point => point.activeJobs) }, { name: "Active AV-related jobs", values: visible.map(point => point.avJobs) }]} /></details>}
      <details className="snapshot-coverage card border-0 mt-4"><summary>Data coverage & sources · {visible.length} date(s)</summary>
        <p>Collections can exist without a matching classification. Import and publish matching analyses to add trend points; raw-only dates remain pending.</p>
        <div className="table-responsive"><table className="table align-middle"><thead><tr><th scope="col">Version date</th><th scope="col">All active jobs</th><th scope="col">Companies / sources</th><th scope="col">AV analysis</th><th scope="col">Collection quality</th></tr></thead>
          <tbody>{visible.map(point => <tr key={point.date}><th scope="row">{point.date}</th><td>{point.activeJobs.toLocaleString()}</td><td>{point.companyCount} / {point.sourceCount}</td>
            <td><span className={`coverage-badge ${point.avJobs == null ? "pending" : "ready"}`}>{point.avJobs == null ? "Pending published analysis" : `${point.avJobs.toLocaleString()} active AV jobs`}</span></td>
            <td>{point.collectionStatus === "partial" ? "Partial collection" : "Collected"}<small className="d-block text-muted">{point.runKind === "verified_crawl" ? "Verified crawl" : "Cumulative export"} · {point.timeQuality === "exact_utc" ? "Exact timestamp" : "Date only"}{!point.sourceReportAvailable ? " · No source report" : ""}</small></td>
          </tr>)}</tbody></table></div>
        <details className="snapshot-provenance"><summary>Source and analysis version keys</summary>{visible.map(point => <div key={point.date}><strong>{point.date}</strong>
          <dl><dt>Collection</dt><dd><code>{point.collectionRunKey}</code></dd><dt>Analysis</dt><dd><code>{point.analysisRunKey || "Not available"}</code></dd><dt>Frozen release</dt><dd><code>{point.releaseKey || "Not available"}</code></dd></dl></div>)}</details>
      </details>
    </>}
  </InsightsLayout>;
}
