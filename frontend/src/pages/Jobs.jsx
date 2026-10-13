import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, MapPin, Briefcase, Bookmark, SlidersHorizontal, ArrowRight, X, ChevronLeft, ChevronRight } from "lucide-react";
import Header from "../components/Header";
import Footer from "../components/Footer";
import CompanyLogo from "../components/CompanyLogo";
import SkillPicker from "../components/SkillPicker";
import { getJobs, getFacets } from "../api/jobs";
import { useJobFilters, apiFilters, FILTER_KEYS } from "../hooks/useJobFilters";
import { countryName, locationText, workArrangement, salaryText, groupedSkills } from "../utils/jobDisplay";
import { getFavorites, toggleFavorite } from "../utils/favorites";

const LABELS = { q: "Search", company: "Company", country: "Country", state_region: "Region", city: "City",
  remote_type: "Work arrangement", seniority: "Experience", skill: "Skill", posted_after: "Posted since",
  has_salary: "Salary information", salary_currency: "Currency", salary_period: "Pay period",
  salary_min: "Minimum", salary_max: "Maximum" };
const ADVANCED = ["state_region", "city", "posted_after", "has_salary", "salary_currency", "salary_period", "salary_min", "salary_max"];
const experienceName = value => ({ entry: "Entry level", mid: "Mid level", vp: "VP" }[value] || (value.charAt(0).toUpperCase() + value.slice(1)).replaceAll("_", " "));

function SelectField({ title, ariaLabel, value, options = [], placeholder, disabled, onChange, format = value => value }) {
  const displayed = [...options];
  // A bookmarked URL can contain a now-unavailable value. Keep it visible rather
  // than silently clearing a user's selection after a release update.
  if (value && !options.some(item => item.value === value)) displayed.unshift({ value, count: 0 });
  return <label className="filter-field">
    <span className="form-label">{title}</span>
    <select className="form-select" aria-label={ariaLabel} value={value} disabled={disabled}
      onChange={event => onChange(event.target.value)}>
      <option value="">{placeholder}</option>
      {displayed.map(item => <option key={item.value} value={item.value} disabled={!item.count}>
        {format(item.value)} ({item.count})
      </option>)}
    </select>
  </label>;
}

