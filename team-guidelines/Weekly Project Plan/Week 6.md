# Weekly Project Plan

## Purpose

This document provides a weekly overview of the team's academic requirements, project goals, individual task allocations, risks, and progress.

It will be reviewed and updated during regular team meetings. Team members should check their assigned tasks and update the checkboxes when tasks are completed.

Meeting-minutes responsibilities will rotate among team members. When it is your turn, please ensure that the minutes follow the required format and are uploaded to the Meeting Minutes folder. 

## Status Key

- [ ] Not completed
- [x] Completed

---
## Week 6 — 24 August to 30 August 2026

### 1. School Deliverables and Meetings

- Facilitator Meeting
  **Date:** 27 August 2026
    - [x] Discuss the current project progress.
    - [x] Discuss the logic for determining whether jobs are relevant to the AV field.
    - [x] Discuss data cleaning, multilingual data, skills extraction, and skills standardisation.
    - [x] Discuss possible data-storage and classification approaches.
    - [x] Review and correct the facilitator meeting minutes against the full transcript.
    - [x] Upload the final checked facilitator meeting minutes to GitHub.  
          **Owner:** Assigned minutes taker  
          **Due:** As soon as possible

- Group Meeting (Saturday)
  **Date:** 29 August 2026
    - [x] Hold the scheduled group meeting.
    - [x] Continue discussing the data-processing and classification approach.
    - [x] Discuss the website-development and data-analysis responsibilities.
    - [x] Arrange an additional face-to-face meeting.
    - [x] Complete the group meeting minutes and upload them to GitHub.  
          **Owner:** Seonjeong Jeong  
          **Due:** After the group meeting  
          **Attendees:** Thushamini, Leon, Seonjeong and Li Luo  
          **Absent:** Nyx Chen and Sunjol Singh Paul

- Group Meeting (Sunday — Face-to-Face)
  **Date:** 30 August 2026  
  **Time:** 9:00 AM - 10:10 AM
    - [x] Confirm the website-development responsibilities.
    - [x] Confirm the initial standard data columns.
    - [x] Discuss the AI-assisted API-field-mapping approach.
    - [x] Discuss multilingual job-data processing.
    - [x] Confirm the temporary identifier for the collected job data.
    - [x] Allocate the initial tasks for frontend, backend and data standardisation.
    - [x] Complete the group meeting minutes.
    - [x] Upload the group meeting minutes to GitHub.  
          **Owner:** Seonjeong Jeong  
          **Due:** After the group meeting  
          **Attendees:** Thushamini, Leon, Seonjeong and Li Luo  
          **Absent:** Nyx Chen and Sunjol Singh Paul

- Week 6 work summary.          
    - [x] Complete the Week 6 work summary.  
          **Owner:** All team members  
          **Location:** Microsoft Teams — Team Shared
    - [x] Upload the completed Week 6 work summary to the CITS5206 Channel.  
          **Owner:** Li Luo    
          **Due:** Sunday, 30 August 2026

---
### 2. Weekly Project Goals

- [x] Progress the website and data/classification work in parallel.
- [ ] Develop a clear and practical approach for classifying AV-related jobs.
- [ ] Determine how irrelevant jobs and unrelated text should be removed.
- [x] Determine how multilingual job data should be translated and processed.
- [ ] Test methods for extracting and standardising skills using Python and LLMs.
- [ ] Investigate how related skills such as Python, Flask and Django should be grouped.
- [x] Prepare classification findings and questions for the next client meeting.
- [ ] Confirm the complete website requirements with Lee.
- [x] Continue collecting dated job data for comparison and proof of concept.
- [x] Upload all important project documents and meeting minutes to GitHub.
- [x] Confirm the initial standard columns for the collected job data.
- [x] Confirm the initial website-development responsibilities.
- [x] Identify AI-assisted API-field mapping as the next data-standardisation task.

---
### 3. Internal Task Allocation
- Website Development Track
    - [x] Confirm responsibility for frontend development.  
          **Owner:** Thushamini Chathusika Hewa Pathegamage
    - [x] Confirm responsibility for backend development.  
          **Owner:** Leon Nel Nel

