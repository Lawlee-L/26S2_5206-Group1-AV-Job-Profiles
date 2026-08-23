# Weekly Project Plan

## Purpose

This document provides a weekly overview of the team's academic requirements, project goals, individual task allocations, risks, and progress.

It will be reviewed and updated during regular team meetings. Team members should check their assigned tasks and update the checkboxes when tasks are completed.

Meeting-minutes responsibilities will rotate among team members. When it is your turn, please ensure that the minutes follow the required format and are uploaded to the Meeting Minutes folder.

## Status Key

- [ ] Not completed
- [x] Completed
- ⚠️ Important deadline or issue

# Week 6 — 24 August to 30 August 2026

## 1. School Deliverables and Meetings

### Facilitator Meeting

**Date:** Wednesday, 26 August 2026

- [ ] Prepare findings and questions for the facilitator meeting.
- [ ] Discuss the proposed methods for extracting skills from job data.
- [ ] Discuss how the collected data should be processed.
- [ ] Discuss and compare suitable database options for the project.
- [ ] Clarify the requirements for location-based and robotics-industry filtering.
- [ ] Complete the facilitator meeting minutes and upload them to GitHub.

**Owner:** Assigned minutes taker  
**Due:** After the facilitator meeting

### Group Meeting

**Date:** To be confirmed

- [ ] Review the facilitator’s feedback and agree on the next implementation steps.
- [ ] Complete the group meeting minutes and upload them to GitHub.

**Owner:** Assigned minutes taker  
**Due:** After the group meeting

### Week 6 Work Summary

- [ ] Complete the Week 6 work summary.

**Owner:** All team members  
**Location:** Microsoft Teams — Team Shared  
**Due:** Sunday, 30 August 2026

- [ ] Upload the completed Week 6 work summary to the CITS5206 Channel.

**Owner:** Li Luo  
**Due:** Sunday, 30 August 2026

## 2. Weekly Project Goals

- [ ] Finalise the review of assigned companies and their data-collection methods.
- [ ] Confirm whether each assigned company has an accessible API endpoint.
- [ ] Update the endpoint findings in **Shared → AV company list.xlsx → Sheet1**.
- [ ] Finalise the list of companies that may be difficult or impractical to support.
- [ ] Respond to the client and request clarification on the additional requirements.
- [ ] Review the two available datasets and understand their structure.
- [ ] Experiment with different methods for extracting skills from job data.
- [ ] Begin discussing how the collected data should be cleaned and processed.
- [ ] Compare possible database options, including DuckDB and MySQL.
- [ ] Prepare findings and recommendations for the facilitator meeting.
- [ ] Identify the next MVP implementation tasks based on the facilitator’s feedback.

## 3. Internal Task Allocation

### Company Endpoint Review

- [ ] Recheck the companies assigned to each team member.
- [ ] Identify the ATS used by each company.
- [ ] Confirm whether the ATS provides an accessible API endpoint.
- [ ] Add confirmed endpoints to the shared company list.
- [ ] Mark companies without an accessible endpoint as:
  - **No accessible endpoint found**
  - **HTML parsing required**
  - **Further investigation required**
- [ ] Review the final list of difficult or unsupported companies.

**Owner:** All team members  
**Location:** Shared → AV company list.xlsx → Sheet1  
**Due:** Before the client response is finalised

### Client Communication

- [ ] Compile the final list of difficult or unsupported companies.
- [ ] Respond to the client regarding the company list.
- [ ] Ask the client to clarify the location-based use case.
- [ ] Ask whether robotics-industry filtering is required.
- [ ] Clarify whether the two-week period is a strict requirement or an example.

**Owner:** Sunjol Singh Paul  
**Due:** Monday, 24 August 2026

### Dataset Review and Skills Extraction

- [ ] Select one of the two available datasets:
  - **green.csv**
  - **av_jobs_20260822T050023Z**
- [ ] Review the structure and available fields in the selected dataset.
- [ ] Develop a method or logic for extracting skills from job data.
- [ ] Test the proposed method on sample job records.
- [ ] Record the method, results, limitations, and possible improvements.
- [ ] Prepare to share the findings at the facilitator meeting.

**Owner:** All team members  
**Due:** Before the facilitator meeting on Wednesday, 26 August 2026

### Data Sharing

- [ ] Share or upload the scraper code and collected job data.
- [ ] Export the collected data to CSV if required for team access.
- [ ] Confirm that all team members can access the datasets.

**Owner:** Nyx Chen  
**Due:** Before the facilitator meeting

### Data Processing and Database Selection

- [ ] Review the current data-storage approach.
- [ ] Identify the fields required for the MVP.
- [ ] Consider how the collected data should be cleaned and standardised.
- [ ] Compare DuckDB, MySQL, and other suitable database options.
- [ ] Consider database suitability for experimentation and deployment.
- [ ] Prepare questions and recommendations for the facilitator.

**Owner:** All team members  
**Due:** Facilitator meeting on Wednesday, 26 August 2026

### MVP Implementation Planning

- [ ] Review the facilitator’s feedback.
- [ ] Confirm whether location filtering should be included in the current MVP.
- [ ] Confirm whether robotics-industry filtering is part of the project scope.
- [ ] Agree on the preferred skills-extraction approach.
- [ ] Agree on the data-processing and storage approach.
- [ ] Divide the next implementation tasks among team members.