export default function Jobs() {
  const { filters: f, page, sort, params, update, clear } = useJobFilters();
  const queryKey = JSON.stringify(f);
  const [jobs, setJobs] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [facets, setFacets] = useState({});
  const [facetsFor, setFacetsFor] = useState("");
  const [facetsError, setFacetsError] = useState("");
  const [retry, setRetry] = useState(0);
  const [favorites, setFavorites] = useState(() => getFavorites());
  const [salaryMin, setSalaryMin] = useState(f.salary_min);
  const [salaryMax, setSalaryMax] = useState(f.salary_max);
  const [salaryError, setSalaryError] = useState("");
  const busyOptions = facetsFor !== queryKey;
  const advanced = params.get("advanced") === "0" ? false : params.get("advanced") === "1" || ADVANCED.some(key => f[key]);
  const salaryUnit = f.salary_currency && f.salary_period ? `${f.salary_currency}/${f.salary_period}` : "";
  const applied = FILTER_KEYS.filter(key => f[key]);
  const total = pagination?.total ?? 0;
  const totalPages = pagination?.totalPages || 0;
  const returnQuery = params.toString() ? `?${params.toString()}` : "";

  useEffect(() => { setSalaryMin(f.salary_min); setSalaryMax(f.salary_max); setSalaryError(""); },
    [f.salary_min, f.salary_max, f.salary_currency, f.salary_period]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setLoading(true); setError("");
    const timer = setTimeout(async () => {
      try {
        const result = await getJobs({ ...apiFilters(f), page, pageSize: 20, sort }, { signal: controller.signal });
        if (!cancelled) { setJobs(result.data || []); setPagination(result.pagination); }
      } catch (err) {
        if (!cancelled && err.name !== "AbortError") { setError(err.message); setJobs([]); setPagination(null); }
      } finally { if (!cancelled) setLoading(false); }
    }, f.q ? 300 : 0);
    return () => { cancelled = true; clearTimeout(timer); controller.abort(); };
  }, [queryKey, page, sort, retry]);

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    setFacetsError("");
    const timer = setTimeout(async () => {
      try {
        const result = await getFacets(apiFilters(f), { signal: controller.signal });
        if (!cancelled) { setFacets(result || {}); setFacetsFor(queryKey); }
      } catch (err) {
        if (!cancelled && err.name !== "AbortError") setFacetsError(err.message);
      }
    }, f.q ? 300 : 0);
    return () => { cancelled = true; clearTimeout(timer); controller.abort(); };
  }, [queryKey, retry]);

  function change(key, value) {
    const patch = { [key]: value };
    if (key === "country") Object.assign(patch, { state_region: "", city: "" });
    if (key === "state_region") patch.city = "";
    update(patch);
  }
  function remove(key) {
    if (key === "salary_currency" || key === "salary_period") {
      update({ salary_currency: "", salary_period: "", salary_min: "", salary_max: "" });
    } else change(key, "");
  }
  function clearAll() { clear(); setSalaryMin(""); setSalaryMax(""); setSalaryError(""); }
  function applySalary(event) {
    event.preventDefault();
    if (salaryMin !== "" && salaryMax !== "" && Number(salaryMin) > Number(salaryMax)) {
      setSalaryError("Minimum must not exceed maximum."); return;
    }
    setSalaryError(""); update({ salary_min: salaryMin, salary_max: salaryMax });
  }
  function chipValue(key) {
    if (key === "country") return countryName(f[key]);
    if (key === "has_salary") return f[key] === "true" ? "Provided" : "Not provided";
    return f[key];
  }
  const select = (key, title, ariaLabel, placeholder, options = facets[key], extra = {}) => <SelectField
    key={key} title={title} ariaLabel={ariaLabel}
    placeholder={busyOptions ? "Updating…" : !options?.length && !f[key] ? "No known values" : placeholder} value={f[key]} options={options}
    disabled={busyOptions || (!options?.length && !f[key])} onChange={value => change(key, value)} {...extra} />;

  return <div className="app-shell">
    <Header />
    <main className="jobs-page container-xl py-4 py-lg-5">
      <section className="career-heading d-flex flex-wrap align-items-end justify-content-between gap-3 mb-4">
        <div><span className="eyebrow">AUTONOMOUS VEHICLE CAREERS</span><h1>Find your next opportunity.</h1>
          <p className="mb-0">Explore real roles, skills and opportunities across the AV industry.</p></div>
        <span className="data-freshness">Dataset: {facets.snapshotDate || (busyOptions ? "Loading…" : "Version unavailable")}</span>
      </section>
      <p className="dataset-note">Showing AV-related jobs active in this snapshot. Check the original posting for current availability.</p>

      <section className="search-card card border-0 shadow-sm" aria-label="Job search filters">
        <div className="card-body p-3 p-lg-4">
          <div className="search-bar input-group input-group-lg mb-3">
            <span className="input-group-text"><Search size={20} /></span>
            <input className="form-control" type="search" aria-label="Search by job title, skills, or company"
              placeholder="Search job title, skill or company…" value={f.q} onChange={event => change("q", event.target.value)} />
          </div>
          <div className="filter-grid primary-filters">
            {select("company", "Company", "Filter by company", "All companies")}
            {select("country", "Country", "Filter by country", "All countries", facets.country, { format: countryName })}
            <SkillPicker value={f.skill} options={facets.skill} types={facets.skillTypes} disabled={busyOptions} onChange={value => change("skill", value)} />
            {select("remote_type", "Work arrangement", "Filter by work type", "All arrangements", facets.remote_type,
              { format: value => ({ remote: "Remote", hybrid: "Hybrid", onsite: "On-site" }[value] || value) })}
            {select("seniority", "Experience", "Filter by experience level", "All experience levels", facets.seniority, { format: experienceName })}
          </div>
          <div className="filter-actions d-flex justify-content-between align-items-center flex-wrap gap-2 mt-3">
            <button type="button" className="btn btn-filter-toggle d-inline-flex align-items-center gap-2" aria-expanded={Boolean(advanced)} aria-controls="advanced-filters"
              onClick={() => update({ advanced: advanced ? "0" : "1" }, false)}>
              <SlidersHorizontal size={16} />{advanced ? "Hide additional filters" : "More filters"}
              {ADVANCED.filter(key => f[key]).length > 0 && <span className="badge rounded-pill text-bg-primary">{ADVANCED.filter(key => f[key]).length}</span>}
            </button>
            <div className="d-flex align-items-center gap-3">
              <span className="filter-status" role="status">{busyOptions ? (facetsError ? "Options unavailable" : "Updating options…") : "Options match your current filters"}</span>
              <button type="button" className="btn btn-sm btn-link clear-filters" onClick={clearAll} disabled={!applied.length && sort === "newest"}>Clear</button>
            </div>
          </div>
          {facetsError && <div className="alert alert-warning mt-3 mb-0" role="alert">{facetsError}
            <button className="btn btn-sm btn-outline-dark ms-2" onClick={() => setRetry(value => value + 1)}>Retry</button></div>}
          <div id="advanced-filters" hidden={!advanced} className="advanced-filters mt-3 pt-3">
            <div className="filter-grid mb-3">
              {select("state_region", "State / region", "Filter by state or region", "All states / regions", facets.state_region,
                { disabled: busyOptions || !f.country || !facets.state_region?.length })}
              {select("city", "City", "Filter by city", "All cities", facets.city,
                { disabled: busyOptions || !f.country || !facets.city?.length })}
              <label className="filter-field"><span className="form-label">Posted since</span><input className="form-control" type="date" aria-label="Posted since"
                max={facets.posted_range?.maximum || undefined} value={f.posted_after} onChange={event => change("posted_after", event.target.value)} /></label>
              {select("has_salary", "Salary information", "Filter by salary information", "Any salary information", facets.has_salary,
                { format: value => value === "true" ? "Salary provided" : "Salary not provided" })}
            </div>
            <form onSubmit={applySalary} className="salary-panel">
              <div className="row g-3 align-items-end">
                <div className="col-md-4"><SelectField title="Salary unit" ariaLabel="Salary currency and period" value={salaryUnit} placeholder="All salary units" options={facets.salary_units}
                  disabled={busyOptions || !facets.salary_units?.length} format={value => value.replace("/", " / ")}
                  onChange={value => { const [currency, period] = value.split("/"); update({ salary_currency: currency, salary_period: period, salary_min: "", salary_max: "" }); }} /></div>
                <label className="filter-field col-md-3"><span className="form-label">Minimum amount</span><input className="form-control" aria-label="Minimum salary" type="number" min="0" step="0.01"
                  placeholder="No minimum" disabled={!salaryUnit} value={salaryMin} onChange={event => setSalaryMin(event.target.value)} /></label>
                <label className="filter-field col-md-3"><span className="form-label">Maximum amount</span><input className="form-control" aria-label="Maximum salary" type="number" min="0" step="0.01"
                  placeholder="No maximum" disabled={!salaryUnit} value={salaryMax} onChange={event => setSalaryMax(event.target.value)} /></label>
                <div className="col-md-2"><button className="btn btn-primary w-100" type="submit" disabled={!salaryUnit}>Apply salary range</button></div>
              </div>
              {salaryError && <p className="text-danger small mt-2 mb-0" role="alert">{salaryError}</p>}
              <p className="small text-secondary mt-2 mb-0">Pay bands overlap your range; this is not a guaranteed offer. Unknown units are excluded. No currency or annual conversion.</p>
            </form>
            <p className="small text-secondary mt-3 mb-0">Location filters use known structured locations. Jobs without a posting date are excluded when a date is selected.</p>
          </div>
          {applied.length > 0 && <div className="active-filters d-flex flex-wrap gap-2 mt-3" aria-label="Active filters">
            {applied.map(key => <button key={key} className="filter-chip" onClick={() => remove(key)} aria-label={`Remove ${LABELS[key]} filter`}>
              <span>{LABELS[key]}: {chipValue(key)}</span><X size={13} /></button>)}
          </div>}
        </div>
      </section>

      <div className="jobs-toolbar d-flex justify-content-between align-items-center flex-wrap gap-3 py-4">
        <span className="results-count" aria-live="polite">{loading ? "Loading jobs…" : `${total.toLocaleString("en")} ${total === 1 ? "job" : "jobs"} found`}</span>
        <label className="d-flex align-items-center gap-2 small text-secondary">Sort by<select className="form-select form-select-sm sort-select" aria-label="Sort jobs" value={sort}
          onChange={event => update({ sort: event.target.value })}>
          <option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="title">Job title</option><option value="company">Company</option>
        </select></label>
      </div>
      {loading && <div className="empty-state card border-0 p-5 text-center"><div className="spinner-border text-primary mx-auto mb-3" role="status"><span className="visually-hidden">Loading</span></div><p>Finding matching opportunities…</p></div>}
      {!loading && error && <div className="alert alert-danger" role="alert"><h2 className="h5">Unable to load jobs</h2><p>{error}</p><button className="btn btn-outline-danger" onClick={() => setRetry(value => value + 1)}>Retry</button></div>}
      {!loading && !error && !jobs.length && <div className="empty-state card border-0 p-5 text-center"><Search size={30} className="mx-auto mb-3 text-secondary" />
        <h2 className="h4">No matching opportunities</h2><p className="text-secondary">Try removing a filter or widening your date or salary range.</p><button className="btn btn-primary mx-auto" onClick={clearAll}>Clear all filters</button></div>}
      {!loading && !error && jobs.length > 0 && <div className="jobs-list-container">
        {jobs.map(job => {
          const key = job.sourceKey || job.id;
          const saved = favorites.some(item => String(item.sourceKey || item.id) === String(key));
          const skills = Object.entries(groupedSkills(job.skills)).filter(([group]) => group !== "Qualifications").flatMap(([, names]) => names);
          return <article className="job-result card border-0" key={key}>
            <div className="job-result-logo"><CompanyLogo company={job.company || "Unknown company"} /></div>
            <div className="job-result-content">
              <span className="job-company-name">{job.company || "Company not specified"}</span>
              <h2><Link className="job-title-link" to={`/jobs/${encodeURIComponent(key)}${returnQuery}`} state={{ returnTo: `/jobs${returnQuery}` }}>{job.title || "Job title not available"}</Link></h2>
              <div className="job-result-meta"><span><MapPin size={15} />{locationText(job)}</span>{["remote", "hybrid", "onsite"].includes(job.remoteType) && <span><Briefcase size={15} />{workArrangement(job)}</span>}
                {job.level && <span className="experience-badge">{experienceName(job.level)}</span>}</div>
              {(job.salary || job.salaryMin != null || job.salaryMax != null) && <p className="job-salary-text"><span>Salary: </span>{salaryText(job)}</p>}
              {!!skills.length && <div className="jobs-skills">{skills.slice(0, 4).map((name, i) => <span key={`${name}-${i}`}>{name}</span>)}
                {skills.length > 4 && <span className="jobs-more">+{skills.length - 4}</span>}</div>}
            </div>
            <div className="job-result-side"><button className={`bookmark-control ${saved ? "saved" : ""}`} aria-label={saved ? "Remove saved job" : "Save job"}
              onClick={() => { toggleFavorite({ ...job, id: key }); setFavorites(getFavorites()); }}><Bookmark size={20} fill={saved ? "currentColor" : "none"} /></button>
              {job.postedDate && <time>{new Date(job.postedDate).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })}</time>}</div>
          </article>;
        })}
      </div>}
      {!loading && totalPages > 1 && <nav className="results-pagination d-flex align-items-center justify-content-center gap-3 mt-4" aria-label="Job results pagination">
        <button className="btn btn-outline-primary btn-sm" aria-label="Previous page" disabled={page <= 1} onClick={() => update({ page: page - 1 }, false)}><ChevronLeft size={18} /></button>
        <span className="small">Page {page} of {totalPages}</span>
        <button className="btn btn-outline-primary btn-sm" aria-label="Next page" disabled={page >= totalPages} onClick={() => update({ page: page + 1 }, false)}><ChevronRight size={18} /></button>
      </nav>}
    </main>
    <Footer />
  </div>;
}
