const countryNames = new Intl.DisplayNames(["en"], { type: "region" });
export function countryName(code) {
  if (!/^[A-Z]{2}$/.test(code || "")) return code || "";
  return countryNames.of(code) || code;
}

export function compactText(value, limit = 160) {
  if (!value) return "";
  const text = String(value).split(/\r?\n/).find((line) => line.trim())?.trim() || "";
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

export function locationText(job) {
  const parts = [job.city, job.stateRegion, countryName(job.countryCode)].filter(Boolean);
  return parts.length ? [...new Set(parts)].join(", ") :
    compactText(job.locationDisplay || job.location) || "Location not specified";
}

export function workArrangement(job) {
  return { remote: "Remote", hybrid: "Hybrid", onsite: "On-site" }[job.remoteType] || "Not specified";
}

export function groupedSkills(skills = []) {
  const groups = { "Tools & technical skills": [], "Domain knowledge": [], "Qualifications": [], "Other extracted skills": [] };
  const unique = new Map();
  for (const skill of skills) {
    const name = (typeof skill === "string" ? skill : skill?.name)?.trim();
    if (!name) continue;
    const key = name.toLowerCase();
    const item = unique.get(key) || { name, types: new Set() };
    item.types.add(skill?.type || "unknown");
    unique.set(key, item);
  }
  for (const { name, types } of unique.values()) {
    const group = types.has("qualification") ? "Qualifications" : types.has("tool") || types.has("technical") ? "Tools & technical skills" :
      types.has("domain") ? "Domain knowledge" : "Other extracted skills";
    groups[group].push(name);
  }
  return groups;
}

export function salaryText(job) {
  const amounts = [job.salaryMin, job.salaryMax].filter((value) => value != null);
  if (!amounts.length) return compactText(job.salaryDisplay || job.salary) || "Salary not available";
  const range = [...new Set(amounts)].map((value) => Number(value).toLocaleString("en-AU")).join("–");
  const bound = job.salaryMin == null ? "Up to" : job.salaryMax == null ? "From" : "";
  const currency = job.salaryCurrency || job.salaryNormalization?.symbol || "Currency not stated";
  const period = job.salaryPeriod ? `per ${job.salaryPeriod}` : "(period not stated)";
  const summary = [bound, currency, range, period].filter(Boolean).join(" ");
  return job.salaryNormalization?.qualifier ? `${summary} · applies to ${job.salaryNormalization.qualifier}` : summary;
}
