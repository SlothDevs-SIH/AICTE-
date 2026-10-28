# Official Problem Statement (as supplied by the team)

**Organization:** AICTE · **Department:** Regulation Bureau
**Title (as understood):** Integrated Institution Complaint Monitoring and Status Dashboard
**PS number:** 26264 (as shown on the Smart India Hackathon portal; supplied by the team on 2026-10-28)
**Source:** text pasted by the team on 2026-10-27 from the official statement. Wording is preserved; only line breaks and list formatting were added so that requirement IDs can point to exact items.

> Requirement IDs used in the plans (`OBJ-n`, `KFn.m`, `INN`, `OUT-n`, `TU-n`) are defined by the numbering below. Do not renumber without updating `MASTER_PLAN.md` §1.3.

---

## Problem Statement

The All India Council for Technical Education (AICTE) receives various complaints and grievances related to technical education institutions from students, faculty members, stakeholders, and other concerned parties. These complaints are handled by different Bureaus/Cells, including the Regulation Bureau (RB) and the Public Grievance Redressal Cell (PGRC).

At present, cases relating to the same institution may be received and processed by different Bureaus/Cells. Due to the absence of a centralized, real-time mechanism for monitoring the status of such cases, there is a possibility of overlapping actions, duplication of efforts, delays in disposal, and difficulty in identifying which Bureau/Cell is currently dealing with a particular institution/case.

There is therefore a need to develop an Integrated Institution Complaint Monitoring and Status Dashboard that provides a consolidated view of all institution-related complaint cases across AICTE Bureaus/Cells.

## Objective

The proposed solution should provide a single-window dashboard through which authorized AICTE officials can:

- **OBJ-1** View all institution-related complaint/grievance cases in one place.
- **OBJ-2** Identify the Bureau/Cell currently handling each case.
- **OBJ-3** Track the complete status and movement of a complaint/case.
- **OBJ-4** Identify cases where RB and PGRC actions overlap or where multiple Bureaus/Cells are dealing with the same institution.
- **OBJ-5** Avoid duplication of action and ensure proper coordination between concerned Bureaus/Cells.
- **OBJ-6** Monitor pending, disposed, under-process, transferred, and escalated cases.
- **OBJ-7** Generate institution-wise, region-wise, Bureau/Cell-wise and status-wise reports.
- **OBJ-8** Provide alerts for pending cases and cases approaching prescribed timelines.

## Key Features Expected

### 1. Centralized Institution Profile
- **KF1.1** Unique Institution ID/AICTE Permanent ID.
- **KF1.2** Institution name, address, region and other relevant details.
- **KF1.3** Consolidated history of complaints/cases related to the institution.

### 2. Complaint/Case Tracking
- **KF2.1** Unique Complaint/Case ID.
- **KF2.2** Date of receipt.
- **KF2.3** Nature/category of complaint.
- **KF2.4** Current status.
- **KF2.5** Presently assigned Bureau/Cell.
- **KF2.6** Assigned officer/official.
- **KF2.7** Last action taken.
- **KF2.8** Next action required.
- **KF2.9** Date of last action and expected disposal date.

### 3. Cross-Bureau/Cell Overlap Detection
- **KF3.1** Automatically identify when complaints concerning the same institution are being handled by RB, PGRC or other Bureaus/Cells.
- **KF3.2** Provide an overlap alert to authorized officials.
- **KF3.3** Enable linking/mapping of related complaints and cases.

### 4. Real-Time Dashboard
The dashboard should display:
- **KF4.1** Total complaints/cases received.
- **KF4.2** Pending cases.
- **KF4.3** Cases under process.
- **KF4.4** Cases disposed.
- **KF4.5** Cases transferred.
- **KF4.6** Cases pending beyond prescribed timelines.
- **KF4.7** Institution-wise case status.
- **KF4.8** Bureau/Cell-wise workload.

### 5. Workflow and Action History
- **KF5.1** Complete chronological history of actions taken.
- **KF5.2** Officer/Bureau responsible for each action.
- **KF5.3** Date and time stamp.
- **KF5.4** Remarks and supporting documents.
- **KF5.5** Transfer/escalation history.

### 6. Search and Filters
Users should be able to search by:
- **KF6.1** Institution Name
- **KF6.2** AICTE Permanent ID
- **KF6.3** Complaint/Case ID
- **KF6.4** Bureau/Cell
- **KF6.5** Region
- **KF6.6** Complaint category
- **KF6.7** Status
- **KF6.8** Date range

### 7. Alerts and Notifications
- **KF7.1** Duplicate/overlapping case alerts.
- **KF7.2** Pending case reminders.
- **KF7.3** Escalation alerts.
- **KF7.4** Timeline/SLA alerts.

### 8. Reports and Analytics
- **KF8.1** Bureau-wise reports.
- **KF8.2** Region-wise reports.
- **KF8.3** Institution-wise complaint history.
- **KF8.4** Pending case ageing analysis.
- **KF8.5** Disposal rate.
- **KF8.6** Overlapping/duplicate cases.
- **KF8.7** Monthly/quarterly performance reports.

## Innovation Expected

**INN** The proposed system should use data matching, rule-based logic and/or AI-assisted analytics to identify complaints relating to the same institution even when the complaint descriptions or case references are different.

For example:
- Institution A → Complaint received by PGRC → Case under process
- Institution A → Complaint received by RB → Action initiated

The system should automatically identify the common institution and display: **"Potential Overlapping Cases – Coordination Required"**

This will enable the concerned Bureaus/Cells to coordinate and decide the appropriate course of action.

## Expected Outcome

The proposed dashboard will establish a single source of truth for institution-related complaints and regulatory actions, thereby:

- **OUT-1** Reducing duplication of work.
- **OUT-2** Preventing conflicting or parallel actions.
- **OUT-3** Improving coordination between RB, PGRC and other Bureaus/Cells.
- **OUT-4** Ensuring timely disposal of complaints.
- **OUT-5** Improving accountability and transparency.
- **OUT-6** Enabling management to monitor the status of institutions and complaints in real time.
- **OUT-7** Supporting data-driven decision-making by AICTE.

## Target Users

- **TU-1** AICTE Regulation Bureau (RB)
- **TU-2** Public Grievance Redressal Cell (PGRC)
- **TU-3** Other concerned AICTE Bureaus/Cells
- **TU-4** Regional Offices/Centres
- **TU-5** Authorized officers and senior management
- **TU-6** Competent Authority/AICTE administration
