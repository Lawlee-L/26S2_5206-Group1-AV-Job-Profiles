# Week 11 Weekly Project Plan

**Week:** 11

**Date:** 5–11 October 2026

**Team Lead / PM:** Nyx Chen

**Status:** Working plan. Internal targets, the Saturday meeting time and assigned minutes takers require team confirmation.

**Time zone:** UTC+8 throughout.

The priority is to get a small, real-data workflow working by **Wednesday, 7 October**, rehearse it, and demonstrate it on Thursday. Separate modules and passing unit tests are not evidence that the full product works. Keep the demo scope small; defer additional pages, a database-engine change and non-essential features until the core path is stable.

---

## 1. School Deliverables and Meetings

| Item | Date / time | Owner and required action |
| --- | --- | --- |
| Project Pitch Video — individual | **6 October, 11:59 PM** | Each member checks the LMS instructions and submits their own video. This is separate from Thursday's team presentation. |
| Final facilitator meeting | **7 October, 11:30 AM–12:00 PM**, online | Li sends the link and agenda on **6 October**; Nyx coordinates the agenda and progress summary. Sumayyah confirmed the meeting in her 4 October email. **Minutes: Sunjol Singh Paul.** |
| Client / UWA Robot Club demonstration | **8 October, 12:00–1:00 PM**, Building 106, G.58, ARTS Murdoch Lecture Theatre | Sunjol confirms attendance and presentation arrangements with Adrian; Nyx coordinates readiness and presenter handover. Around **five minutes per team**, plus any discussion directed by the organiser. |
| Group meeting | **10 October, 12:00 PM — proposed regular slot** | Review demo feedback, remaining defects and the final report. **Minutes: Leon Nel Nel.** Confirm the time in Teams. |
| Week 11 accountability document | **11 October, 8:00 PM** course upload deadline | Nyx creates/shares the new weekly document in Teams; everyone fills in actual contributions by the **7:00 PM internal target**. Nyx checks completion and uploads it. |
| Final Project Report — group | **13 October**, as listed in the LMS timetable | Nyx coordinates report allocation and checks the live assessment brief for the exact submission time, required attachments and software expectations. All members supply their own section/evidence. |

**Meeting distinction:** Wednesday is the facilitator meeting; Thursday is the client-organised public demonstration. The 3 October team minutes mention **11:00 AM** for the demo, but Adrian's calendar invitation says **12:00–1:00 PM**. Use the invitation unless the organiser sends an updated time.

**Attendance:** The 3 October minutes record that Nyx could attend; Sunjol needed to check work availability, and Leon, Seonjeong and Thushamini had conflicts. These are previous statements, not a final attendance list. Reconfirm in Teams on 5–6 October and identify a lead presenter and backup. Do not assume the whole team is available or that the event can be moved.

### Facilitator meeting preparation

- [ ] Li sends the online meeting link and the [Week 11 agenda](../../Meeting%20Minutes/Facilitator%20Meeting/07-10-2026-agenda.md) on 6 October, as requested by Sumayyah.
- [ ] Each module owner supplies a brief factual update: what runs, what fails, and the next action/owner/date. Nyx collates these before the meeting.
- [ ] Keep Wednesday's agenda focused on Thursday's demo: progress/blockers, a working integrated workflow, and presenters/rehearsal/fallback. Discuss final-report planning at Saturday's group meeting.
- [ ] Sunjol records demo-preparation decisions and actions; shares draft minutes by **8 October** in `Meeting Minutes/Facilitator Meeting/`.

### Client demonstration preparation

