# Ethics, Security and Limitations

## Collection boundary

This MVP is restricted to publicly accessible company/ATS recruitment data. It
does not log in, bypass access controls, solve CAPTCHAs, evade blocking, collect
applicant information or access non-public systems.

Scrapy is configured to obey `robots.txt`, identify the research client, disable
cookies, limit concurrency, add delay, retry transient failures and auto-throttle.
If a source disallows collection or UWA/client/legal guidance changes, disable and
review that source; do not work around the restriction.

Public availability alone is not a complete permission decision. The team must
still follow applicable site terms, UWA policy, client decisions and Australian
law before scheduled or redistributed collection.

## Data and security controls

- Source URLs, timestamps, response checksums and immutable run IDs provide an
  audit trail.
- Pydantic rejects malformed or unexpected fields before analytical storage.
- Raw responses and intermediate validated files are Git-ignored. One selected
  processed snapshot may be committed for team use after reviewing its size,
  contents, provenance and public-repository implications.
- No credentials, API keys or user-provided input are required by current spiders.
- Source HTML is converted to plain text; it is data, never executable code.
- DuckDB is opened read-only by consumers where possible, and each run builds a
  separate database rather than mutating one shared live file.

Future dashboard code must treat descriptions as untrusted text and escape them
before rendering. Future LLM stages must defend against instructions embedded in
job text, restrict tool/data access, record model/version/prompts, and validate
structured output before accepting it.

## Limitations

- The 16 sources are an engineering sample of low-difficulty structured boards,
  not a statistically representative census of the AV industry.
- Coverage is limited to jobs visible on the selected public board/region. XPeng
  and WeRide currently cover their specified US boards only.
- ATS fields are inconsistent. Missing salary, dates, location detail or team
  values often mean “not exposed”, not “does not exist”.
- Advertised titles and skills are not yet normalised or classified.
- A job disappearing from a successfully refreshed board is marked inactive; it
  is an observation, not proof of when or why the role closed.
- External endpoints can change at any time, so a historical verification result
  is not proof of present availability.
- Job advertisements may contain personal contact information or copyrighted
  text. Retention, access and redistribution should be minimised and reviewed.

## Responsible reporting

Reports must separate collected source facts, deterministic derived values, team
interpretation and later AI-generated classification. Counts should state the
run date and coverage. Do not generalise from this source sample to all companies
or claim client approval without recorded evidence.