**Owner:** All team members  
**Due:** During the next group meeting

## 4. Quick Check

### Li Luo

**Attend to meetings:** 0/2

#### Routine Weekly Responsibilities

- [ ] Attend the facilitator meeting.
- [ ] Attend the group meeting.
- [ ] Complete the Week 6 work summary form.

#### Project-Related Tasks

- [ ] Recheck assigned companies and update endpoint findings.
- [ ] Select one dataset and experiment with a skills-extraction method.
- [ ] Prepare ideas for data processing and database selection.
- [ ] Help identify the next MVP implementation tasks.

#### Role-Specific Responsibilities: Team Lead

- [ ] Complete the Week 6 project plan and maintain the weekly task tracker.
- [ ] Remind team members of their tasks and deadlines.
- [ ] Monitor the progress of the company endpoint review.
- [ ] Coordinate preparation for the facilitator meeting.
- [ ] Upload the completed Week 6 work summary to the CITS5206 Channel.

### Nyx Chen

**Attend to meetings:** 0/2

#### Routine Weekly Responsibilities

- [ ] Attend the facilitator meeting.
- [ ] Attend the group meeting.
- [ ] Complete the Week 6 work summary form.

#### Project-Related Tasks

- [ ] Recheck assigned companies and update endpoint findings.
- [ ] Share or upload the scraper code and collected job data.
- [ ] Export the collected data to CSV if required.
- [ ] Confirm that team members can access the datasets.
- [ ] Select one dataset and experiment with a skills-extraction method.
- [ ] Prepare ideas for data processing and database selection.
- [ ] Help identify the next MVP implementation tasks.

### Seonjeong Jeong

**Attend to meetings:** 0/2

#### Routine Weekly Responsibilities

- [ ] Attend the facilitator meeting.
- [ ] Attend the group meeting.
- [ ] Complete the Week 6 work summary form.

#### Project-Related Tasks

- [ ] Recheck assigned companies and update endpoint findings.
- [ ] Select one dataset and experiment with a skills-extraction method.
- [ ] Prepare ideas for data processing and database selection.
- [ ] Help identify the next MVP implementation tasks.

### Sunjol Singh Paul

**Attend to meetings:** 0/2

#### Routine Weekly Responsibilities

- [ ] Attend the facilitator meeting.
- [ ] Attend the group meeting.
- [ ] Complete the Week 6 work summary form.

#### Project-Related Tasks

- [ ] Recheck assigned companies and update endpoint findings.
- [ ] Compile the final list of difficult or unsupported companies.
- [ ] Respond to the client and request clarification on the additional requirements.
- [ ] Select one dataset and experiment with a skills-extraction method.
- [ ] Prepare ideas for data processing and database selection.
- [ ] Help identify the next MVP implementation tasks.

### Thushamini Chathusika Hewa Pathegamage

**Attend to meetings:** 0/2

#### Routine Weekly Responsibilities

- [ ] Attend the facilitator meeting.
- [ ] Attend the group meeting.
- [ ] Complete the Week 6 work summary form.

#### Project-Related Tasks

- [ ] Recheck assigned companies and update endpoint findings.
- [ ] Select one dataset and experiment with a skills-extraction method.
- [ ] Prepare ideas for data processing and database selection.
- [ ] Help identify the next MVP implementation tasks.

### Leon Nel Nel

**Attend to meetings:** 0/2

#### Routine Weekly Responsibilities

- [ ] Attend the facilitator meeting.
- [ ] Attend the group meeting.
- [ ] Complete the Week 6 work summary form.

#### Project-Related Tasks

- [ ] Recheck assigned companies and update endpoint findings.
- [ ] Select one dataset and experiment with a skills-extraction method.
- [ ] Prepare ideas for data processing and database selection.
- [ ] Help identify the next MVP implementation tasks.

## 5. Expected Weekly Outcomes

- The company endpoint review is completed and recorded in the shared spreadsheet.
- Companies without accessible endpoints are clearly identified.
- The client receives a response regarding difficult or unsupported companies.
- The client’s additional requirements are clarified.
- All team members review at least one dataset.
- Initial skills-extraction methods are tested and documented.
- The team begins forming a clear approach to data processing.
- Suitable database options are compared and discussed.
- The facilitator provides feedback on skills extraction, data processing, and database selection.
- The next MVP implementation tasks are identified and allocated.
- Week 6 contribution records and meeting minutes are completed.

## 6. Risks or Blockers

- Some company career websites may not provide accessible endpoints.
- Some ATS platforms may require complex HTML parsing or additional investigation.
- Incomplete endpoint findings may delay the response to the client.
- The client’s additional requirements may expand the MVP scope.
- Location information may be missing or inconsistent in the collected job data.
- Different datasets may use inconsistent field names or data structures.
- Skill extraction may produce inaccurate, duplicated, or overly general results.
- Team members may use different extraction methods that are difficult to compare.
- The database decision may be delayed if deployment requirements remain unclear.
- Delayed task updates may affect preparation for the facilitator meeting.

## 7. Week 6 Summary

To be completed at the end of Week 6.