- [ ] Sunjol confirms the team's attendance with Adrian, checks presentation logistics and reports the reply to the group by **6 October**.
- [ ] Confirm who will present and who will operate the demo laptop. If the relevant developer cannot attend, arrange a practical handover to an attending member.
- [ ] Prepare answers to Adrian's three questions: **which companies are hiring; which roles are available; which skills/tools are required and what trends can be supported by the data**.
- [ ] Demonstrate working functionality with real data. Distinguish current findings from unimplemented features, missing labels and unsupported historical comparisons.
- [ ] Rehearse on the actual demo computer on **7 October**, after the core path passes. Target **6:00 PM**, subject to presenter availability.
- [ ] Prepare a local backup: tested startup instructions, a recording of working functionality, and clearly dated real-data charts/screenshots. Do not describe a recorded or static display as a live end-to-end system.
- [ ] An attending member captures client questions and follow-up requests; agree that person when attendance is confirmed. Thursday's feedback capture is separate from the Wednesday/Saturday minutes roster.

---

## 2. Weekly Project Goals

- [ ] Run **collection output → classification output → importer/MySQL → Flask backend → real frontend jobs list → job details** using a compatible, explicitly selected data/classification version.
- [ ] Give presenters a reproducible local setup. A shared server is not a prerequisite for this week's demonstration; final hosting remains a client discussion.
- [ ] Provide a small, trustworthy market-analysis display using real data: hiring companies, supported role/cluster groupings, and skill demand.
- [ ] Resolve or honestly disclose country-location gaps, unnamed clusters and incomplete trend coverage. Do not guess countries or turn unapproved labels into validated results.
- [ ] Record a tested commit, published data version, acceptance results and known limitations before the demo.
- [ ] Convert Thursday's feedback into assigned issues and final-report evidence, not an uncontrolled last-minute scope expansion.

### Minimum live-demo acceptance check — target: 7 October

1. The demo computer can start MySQL, the backend and frontend from documented commands; configuration contains no committed credentials.
2. The jobs page loads **real published AV-relevant jobs**, not `frontend/src/data/jobs.js` sample entries. Match a known job's database identifier and `source_key` across the dataset, database and backend response; use the backend's job identifier consistently for the detail route.
3. Opening a job shows the matching company, original title, available skills and available description/responsibilities/requirements. Missing data is labelled as unavailable, not fabricated.
4. Demonstrated search works against real data. Disable or clearly mark filters, sorting and other controls that are not connected. Show loading, empty and error states without crashing.
5. Counts and analytical displays identify the selected published version and population. Do not mix cumulative/removed jobs with active-job counts without explanation. Only compare dates with compatible underlying observations and analysis.
6. Presenters can repeat the journey without the developer's help. Record pass/fail results, the tested commit and data version, failures, owners and fallback.

**Fallback decision:** If the live path is still unstable after the Wednesday checkpoint, tell the team immediately. Sunjol should explain the limitation to Adrian and check whether a real-data dashboard plus a demonstration of completed modules is acceptable. Prepare that fallback in parallel; do not silently substitute mock data.

---

## 3. Internal Task Allocation

### Frontend — Thushamini Chathusika Hewa Pathegamage

- [ ] Use the agreed Flask responses to connect the jobs list and job-detail route; remove sample data and placeholder counts from the live-demo path. **Target: 7 October, before rehearsal.**
- [ ] Pair with Leon to resolve field mapping, backend base URL, cross-origin access, pagination and request/error handling. Test against the same published data version.
- [ ] Review open **PR #54** with its current scope in mind: its description still identifies sample data and UI-only controls. Keep code review/testing separate from the end-to-end acceptance decision.
- [ ] Give attending presenters a short practical walkthrough and startup guide. About/Terms pages and cosmetic additions are lower priority than a working list and details page.

### Backend — Leon Nel Nel

- [ ] Support frontend integration using the existing published read interfaces and frozen job-detail contract; agree exact response fields and job identifiers with Thushamini. **Target: 7 October.**
- [ ] Verify jobs, job details, search and displayed counts against the actual demo database, including browser-origin configuration and useful error responses.
- [ ] Provide backend startup/configuration instructions and help the presenter run the service locally.
- [ ] Keep aggregate/trend calculations and HTTP API behaviour in the backend. Ask Nyx for an explicit read-contract change if required; do not change importer-owned tables or invent data mappings independently.
- [ ] Record the **10 October group meeting** and share draft minutes by **11 October**.

