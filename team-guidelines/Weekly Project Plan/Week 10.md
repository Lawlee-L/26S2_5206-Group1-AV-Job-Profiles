# Week 10 Weekly Project Plan

**Week:** 10  
**Date:** 28 September – 4 October 2026  
**Team Lead / PM:** Nyx Chen  
**Status:** Working plan. Internal dates and meeting availability should be confirmed with the team.

The project is entering integration, not another planning-only week. The team should have a **video-ready Minimum Viable Product (MVP) by 4 October** as an **internal target**, leaving time to record individual videos. This is not an LMS submission date or a claim that every final feature is complete.

---

## 1. School Deliverables and Meetings

### LMS Unit Timetable: assessment milestones

| Timetable week | Date | Assessment | What it means for this plan |
| --- | --- | --- | --- |
| Week 10 | **29 September, 11:59 PM (UTC+8)** | Software Feature Report and Professional Reflection, both individual | Each member submits their own work; protect time on 28–29 September. |
| Week 11 | **6 October, 11:59 PM (UTC+8)** | Project Pitch Video, individual | Each member needs a working feature/contribution to demonstrate. |
| Week 12 | **13 October** | Final Project Report, group | The [LMS Unit Timetable](https://lms.uwa.edu.au/ultra/courses/_113158_1/document/_7055363_1?view=content&state=view) lists this date but not an exact time. Confirm the submission details and whether a completed runnable MVP is also expected then. |

**Internal integration target:** Sunday, **4 October** is our proposed video-readiness checkpoint, **not** a separate course deadline. The LMS timetable does not list a separate MVP submission on that date. The [individual video instructions](https://lms.uwa.edu.au/ultra/courses/_113158_1/assessment/_6644055_1/overview?courseId=_113158_1) require a demonstration of software features and personal contributions, plus future plans; they do not say that every final project feature must be complete by 6 October.

- Individual assessments — **Tuesday, 29 September 2026, 11:59 PM (UTC+8)**
  - [ ] Submit the Software Feature Report (Individual) through the Learning Management System (LMS).
  - [ ] Submit the Professional Reflection (Individual) through LMS.
    **Owner:** Each student for their own submissions.  
    **Note:** Check the assessment pages for submission instructions and any individually approved adjustment; these are not group submissions.

- Facilitator Meeting — **Wednesday, 30 September 2026, 11:30 AM–12:00 PM (UTC+8)**
  - [ ] Confirm that Dr Sumayyah has the invitation, online meeting link and agenda.  
    **Owner:** Li Luo (Facilitator Liaison), with agenda points coordinated by Nyx.  
    **Internal target:** 29 September.
  - [ ] Present a short, accurate progress update: collected and classified data, database import, frontend/backend integration and remaining gaps.
  - [ ] Ask for advice on the smallest demonstrable end-to-end workflow, how to report unlabelled clusters and limited historical trend data, and whether the 13 October group report also requires a completed runnable MVP.
  - [ ] Check the plan for a client demonstration and feedback before the final group report.
  - [ ] Confirm action items, owners and dates; upload the minutes to `Meeting Minutes/Facilitator Meeting/`.  
    **Minutes owner:** Leon Nel Nel (assigned by rotation; please confirm availability or arrange a swap).<br>
    **Internal target:** 1 October.

- Group Meeting — **Saturday, 3 October 2026, 12:00 PM (proposed regular slot)**
  - [ ] Run the agreed end-to-end acceptance check below live, identify anything still using mock data, and record failures with owners and next-day fixes.
  - [ ] Agree on the smallest stable project version and setup instructions each member can use for their own pitch video; do not defer this decision to the 4 October freeze.
  - [ ] Identify individual feature ownership and contribution evidence; each member chooses their own video content using the LMS instructions.
  - [ ] Review blockers and update owners/dates for the following week.
  - [ ] Upload minutes to `Meeting Minutes/Team Meeting/`.  
    **Minutes owner:** Thushamini Chathusika Hewa Pathegamage (assigned by rotation; please confirm the meeting and your availability or arrange a swap).<br>
    **Internal target:** 4 October.

- Weekly Team Accountability Document — **Sunday, 4 October 2026**
  - [ ] Put the blank Week 10 document in Microsoft Teams `Team – Shared` and remind each member to describe work actually completed.  
    **Owner:** Nyx.
  - [ ] Check that each member has filled in their own section; compile and upload the completed document to the CITS5206 Teams channel.  
    **Owner:** Nyx.  
    **Internal target:** 7:00 PM. The course document states a Sunday 8:00 PM upload deadline.

- Project Pitch Video (Individual) — **Tuesday, 6 October 2026, 11:59 PM (UTC+8)**
  - [ ] Each member checks the LMS brief and prepares, records and submits their own video: no more than five minutes, approximately two minutes on the whole project and three minutes on their own contributions, using their own face and voice and explaining any AI use.
    **Owner:** Each student.
  - [ ] Provide a stable, runnable shared project version, setup notes and known limitations by **Sunday, 4 October**. This leaves Monday, 5 October for individual recording and troubleshooting.
    **Owner:** Relevant module owners, coordinated by Nyx.

- Final Project Report (Group) — **Tuesday, 13 October 2026, listed in the LMS Unit Timetable**
  - [ ] Confirm the exact submission time and final software/report expectations when the assignment details become available.
    **Owner:** Nyx to ask the facilitator; all members to check LMS.
  - [ ] Carry the 4 October demo's defects, evidence and client feedback into the final report plan rather than treating the video-ready build as the final submission.
    **Owner:** All module owners.

---

## 2. Weekly Project Goals

- [ ] Agree on and run the minimum project path: trace a real collected posting by `source_key` through classification, database, backend response and website display.
- [ ] Bring the importer, database, backend and frontend together in one documented local setup; identify and remove demo-path mock data.
- [ ] Show only validated autonomous-vehicle (AV) relevant jobs in public views, with counts reconciled to the published data release.
- [ ] Prepare the client's three priority dashboard areas: job-count changes, skill demand and country-level locations. Mark any chart that lacks enough dated observations as a prototype rather than a measured trend.
- [ ] Review classification limitations: one AV job has no extracted skills, 596 AV jobs are in the noise/unassigned cluster, and cluster names have not been approved.
- [ ] Keep decisions, blockers, meeting minutes and progress visible in GitHub Issues or pull requests (PRs).
- [ ] Let every member test the shared project early enough to prepare their own pitch video and describe their actual contribution.

### Video-ready MVP acceptance check — internal target: 4 October

The team should record a **pass/fail result**, not just a statement that code was uploaded:

1. A reproducible local setup starts the database, backend and website from documented commands without exposing credentials.
2. At least one **real, AV-relevant** posting can be traced by the same `source_key` from the collection/classification outputs to the database, backend response and visible page; its title, company, skills and AV relevance agree across stages.
3. The website shows real AV-only job information and usable views for job counts, skill demand and country-level locations. Show changes over time only where comparable dated data support them; otherwise mark that trend as unavailable and assign a follow-up owner. Do not present unapproved cluster names or incomplete charts as validated results.
4. Each member can show their own actual software contribution or integration work, and the group records the tested commit/version, setup steps, remaining defects, owner and follow-up date.

If a check fails on 3 October, the team should name a repair owner and a narrower honest demo path that still works by 4 October. Do not mark the whole MVP as complete merely because individual modules work separately.

---

## 3. Internal Task Allocation

### Data collection and translation — Li Luo

- [ ] Provide the latest dated collection/translation output and source-health summary, including new, changed, removed and failed-source counts.  
  **Internal target:** 2 October.
- [ ] Verify whether the WeRide/Moka posting with only a title has a retrievable detail description; record the result without inventing missing skills.  
  **Internal target:** 3 October.
- [ ] Explain which dated snapshots can support job-count changes. Do not equate cumulative history with a series of verified weekly classification results.

### Classification and client liaison — Sunjol Singh Paul

- [ ] Share a concise classification quality summary, including AV relevance, extracted skills, the noise group and reproducible run instructions.  
  **Internal target:** 1 October.
- [ ] Prepare a reviewable shortlist of the largest meaningful AV clusters with top terms and example titles; separate the noise group. Ask the team/client for label suggestions rather than treating proposed names as approved.  
  **Internal target:** 2 October.
- [ ] Follow up with Adrian on project progress, cluster-label review, the intended dashboard demonstration and any outstanding requirements. Copy or summarise the outcome for the team.  
  **Internal target:** 2 October; client liaison remains with Sunjol.

### Database and integration — Nyx Chen

- [ ] Share the published local AV-only release counts and the database connection/read-view contract with Leon and Seonjeong; explain the current limitations.  
  **Internal target:** 30 September.
- [ ] Finish review of importer and AV-only dashboard PRs, include the latest quality-check fixes, and coordinate their review/integration in dependency order.  
  **Internal target:** 2 October.
- [ ] Pair with Leon and Sunjol on one repeatable integration check: a known `source_key` appears in the imported analysis, backend response and website with matching skills and relevance.  
  **Internal target:** 3 October.
- [ ] Record the setup commands, required environment variables, test result and known gaps so every member can run the project; do not include credentials.  
  **Internal target:** 4 October.

### Backend — Leon Nel Nel

- [ ] Continue [backend Issue #42](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/issues/42): connect the backend to the published AV-only database views and expose the fields required by the website.  
  **Internal target:** first working endpoint by 2 October.
- [ ] Agree with Thushamini on response shapes and error handling; test a real job detail and a skills/company aggregate.  
  **Internal target:** 3 October.
- [ ] Document how to start the backend locally and report connection or schema blockers promptly.

### Frontend — Thushamini Chathusika Hewa Pathegamage

- [ ] Meet Leon to agree on the API contract and connect a real jobs list and detail page to the backend.  
  **Internal target:** 2 October.
- [ ] Mark any remaining mock or placeholder content and remove it from the shared working path that members may show in their individual videos.  
  **Internal target:** 3 October.
- [ ] Prepare a short user journey that members can explore in their own videos, and test loading, empty states and basic layout on a narrow screen.  
  **Internal target:** 4 October.

### Dashboard and analysis — Seonjeong Jeong

- [ ] Confirm the dashboard fields and query/API needs with Leon and Nyx; use the published AV-only population for current counts and skill demand.  
  **Internal target:** 1 October.
- [ ] Prepare usable job-count, skills and country views for the demonstration. Where a genuine time series is unavailable, show the current snapshot and describe the missing historical data.  
  **Internal target:** 3 October.
- [ ] Help check whether proposed cluster labels are understandable from their top terms and example postings; keep proposals distinct from approved names.

### All members

- [ ] Complete individual assessments by the LMS deadline or the date in each person's approved adjustment.
- [ ] Run the shared project by 4 October; report incorrect data, missing provenance or broken user flows before making an individual recording.
- [ ] Prepare and submit the Project Pitch Video individually by 6 October, following the LMS brief.
- [ ] Update personal GitHub task status and the Week 10 accountability entry with work actually done.

---

## 4. Integration Checkpoints and Risks

| Checkpoint / risk | Practical response | Owner / target |
| --- | --- | --- |
| The individual Project Pitch Videos are due 6 October, shortly after Week 10 | Pass and record the video-ready MVP acceptance check by 4 October so each member has time to record | Module owners, coordinated by Nyx / 4 October |
| Frontend, backend and database still run separately | Agree on one `source_key` test case and run all three together | Nyx, Leon, Thushamini / 3 October |
| Only one classified database run is available for some analyses | Do not present synthetic skill or cluster trends; document the snapshots required for real trend charts | Seonjeong, Nyx, Li / 3 October |
| 115 AV cluster rows have no approved label, including one 596-job noise group | Request proposed names for meaningful clusters and a reviewer; keep noise visibly unassigned | Sunjol, Seonjeong / 3 October |
| Client feedback or two difficult company sources may not arrive in time | Demonstrate the reliable in-scope data; report the limits and follow up separately | Sunjol, Li / 2 October |
| Individual reports are due early in the week | Keep 28–29 September meetings and internal requests short; schedule integration work after those submissions | Nyx / 29 September |
| The LMS timetable lists the group Final Project Report on 13 October but does not state an exact time or separate MVP deadline | Confirm the assessment details with the facilitator/LMS; use the 4 October demo to expose gaps early, not as a substitute for the final group work | Nyx and all members / 30 September onward |

## 5. Week 10 Summary

To complete after the Saturday group meeting: record what actually ran end to end, which tasks remain open, whether every member has the setup needed for an individual video, and the next owners/dates. Do not mark a task complete solely because code or sample data was uploaded.

### Meeting Minutes Rotation

| Week | Meeting | Minutes Owner | Status |
| --- | --- | --- | --- |
| Week 10 | Facilitator Meeting, 30 September | Leon Nel Nel | Assigned; confirm availability |
| Week 10 | Group Meeting, 3 October (proposed) | Thushamini Chathusika Hewa Pathegamage | Assigned; confirm meeting and availability |

These assignments balance the actual `Recorded by` entries through Week 9:
Leon has taken one set of minutes and Thushamini two. The central
`Meeting Minutes/CITS5206 Meeting Minutes Rotation.md` records these assignments;
update it if either member needs a swap.