- Data Collection and Standardisation Track
    - [x] Confirm the initial standard data columns: `company_name`, `job_title`, `job_description`, `job_url`, `salary` and `location`.  
          **Owner:** Data Analysis Team
    - [x] Confirm that `salary` and `location` will be collected when the information is available.  
          **Owner:** Data Analysis Team
    - [x] Confirm that `skill_set` and `generic_job_title` will be extracted from job descriptions using AI.  
          **Owner:** Data Analysis Team
    - [x] Identify that equivalent API fields may have different names across companies.  
          **Owner:** Data Analysis Team
    - [ ] Develop an AI-assisted approach for mapping different API field names to the standard column names.  
          **Owner:** Seonjeong Jeong  
          **Due:** As soon as possible
    - [x] Confirm that non-English job postings will be translated into English using AI while retaining the original text where possible.  
          **Owner:** Data Analysis Team
    - [x] Confirm that `company_name + job_title` will initially be used as a temporary identifier.  
          **Owner:** Data Analysis Team
    - [ ] Review and propose a more robust primary-key strategy after examining the collected data.  
          **Owner:** Data Analysis Team  
          **Due:** Before the next team meeting
    - [x] Run the data-collection script and save the result with the collection date.  
          **Owner:** Nyx Chen
    - [ ] Compare the latest collected data with the previous dataset.  
          **Owner:** Nyx Chen
    - [ ] Allocate further data-analysis tasks after the initial column-mapping approach is established.  
          **Owner:** Data Analysis Team  
          **Due:** After the initial mapping
- Client Communication
    - [x] Email the client about the companies and available API information.  
          **Owner:** Sunjol Singh Paul
    - [x] Help arrange the next client meeting.  
          **Owner:** Sunjol Singh Paul
    - [x] Ask the client whether soft skills should be included.  
          **Owner:** Sunjol Singh Paul
    - [x] Ask whether skills should use a main skill–subskill structure.  
          **Owner:** Sunjol Singh Paul

---
### 4. Quick Check

#### Li Luo
Attend to meeting : 3/3
- Routine Weekly Responsibilities
    - [x] Complete the Week 6 work summary form.    
- Project-Related Tasks
  - Data Collection and Standardisation Track
    - [x] Work on AV-job relevance, data cleaning and classification logic.
    - [x] Participate in confirming the initial standard data columns.
    - [x] Participate in confirming the multilingual-data-processing approach.
    - [x] Participate in confirming the temporary identifier.
    - [x] Discussed and came up with the data columns needed for the database.
  - [x] Share completed tasks and findings before the next online meeting.
- Role-Specific Responsibilities: Team Lead
    - [x] Complete the Week 6 project plan and weekly task tracking.
    - [x] Upload the completed Week 6 work summary to the CITS5206 Channel.
    - [x] Hand over the team-lead role to Nyx Chen for Week 7.

---
#### Nyx Chen 
Attend to meeting : 1/3 
- Routine Weekly Responsibilities
    - [x] Complete the Week 6 work summary form.    
- Project-Related Tasks
  - Data Collection and Standardisation Track
    - [x] Run the data-collection script and save the result with the collection date.
    - [x] Compare the latest data with the previous dataset.
    - [x] Continue investigating data cleaning, translation and classification.
- Role-Specific Responsibilities: Team Lead
    - [ ] Prepare to take over as team leader from Week 7.

---
#### Seonjeong Jeong
Attend to meeting : 2/3
- Routine Weekly Responsibilities
    - [x] Complete the Week 6 work summary form.    
- Project-Related Tasks
  - Data Collection and Standardisation Track
    - [x] Participate in confirming the initial standard data columns.
    - [x] Identify the differences between equivalent API field names.
    - [x] Discussed and came up with the data columns needed for the database.

- Role-Specific Responsibilities: Meeting Facilitator and Minutes Taker
    - [x] Facilitate and progress the Saturday group meeting.
    - [x] Facilitate, progress and record the Sunday face-to-face meeting.
    - [x] Complete the Sunday face-to-face meeting minutes.
    - [x] Upload the meeting minutes to GitHub.