### Database / importer and team coordination — Nyx Chen

- [ ] Help Leon, Thushamini and Seonjeong select and read the same published version; verify matching source identities, job details, skills and count definitions. **Target: 7 October.**
- [ ] Review Seonjeong's location-parser **PR #64**. After review, integrate the parser into the importer with tests and an unresolved-location report if feasible. The PR currently adds the parser/tests only; it does not wire the fields into `weekly_import.py`.
- [ ] Preserve raw location text and existing version/recovery guarantees. Do not patch published historical rows directly to obtain a chart. Unknown or ambiguous locations remain unknown; document any tested republish procedure needed to display enriched locations.
- [ ] Agree the smallest useful CSV export with Seonjeong: required datasets/columns, selected release, AV/active-job population and date meaning. Provide or document a tested export if needed for the demo; CSV is an analysis/handover option, not a replacement for the database-to-website path.
- [ ] Publish the acceptance checklist result and keep blockers, owners and internal targets current. Coordinate the Week 11 accountability document and final-report allocation.
- [ ] Provide database support only; frontend requests/rendering and backend business calculations remain with their module owners.

### Classification and client liaison — Sunjol Singh Paul

- [ ] Confirm Thursday's arrangements, attendance and the team's presentation plan with Adrian. Also follow up on final deployment/client handover expectations. **Target: 6 October.**
- [ ] Identify the classification output and collection version used for the demo, with reproducible instructions and a quality/limitations summary. If outputs change, keep `source_key` traceable and explicitly match them to the selected collection version.
- [ ] Review open **PR #57** and make its test/evaluation outcome clear before integration. Do not require a new full model run merely to demonstrate an already validated version.
- [ ] Supply usable skill/cluster summaries; distinguish proposed names from approved labels and keep noise/unassigned jobs separate. Prioritise the largest meaningful groups over naming every cluster before Thursday.
- [ ] Record the **7 October facilitator meeting** and share draft minutes by **8 October**.

### Dashboard / market analysis — Seonjeong Jeong

- [ ] Prepare a demonstrable Tableau view from the selected published dataset or an agreed export: hiring companies and skills, plus role/cluster information where supported. **Target: 7 October.**
- [ ] Coordinate location-parser feedback with Nyx. Recheck country charts only after structured fields have been populated through a tested workflow. Show unknown coverage rather than dropping it silently.
- [ ] Label the source version, filters and date meaning. Display measured historical trends only where comparable versions exist; otherwise show the current snapshot and explain the limitation.
- [ ] Export a presenter-ready workbook or dated charts and explain how to operate/read them if you cannot attend Thursday.

### Collection / translation and facilitator liaison — Li Luo

- [ ] Send the Wednesday link and agenda on **6 October** and share facilitator replies with the group.
- [ ] Identify the official collection/translation file to use, its date, collection coverage and known missing fields. Preserve the compatible previously classified version for the demo unless a newer matching analysis is verified.
- [ ] Clarify source-provided location fields where needed and help validate uncertain examples. Follow up on missing job descriptions when feasible; do not delay the demo for a source that cannot supply them.
- [ ] Support report evidence on collection, translation, source limitations and repeated-run behaviour.

### All members

- [ ] Protect time for the **6 October individual video submission**; do not treat the Thursday event as a substitute.
- [ ] Confirm attendance and minutes assignments promptly; arrange and document swaps if unavailable.
- [ ] Report blockers immediately with reproduction steps, owner and fix target. Link related issues/PRs rather than relying only on private messages.
- [ ] Supply final-report contribution notes, evidence links, testing results and limitations by the **10 October meeting**; complete an integrated report draft by **11 October**.
- [ ] After rehearsal, limit changes to reviewed fixes essential for the demo. Re-run affected checks and update the tested commit if anything changes.

