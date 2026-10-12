# Week 12 Weekly Project Plan

**Week:** 12  
**Date:** 12–18 October 2026  
**Team Lead / PM:** Nyx Chen  
**Time zone:** UTC+8  
**Status:** Updated plan for report submission and project handover. Proposed internal checkpoints require team confirmation.

This week prioritises the final report, a reviewed and reproducible software delivery, container packaging and client handover. Avoid major redesigns and new untested features. A working local application is not evidence that scheduled weekly automation or client acceptance is complete.

## 1. Current Position and Confirmed Updates

- The **10 October group meeting was cancelled because four members were unavailable**, as confirmed by Nyx on 12 October. No minutes are required for that cancelled meeting; Leon's recording assignment was not completed and must not be counted as a recorded meeting.
- The final facilitator meeting took place on **7 October**. No additional facilitator meeting is assumed this week.
- Report responsibilities were claimed in Teams: **A — Leon; C — Li; D — Sunjol; E — Thushamini; F — Seonjeong**. Each member writes their own technical paragraph in B; **Nyx owns final integration, editing and submission checks**.
- Li has created the [shared final-report Google Doc](https://docs.google.com/document/d/17bNWTDR_txV9FEcsJVShvYnk15rb8TY73i6PD8T5tqE/edit?usp=sharing) and reports that her collection paragraph and Section C draft are added. Section C still needs current frontend/dashboard verification evidence. Document completion is based on her Teams update, not an independent review of the shared document.
- **Nyx approved the existing skill-cluster display names for the MVP on 12 October in his role as team lead.** Use the existing names; do not make another naming exercise a delivery blocker. This is team-lead approval, not a claim that Adrian approved each name or that the approval has already been persisted in the classification/database records.
- At planning time, **PR #73** (integrated portal), **#72** (Tableau), **#57** (classification evaluation) and **#54** (earlier frontend work) remain open. Confirm their current state before final release.

## 2. Deliverables and Checkpoints

| Item | Target (UTC+8) | Owner / required outcome |
| --- | --- | --- |
| Outstanding report content | **12 October, 6 PM — proposed catch-up target** | All writers confirm their completed sections and supply missing facts/evidence. The original 11 October internal deadline has passed. |
| Integrated report draft | **12 October evening** | Nyx assembles A–F; each writer reviews their own technical facts and links. |
| Final software verification | **13 October, before report sign-off** | Component owners identify the delivered commit/data release and record integration results and remaining limitations. |
| Final PDF sign-off | **13 October, 6 PM — proposed internal target** | All members check the final facts; Nyx checks formatting, evidence access and the five-page limit. Agree one uploader. |
| Final Group Report | **13 October, before 11:59 PM**, as recorded in Issue #67; verify LMS | The agreed uploader submits one PDF, saves the receipt and informs the group. |
| Software handover | **13 October — internal target** | Sunjol sends Adrian the reviewed repository/release, setup guides, data/version information and known limitations; records the response. |
| Week 12 accountability document | **18 October, 8 PM** course upload deadline | Everyone fills in actual contributions by the **7 PM internal target**. Nyx checks completion and upload. |
| Individual Group Member Evaluation | **Week 13 Monday, 11:59 PM**; 19 October on this timetable | Each member completes Feedback Fruits individually; verify the displayed deadline. |

Do not use a late-submission allowance as the working deadline. Report submission, software handover and client acceptance are separate outcomes. If an internal checkpoint is missed, immediately identify the blocker, owner and replacement target.

## 3. Final Report Allocation and Completion

Follow [Issue #67](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/issues/67). Fill the shared document directly; do not create competing report copies.

### B — Everyone writes their own technical paragraph

Aim for approximately **60–80 English words**, plus evidence links: **implemented functionality → integration → code and test evidence**. These are planning targets, not an assessment word limit.

| Report location | Writer | Technical content |
| --- | --- | --- |
| 2.1 Collection, standardisation and translation | Li | Sources, translation, dated datasets, source identifiers and output contract. |
| 2.2 Job analysis and clustering | Sunjol | AV relevance, skills, clustering, input/output matching and uncertainty handling. |
| 2.3 Database and importer | Nyx | Relationships, separate collection/classification imports, validation, versions, frozen publication and recovery. |
| 2.4 Backend | Leon | Read-only views, API responses, filters and integration with the portal. |
| 2.5 Frontend | Thushamini | Real-data pages, search/filter/navigation behaviour and integrated user experience. |
| 2.6 Market-analysis dashboard | Seonjeong | Tableau metrics, data population/version, visualisations and analytical limitations. |

Describe the final reviewed implementation and acknowledge shared integration work accurately. Do not claim all later fixes were written by the original module owner.

### Common writing packages — already allocated

| Package | Owner | Required content / progress |
| --- | --- | --- |
| **A — Requirements, overall solution and delivery-status table** | **Leon** | Approved requirements, a short pipeline overview, and requirement/completion/evidence mapping. A does not write B's six technical paragraphs. |
| **C — Verification and testing** | **Li** | Initial draft supplied. Update it with final component/integration tests, tested commit/release, actual results and remaining gaps. |
| **D — Deployment, documentation and handover** | **Sunjol** | Supported setup, actual container status, guide links, clean-start verification and the client handover package. |
| **E — Feedback, limitations and future work** | **Thushamini** | Student-demo feedback supplied by Nyx, client/teacher responses where available, completed fixes and realistic next steps. |
| **F — GenAI use and references** | **Seonjeong** | Each member's actual AI use, risks, human checking/adaptation and full accessible evidence URLs. |
| **Final integration, editing and submission checks** | **Nyx** | Assemble A–F, reconcile terminology/counts, remove repetition, export and inspect the PDF, coordinate sign-off and submission. |

- [ ] Each owner confirms whether their section is complete, incomplete or blocked today.
- [ ] All members provide technical evidence and their actual GenAI use to the relevant common-task owner.
- [ ] Nyx supplies PR #73 test/build/live-API evidence to Li; Seonjeong supplies Tableau verification evidence.
- [ ] Keep the **whole report within five pages**, including title, contents and references unless LMS explicitly permits an exemption. Use repository links for long logs, commands and screenshots.
- [ ] Keep the A → F order. Do not add six separate personal-contribution chapters.
- [ ] Confirm facilitator access to every evidence resource and retain the successful submission receipt.

Nyx coordinates and edits; missing sections and unsupported technical claims remain the relevant writer's responsibility.

## 4. Integration and Final Software Verification

### PR coordination

- [ ] Leon and Thushamini review **#73** together: compatible API/UI, filters, details, navigation and tests.
- [ ] Coordinate **#54 and #73** before merging because they overlap. Preserve the reviewed integrated workflow rather than replacing it with older parallel code.
- [ ] Review **#72** with Seonjeong: packaged workbook opens, extract/version is identified, chart populations and date meanings are clear.
- [ ] Review **#57** with Sunjol: document the evaluation outcome and whether it is required for the delivered classification pipeline.
- [ ] Freeze an identified reviewed commit/data release after acceptance checks; re-run affected checks after any critical fix.
- [ ] Close resolved issues with evidence. Retain real limitations and future work rather than reporting every open issue as an unresolved defect.

**Existing verification evidence:** PR #73 records **113 backend tests, 46 frontend tests, a successful production build, zero dependency-audit vulnerabilities and passing real published-MySQL API smoke tests**. These results apply to that tested implementation, not automatically to the final merged/containerised project. They are not the total test count for the entire repository.

### Final acceptance checklist

1. Another member follows the operating instructions and starts the application successfully.
2. Frontend → Flask → published MySQL reads real active AV jobs; list/detail identifiers match.
3. Company, country, region/city, skills, work arrangement and salary filters behave as documented; salary units/currencies are not guessed or silently converted.
4. Job-detail navigation preserves filters; loading, empty and error states work; original posting links are usable.
5. Tableau opens and documents its dataset/release, population and chart meanings.
6. Collection and classification inputs match explicitly by date/version and `source_key`; import validation, publication and documented recovery are verified.
7. Unknown values remain unknown. The approved existing cluster names are used consistently; unclustered jobs are not forced into an invented category.
8. Record the commit, data release, test date, tester, outcomes and remaining limitations. Deliver no passwords or secret API keys.

## 5. Containerisation and Client Handover

**Coordinator: Sunjol**, following the 7 October meeting action. Each component owner supplies their own dependencies, configuration and verification.

- [ ] Package frontend, Flask and MySQL with persistent storage, safe configuration and service readiness checks.
- [ ] Provide explicit commands for collection/translation, classification, import, QA and publication.
- [ ] Document internet/API-key/paid-service/compute requirements. Provide a setup path using verified existing data so reviewers do not need to purchase a new classification run.
- [ ] Include safe `.env.example` files; keep actual credentials outside GitHub.
- [ ] Test the package on another member's computer. Document normal shutdown/restart, backup and any command that deletes persistent data.
- [ ] Update the root README with the final repository structure, current roles, quick-start path and links to the component guides.
- [ ] Deliver an identified code version, data/classification references, Tableau workbook, operating guides, verification record and known limitations.
- [ ] Sunjol requests Adrian's feedback/acceptance and records the actual reply. A sent handover message alone is not client acceptance.

The checked Compose file currently starts **MySQL only**; it does not establish complete application or pipeline packaging. **One-command application startup and scheduled weekly automation are different features.** Claim the latter only after the entire workflow and failure handling have been tested.

If container packaging is not ready by report sign-off, provide the verified native setup and describe packaging as incomplete. Do not delay submission or claim an untested package is ready. Permanent shared hosting is not a prerequisite for the agreed local handover.

## 6. Component Responsibilities

| Member | Priority work |
| --- | --- |
| **Nyx** | Report integration and coordination; database/importer support and release/recovery guidance; PR #73 evidence; student-demo feedback; Week 12 contribution document. |
| **Li** | Section C; official collection/translation versions, source coverage and collection execution; final test evidence consolidation. |
| **Sunjol** | Section D; container/pipeline coordination; classification versions and requirements; client handover and follow-up. |
| **Leon** | Section A; backend verification and integration review; database-view permissions, configuration and container connectivity. |
| **Thushamini** | Section E; frontend verification and overlapping-PR coordination; usability/mobile checks and frontend operating guidance. |
| **Seonjeong** | Section F; Tableau verification/delivery; analytical population and date definitions; dashboard operating guidance. |

All members supply their own B paragraph, actual contributions, AI-use details and factual review. Escalate blockers with reproduction steps, owner and target; do not rely only on private messages.

## 7. Data, Naming and Feedback Decisions

- **Cluster naming:** use the existing display names approved by Nyx on 12 October. Record the delivered naming implementation/version. Team-lead approval does not imply a write to database approval fields; describe the current storage correctly. Any later formal persistence must use the normal reviewed import/publication workflow, not direct edits to frozen releases.
- **Count definitions:** the tested portal has **2,412 active AV jobs**; Tableau PR #72 reports **2,902 AV records**, including inactive records. Validate each population on the final release and explain it; do not force different populations to have the same count.
- **History:** the tested local database has one classified date, **25 September**. Additional collected dates do not establish classified historical skill trends. Document missing analysis and available date meaning rather than inventing comparisons.
- **Feedback:** identify student, teaching-staff and Adrian feedback separately. Nyx's 8 October student demonstration is evidence of user feedback, not automatic client acceptance. No fresh meeting or naming review is required merely to reuse the approved MVP names.

## 8. Meetings, Records and Weekly Closure

- **10 October:** cancelled because four members were unavailable. No missing-minutes action is assigned to Leon for this event.
- **12–13 October:** arrange a short report/integration checkpoint only if needed; confirm the time and recorder in Teams. Do not wait for all six members to be available before making progress on assigned work.
- **Facilitator:** no new meeting assumed after the 7 October final meeting.
- **Further group meeting:** hold one only if remaining handover work requires it. Leon is the proposed next recorder because his cancelled 10 October turn was not fulfilled; confirm availability or document a swap. No 17 October meeting is presented as booked.
- Update the minutes rotation only for real meetings/confirmed assignments. Record actual decisions and completed contributions, not planned work as already done.

### Week 12 Summary — fill in after delivery

- [ ] Final report submitted; uploader and receipt recorded.
- [ ] Reviewed delivery commit, database/data versions and dashboard file identified.
- [ ] Another member reproduced the setup; failures and limitations recorded.
- [ ] Client received the package; feedback/acceptance status recorded separately.
- [ ] Container and scheduled-automation status stated accurately.
- [ ] Week 12 accountability document completed.
- [ ] Each member reminded of the individual Group Member Evaluation deadline.

### Planning Sources

- [Week 11 plan](Week%2011.md).
- [Final-report allocation — Issue #67](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/issues/67), supplemented by the Teams claims shared by Nyx on 12 October.
- [Shared report](https://docs.google.com/document/d/17bNWTDR_txV9FEcsJVShvYnk15rb8TY73i6PD8T5tqE/edit?usp=sharing).
- [7 October facilitator minutes](../../Meeting%20Minutes/Facilitator%20Meeting/07-10-2026.md).
- [Meeting minutes rotation](../../Meeting%20Minutes/CITS5206%20Meeting%20Minutes%20Rotation.md).
- [PR #73](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/pull/73), [#72](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/pull/72), [#57](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/pull/57), [#54](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/pull/54).
- [Database team operating guide](../../database/TEAM_GUIDE.md).
- Nyx's 12 October confirmation: existing cluster display names approved for MVP; 10 October group meeting cancelled because four members were unavailable.