---
#### Sunjol Singh Paul
Attend to meeting : 1/3
- Routine Weekly Responsibilities
    - [x] Complete the Week 6 work summary form.    
- Project-Related Tasks
  - Data Collection and Standardisation Track
    - [x] Continue testing skills-extraction and standardisation methods.
  - Client Communication
    - [x] Email the client about company and API information.
    - [x] Help arrange the next client meeting.
    - [x] Prepare client questions about the classification structure and project scope.

---
#### Thushamini Chathusika Hewa Pathegamage
Attend to meeting : 3/3
- Routine Weekly Responsibilities
    - [x] Complete the Week 6 work summary form.    
- Project-Related Tasks
- [x] Discussed and came up with the data columns needed for the database.
  - Website Development Track
    - [x] Confirm responsibility for frontend development.

---
#### Leon Nel Nel
Attend to meeting : 3/3
- Routine Weekly Responsibilities
    - [x] Complete the Week 6 work summary form.    
- Project-Related Tasks
- [x] Discussed and came up with the data columns needed for the database.
  - Website Development Track
    - [x] Confirm responsibility for backend development.
    
---
### 5. Expected Weekly Outcomes

- The team is working in two clear groups: website development and data analysis/classification.
- Thushamini is responsible for frontend development.
- Leon is responsible for backend development.
- The initial standard dataset columns have been confirmed.
- The team has identified AI-assisted API-field mapping as the next data-standardisation task.
- The team has agreed on an initial approach for processing non-English job postings.
- The team has selected `company_name + job_title` as a temporary identifier.
- The primary-key strategy still needs to be reviewed.
- The classification and skills-standardisation approaches are still being developed.
- Important project documents and meeting minutes still need to be checked and uploaded.
- Week 6 contribution records still need to be completed.

---
### 6. Risks or Blockers

- Only four of the six team members attended the Saturday group meeting.
- Only the same four members attended the follow-up face-to-face meeting.
- The meeting outcomes and action items need to be communicated to the absent members.
- Job descriptions may include unrelated roles, company information or legal text.
- Different platforms may use inconsistent formats and field names.
- Equivalent API fields may have different names across companies.
- Multilingual job descriptions may require translation before classification.
- AI-generated translations, field mappings and extracted skills may be inaccurate or inconsistent.
- A fixed skills dictionary may miss new or emerging technologies.
- Similar or related skills may not be standardised consistently.
- `company_name + job_title` may not be sufficiently unique as a permanent primary key.
- Salary and location information may not be available for every job.
- The client has not yet confirmed the treatment of soft skills or the preferred classification structure.
- Delays in confirming the website requirements may affect website development.
- Progress may slow during the study break, but project work still needs to continue.

---
### 7. Week 6 Summary

During Week 6, the team continued working on the website-development and data-analysis components of the project. The facilitator meeting was completed on 27 August 2026. The scheduled group meeting was held on Saturday, 29 August 2026, and an additional face-to-face meeting was held on Sunday, 30 August 2026.

Thushamini, Leon, Seonjeong and Li Luo attended both group meetings. Nyx and Sunjol were absent from both meetings. Seonjeong facilitated and progressed both meetings and recorded the minutes for the Sunday face-to-face meeting.

The team confirmed that Thushamini would be responsible for frontend development and Leon would be responsible for backend development. The initial frontend tasks are the landing page, job-listing page and job-detail page. Leon will investigate and propose a suitable backend technology stack and database.

The team also confirmed the initial standard data columns: `company_name`, `job_title`, `job_description`, `job_url`, `salary` and `location`. The team agreed to investigate using AI to map different API field names to the standard columns and to extract `skill_set` and `generic_job_title` from job descriptions. Non-English postings will be translated into English while retaining the original text where possible.

The team will initially use `company_name + job_title` as a temporary identifier. A more robust primary-key strategy will be reviewed after the collected data has been examined. Seonjeong will begin developing the AI-assisted field-mapping approach, and further data-analysis tasks will be allocated after the initial approach is established.

Several implementation, data-collection, client-communication and documentation tasks remain incomplete and will continue into Week 7.

---
