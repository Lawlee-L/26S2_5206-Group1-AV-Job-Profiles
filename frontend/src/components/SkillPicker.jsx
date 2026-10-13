import React, { useEffect, useId, useState } from "react";

export default function SkillPicker({ value, options = [], types = {}, disabled, onChange }) {
  const id = useId();
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  useEffect(() => { setQuery(value); }, [value]);
  useEffect(() => { if (open && active >= 0) document.getElementById(`${id}-option-${active}`)?.scrollIntoView?.({ block: "nearest" }); }, [open, active, id]);
  const candidates = options.filter(item => item.value.toLowerCase().includes(query.trim().toLowerCase()));
  const groups = { "Tools & technical skills": [], "Domain knowledge": [], "Qualifications": [], "Other extracted skills": [] };
  candidates.slice(0, 60).forEach(item => {
    const kind = types[item.value] || [];
    const group = kind.includes("qualification") ? "Qualifications" : kind.includes("tool") || kind.includes("technical") ? "Tools & technical skills" :
      kind.includes("domain") ? "Domain knowledge" : "Other extracted skills";
    groups[group].push(item);
  });
  const shown = Object.values(groups).flat();
  function choose(item) { onChange(item.value); setQuery(item.value); setOpen(false); setActive(-1); }
  function keyDown(event) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault(); setOpen(true);
      if (!shown.length) { setActive(-1); return; }
      setActive(index => event.key === "ArrowDown" ? Math.min(index + 1, shown.length - 1) : Math.max(index - 1, 0));
    } else if (event.key === "Enter" && open && shown[Math.max(0, active)]) {
      event.preventDefault(); choose(shown[Math.max(0, active)]);
    } else if (event.key === "Escape") { setOpen(false); setQuery(value); setActive(-1); }
  }
  let optionIndex = -1;
  return <div className="filter-field skill-picker">
    <label className="form-label" htmlFor={id}>Skill or qualification</label>
    <div className="skill-picker-input">
      <input id={id} role="combobox" className="form-control" aria-label="Filter by skill" aria-autocomplete="list"
        aria-controls={`${id}-options`} aria-expanded={open} aria-activedescendant={open && active >= 0 ? `${id}-option-${active}` : undefined}
        placeholder={disabled ? "Updating skills…" : "Search skills…"} disabled={disabled} value={query} autoComplete="off"
        onFocus={() => { setOpen(true); setQuery(""); setActive(-1); }}
        onChange={event => { setQuery(event.target.value); setOpen(true); setActive(-1); }}
        onBlur={() => { setOpen(false); setQuery(value); setActive(-1); }} onKeyDown={keyDown} />
      {value && <button type="button" aria-label="Clear skill selection" onMouseDown={event => event.preventDefault()}
        onClick={() => { onChange(""); setQuery(""); setOpen(false); }}>×</button>}
    </div>
    {value && !disabled && !options.some(item => item.value === value) && <small className="text-secondary">This selected skill has no matches for the other filters. Clear it or widen the search.</small>}
    {open && !disabled && <div className="skill-picker-options" id={`${id}-options`} role="listbox" aria-label="Available skills">
      {Object.entries(groups).map(([name, items]) => items.length > 0 && <div role="group" aria-label={name} key={name}>
        <span className="skill-group-heading">{name}</span>{items.map(item => { const index = ++optionIndex; return <button type="button" role="option"
          id={`${id}-option-${index}`} aria-label={`${item.value} (${item.count})`} aria-selected={item.value === value} className={active === index ? "is-highlighted" : ""}
          tabIndex={-1} key={item.value} onMouseDown={event => event.preventDefault()} onClick={() => choose(item)}>
          <span>{item.value}</span><small>{item.count.toLocaleString()}</small></button>; })}</div>)}
      {!shown.length && <p>No matching skills for these filters.</p>}
      {candidates.length > 60 && <small className="skill-picker-hint">Type to find a specific skill. Showing 60 matches.</small>}
    </div>}
  </div>;
}
