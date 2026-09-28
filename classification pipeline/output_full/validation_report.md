# Known-answer spot-check (14 reference postings)

These 14 postings are a sanity check, not a training or tuning set.

## Agreement with the reference labels

- Postings located in pipeline output: **14/14**
- Seniority exact match: **12/14**
- experience_min exact match: **8/8** (where both are non-null)
- experience_max exact match: **3/3** (where both are non-null)

## Trap cases

### TRAP A — misleading title, technical body

- **Posting:** AV Ride — Senior Frontend Engineer – Engineering Productivity Systems
- **Reference `av_relevant`:** True
- **Expectation:** should land in / near a TECHNICAL cluster
- **Landed in:** cluster `66` (lean: **technical**)
- **Cluster terms:** robotaxi, l4 robotaxi, performance stability, react, web, l4, stability, web applications, typescript, interactive, usability, applications, write, mysql, remote assistance
- **Neighbours:** Senior Frontend Engineer | Front-end development engineer | Software Engineer, Operational Tools | System Architect (Robotaxi Direction) | Full-stack development engineer - L4 business
- **Verdict:** PASS

### TRAP B — technical-sounding title, non-technical body

- **Posting:** Motional — Senior Technical Program Manager
- **Reference `av_relevant`:** False
- **Expectation:** should NOT land in a technical cluster
- **Landed in:** cluster `-1` (lean: **n/a (noise)**)
- **Cluster terms:** data, management, development, business, work, processes, develop, quality, process, technical, design, projects, systems, bachelor, bachelor degree
- **Neighbours:** Talent Pool Registration | Product Strategy Manager | Senior Search & Ranking Engineer (AI Agent) | Government Relations(GR) Manager | Senior Strategy Manager
- **Verdict:** PASS

## Per-posting comparison

| # | Title | Cluster (lean) | Seniority (ref) | Exp min (ref) | Exp max (ref) |
|---|-------|----------------|-----------------|---------------|---------------|
| 0 | Accountant | 148 (corporate) | Mid (Mid) OK | 3 (3.0) | 5 (5.0) |
| 10 | Machine Learning Engineer – Motion Plann | -1 (n/a (noise)) | Senior (Mid) diff | 3 (nan) | <NA> (nan) |
| 72 | Lead ML/Perception Engineer | -1 (n/a (noise)) | Lead (Lead) OK | 5 (5.0) | <NA> (nan) |
| 24 | Senior Brand Designer | -1 (n/a (noise)) | Senior (Senior) OK | 5 (5.0) | <NA> (nan) |
| 58 | Corporate Counsel | 135 (corporate) | Senior (Other) diff | 5 (5.0) | 8 (8.0) |
| 5 | Facilities Technician | -1 (n/a (noise)) | Entry (Entry) OK | <NA> (nan) | <NA> (nan) |
| 13 | Robot Service Technician – Full Time/Con | 137 (technical) | Entry (Entry) OK | <NA> (nan) | <NA> (nan) |
| 54 | Technical Recruiter | 126 (corporate) | Junior (Junior) OK | 1 (1.0) | 3 (3.0) |
| 34 | Software Engineer, Networking & Linux Sy | 60 (technical) | Senior (Senior) OK | <NA> (nan) | <NA> (nan) |
| 27 | Senior Frontend Engineer – Engineering P | 66 (technical) | Senior (Senior) OK | <NA> (3.0) | <NA> (nan) |
| 4 | DevOps Engineer – Developer Tools | 87 (technical) | Mid (Mid) OK | 3 (3.0) | <NA> (nan) |
| 642 | 2027 Campus Recruiting General Intellige | 109 (technical) | Graduate (Graduate) OK | <NA> (nan) | <NA> (nan) |
| 330 | Senior Technical Program Manager | -1 (n/a (noise)) | Senior (Senior) OK | 5 (5.0) | <NA> (nan) |
| 28 | Senior Manager – HR Operations | 141 (corporate) | Senior Manager (Senior Manager) OK | 10 (10.0) | <NA> (nan) |