---

## 4. Integration Checkpoints and Risks

| Checkpoint / risk | Response | Owner / internal target |
| --- | --- | --- |
| 5–6 October: frontend remains disconnected | Agree response fields, pick one traceable real job and pair on list/detail integration; surface blockers immediately | Thushamini + Leon; Nyx supports data |
| 6 October: presenters or attendance unclear | Reconfirm conflicts, name presenters/operator and send the client a clear confirmation or request | Sunjol + Nyx |
| 7 October: final facilitator meeting | Bring factual status and remaining actions, not only module descriptions; record advice and owners | Nyx + Sunjol; Li sends invitation |
| 7 October: end-to-end test and rehearsal | Run the acceptance check on the actual computer; freeze the tested demo version and prepare an honest fallback | All module owners + presenters |
| 8 October: public demo | Show tested real functionality and three client priorities; capture questions and avoid unsupported claims | Confirmed attending members |
| Location or clustering gaps remain | Show unknown/unassigned values and measured coverage; do not invent country codes, labels or trends | Nyx + Seonjeong + Sunjol |
| Hosting unresolved / internet fails | Demonstrate locally where practical; keep a recording and dated analytical backup; confirm client handover separately | Sunjol + module owners |
| 10–11 October: group-report readiness | Allocate sections, close critical demo defects, collect evidence and assemble a consistent draft | Nyx + all members |

## 5. Week 11 Summary

To complete after the Saturday meeting: record the actual demo outcome, client feedback, remaining blockers, tested code/data versions, report owners and final handover tasks. Do not mark integration complete because separate module tests pass.

### Meeting Minutes Rotation

| Week | Meeting | Minutes Owner | Status |
| --- | --- | --- | --- |
| Week 11 | Facilitator meeting, 7 October | Sunjol Singh Paul | Assigned; confirm availability or swap |
| Week 11 | Group meeting, 10 October, proposed 12:00 PM | Leon Nel Nel | Assigned; confirm time/availability or swap |

Assignments use the actual `Recorded by` entries in all **18** published minutes files through 3 October: Sunjol **2**, Leon **2**, Nyx **3**, Li **3**, Thushamini **3**, Seonjeong **5**. Sunjol takes Wednesday because his last recorded meeting was 12 September; Leon takes Saturday after recording the 30 September facilitator meeting. If both complete these assignments, everyone except Seonjeong will have recorded three meetings. This balances frequency without assigning Seonjeong another turn.

### Planning Sources

- [3 October team minutes](../../Meeting%20Minutes/Team%20Meeting/03-10-2026.md): integration, CSV exports, deployment discussion and previous attendance statements.
- [30 September facilitator minutes](../../Meeting%20Minutes/Facilitator%20Meeting/30-09-2026): integration priorities and final development discussion.
- [Meeting Minutes Rotation](../../Meeting%20Minutes/CITS5206%20Meeting%20Minutes%20Rotation.md).
- [Facilitator email thread](https://outlook.cloud.microsoft/mail/id/AAQkAGNlODQ4YzVhLWUyZTItNDk0MC1hNmMwLTRjZmM3ZjM2ODc4OQAQAELk5VsD4k5FrFyRg3%2B6qn4%3D): Sumayyah's 4 October confirmation and advance-link request.
- [Client demo email thread](https://outlook.cloud.microsoft/mail/id/AAQkAGNlODQ4YzVhLWUyZTItNDk0MC1hNmMwLTRjZmM3ZjM2ODc4OQAQANIk90ynStZFu6KnFZkrYZY%3D): 25 September invitation, 1 October attendance request and 3 October publicity.
- [Week 10 plan](Week%2010.md): LMS timetable/assessment links. Recheck the live final-report brief before submission; Outlook links require the relevant mailbox permissions and are not public evidence.
