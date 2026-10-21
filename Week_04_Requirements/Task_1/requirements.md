# Software Requirements Specification

## Priority scale

- **Critical:** Explicitly critical or legally/audit essential.
- **High:** Core operational, security, accessibility, or performance need.
- **Medium:** Important capability, not identified as critical.
- **Low:** Desirable, optional, or weakly evidenced.

Priority is assigned from stakeholder emphasis, legal/compliance risk, and operational impact.

## Source documents

- `conversations/conv_pines014_material_volume.eml`
- `conversations/conv_pines015_capacity_interface.eml`
- `conversations/conv_pines016_shelf_space.eml`
- `conversations/conv_pines018_item_transfer.eml`
- `conversations/conv_pines019_020_missing_intransit.eml`
- `conversations/conv_pines021_item_purging.eml`
- `conversations/conv_pines022_deletions.eml`
- `conversations/conv_pines023_patron_characteristics.eml`
- `conversations/conv_pines024_inactive_patrons.eml`
- `early_draft_srs_galecia.txt`
- `email_financial_reports.eml`
- `email_report_features.eml`
- `email_staff_login.eml`
- `evergreen_reference_2009.txt`
- `interview_cataloging_2009-05-08.txt`
- `interview_sysadmin_2009-05-10.txt`
- `meeting_minutes/meeting_2009-03-15_minutes.txt`
- `meeting_minutes/meeting_2009-07-20_minutes.txt`
- `meeting_tech_subcommittee_2009-06-30.txt`
- `survey_results_2009.txt`

## Requirements

### REQ-001 - Data Backup and Disaster Recovery

**Constraint | Critical**

**The system shall implement and document data backup, recovery, and disaster recovery procedures (regular backups, off-site storage, and tested recovery plans) to prevent data loss and ensure availability.**

Given the criticality of patron, financial, and inventory data, robust backup and recovery processes are essential. Regular backups, off-site retention, and tested recovery procedures reduce risk of data loss and minimize downtime after incidents.

**Trace:** `early_draft_srs_galecia.txt`

### REQ-002 - Dedicated Reporting Store and Non-Interference with OPAC

**Constraint | Critical**

**The system shall use a dedicated reporting database or replica and background processing for report generation to ensure reporting activities do not degrade OPAC or other production services.**

Running heavy analytical queries on the production transactional database can impair patron-facing services. A separate reporting store (or replica) combined with queued/background processing isolates reporting workloads so report generation cannot constrain OPAC responsiveness or circulation operations.

**Trace:** `evergreen_reference_2009.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-003 - Development and Training Environments with Migration Capability

**Constraint | High**

**The system shall provide separate development and training environments and support controlled migration (export/import) of configurations, report templates, and permissions to production.**

Separate environments allow safe testing and staff training without impacting production. Mechanisms to migrate templates and configurations ensure reproducible and controlled promotion of changes to production environments.

**Trace:** `evergreen_reference_2009.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-004 - Scalability, Server Environment and Relational Database Constraint

**Constraint | High**

**The system shall scale to support large-consortium workloads (e.g., hundreds of locations, tens of millions of circulations, hundreds of thousands of items processed annually), operate on Linux or Solaris servers, and use a fully relational PostgreSQL back-end with reporting designed to work with the relational model (avoid denormalization approaches that fight the relational design).**

The software must be architected for high-volume transactions and large datasets while conforming to the consortium's server environments (Linux/Solaris) and relying on PostgreSQL's relational model. Reporting and ETL/design decisions should not require denormalizing the primary data model in ways that compromise integrity or maintainability.

**Trace:** `early_draft_srs_galecia.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-005 - Transaction Archiving, Retention, Privacy and Security Controls

**Constraint | Critical**

**The system shall archive transaction data and maintain transaction history for a configurable period (detailed transactions retained for X days, configurable), retain monthly and annual aggregates indefinitely, anonymize demographic and transaction data for statistical reporting to protect patron privacy, and implement security controls (access control, encrypted storage, tamper-evident logs) to comply with applicable state laws and data-protection regulations.**

Archiving must balance reporting/audit needs with legal privacy obligations. Detailed-transaction retention must be configurable (default reasonable value), while aggregates are kept indefinitely. Statistical outputs must be anonymized. Financial and personal data should be protected by security measures (access control, encryption) and audit logging to ensure compliance and data integrity.

**Trace:** `conversations/conv_pines022_deletions.eml`, `early_draft_srs_galecia.txt`, `email_report_features.eml`, `survey_results_2009.txt`

### REQ-006 - Web Standards and Accessibility (Section 508) Compliance

**Constraint | Critical**

**The system shall produce standards-compliant, semantic HTML (including alt tags and ARIA where appropriate), support legacy browsers (Internet Explorer 6.0+ and Firefox 2.0+ at minimum), and be accessible to assistive technologies (screen readers such as JAWS/NVDA, screen-magnification like ZoomText) in compliance with Section 508 requirements.**

Web components and report outputs must validate against W3C HTML standards for broad compatibility, include accessibility features and semantic structure, and work with assistive technologies. Legacy browser support is required for some library locations, and accessibility is a legal necessity for public institutions.

**Trace:** `evergreen_reference_2009.txt`, `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-007 - Capacity Overview, Metrics Definition and Branch Drill-down

**Functional | Critical**

**The system shall provide a consolidated capacity overview across all branches with defined capacity metrics (e.g., items vs. shelf space, physical items vs. configured limit, circulation volume vs. processing capacity), interactive features (sorting, filtering by region/library type/current load), ability to drill down into individual branches for details, trend displays (growth/shrinkage), CSV export, and UI grouping/filtering strategies to remain usable at very large scales (e.g., 286 locations).**

A high-level capacity interface must present meaningful metrics, be interactive, show trends, and allow drill-down to branch detail. To remain usable with hundreds of locations, the UI must support grouping (by system/region) and filtering. Defining the metrics ensures consistency and meaningful comparisons across branches.

**Trace:** `conversations/conv_pines015_capacity_interface.eml`, `early_draft_srs_galecia.txt`

### REQ-008 - Core ILS Functionalities (Material Missing from Draft)

**Functional | Critical**

**The system shall implement core integrated library system (ILS) functionalities including catalog management (bibliographic records and linked item records), circulation (checkouts, check-ins, renewals), acquisitions (ordering/receiving/invoicing), patron management (registration, blocks, categories), holds management, and inventory/item tracking.**

The requirements set contains extensive reporting and operational constraints but omitted explicit statements of the core ILS functions. Explicitly documenting cataloging, circulation, acquisitions, patron management, holds, and item tracking is necessary for a complete, implementable ILS specification.

**Trace:** `early_draft_srs_galecia.txt`

### REQ-009 - Data Quality and Uncataloged Material Tracking

**Functional | High**

**The system shall provide data-quality reports (e.g., invalid item types, overly long call numbers, bibliographic records without linked item records), display last-edit metadata distinctly from circulation dates, and support tracking of uncataloged bulk materials as inventory until fully cataloged.**

Routine data-quality reports help catalogers and managers find anomalies and maintain integrity. The system must present edit metadata clearly and allow staff to track uncataloged inventory items (e.g., board books) through processing workflows until cataloging is complete.

**Trace:** `interview_cataloging_2009-05-08.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-010 - Deletion Audit Logging and Reporting (Tamper-evident Storage)

**Functional | Critical**

**The system shall log all deletions and denied deletion attempts in a secure, tamper-evident audit store capturing record type, record ID, timestamp, user, location, and related metadata, and provide reporting interfaces to query and aggregate deletion activity by location, time period, and user.**

Auditing deletions is required for accountability and troubleshooting. Logs must be stored persistently and securely (tamper-evident), include key metadata, and be queryable so administrators can produce summaries (e.g., patron records deleted in a quarter) and detect denied deletion attempts indicating policy violations.

**Trace:** `conversations/conv_pines022_deletions.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-011 - Financial Reporting, Item Value Reports and Audit Ledger

**Functional | Critical**

**The system shall provide financial reports including patron account balances, accrued fines/charges, waived fines, payments by method and period, reports of item values for the entire collection or subsets, and maintain a detailed, auditable financial ledger linking payments to the charges they were applied to for reconciliation and auditing.**

Accurate financial reporting and a detailed ledger are required for reconciliation and audits. The system must be able to produce period-specified financial summaries, compute item values for collections or subsets, and retain an auditable trail that links payments to charges in accordance with accounting/auditing standards.

**Trace:** `early_draft_srs_galecia.txt`, `email_financial_reports.eml`

### REQ-012 - Holds, Checkouts and Transaction Reporting Across Organizational Levels

**Functional | High**

**The system shall provide reports of holds placed, holds filled, and check-outs aggregated and filterable at multiple organizational levels (patron, home branch/library, group of libraries, system, county) and support adding additional levels as needed.**

Management requires the ability to analyze holds and circulation across hierarchical levels for planning and accountability. Reports should provide breakdowns and filtering/grouping at patron, branch, group, system, and higher levels and must be configurable to accommodate various organizational structures.

**Trace:** `early_draft_srs_galecia.txt`, `survey_results_2009.txt`

### REQ-013 - HTML Help System (Searchable, Hierarchical, Accessible)

**Functional | High**

**The system shall provide an online help system that is hierarchical, cross-linked, searchable, implemented in standards-compliant HTML, and accessible to assistive technologies.**

Users need a searchable, well-structured help system for self-service support. Delivering help as standards-compliant HTML ensures cross-browser compatibility and that content can be consumed by screen readers and other assistive technologies.

**Trace:** `interview_sysadmin_2009-05-10.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-014 - Item Transfer Utility with Audit Trail and Safety Controls

**Functional | Critical**

**The system shall provide a batch item-transfer utility to move items between branches that supports querying candidate materials (saveable queries), manual selection/refinement, preview of changes, batch update of item location/status, comprehensive transfer history/audit trail (timestamps, user, role, changes), undo/cancel and configurable auto-revert rules, role-based permission controls, alerts for transfer issues, and printable transit labels.**

Bulk transfers require a utility that identifies candidates via queries, allows manual refinement and previews before applying batch updates, and tracks history/audit information for accountability. The utility must support undo or auto-revert policies, alert on anomalies, restrict capabilities by role, and produce transit labels to aid physical movement.

**Trace:** `conversations/conv_pines018_item_transfer.eml`, `interview_cataloging_2009-05-08.txt`

### REQ-015 - Material Volume, Shelf-Space Estimation and Collection Composition Reports

**Functional | High**

**The system shall compute and present material-volume and shelf-space reports that display totals and percentages (percentage of total circulations, percentage of collection, estimated percentage of shelf space) per genre/format, support customizable categories, run per-library or system-wide, provide side-by-side comparisons, allow date-range filters, and show historical trends; where shelf space is not tracked, provide estimation methods (direct input or estimation by item dimensions or proxy counts).**

Catalogers and managers need to compare how genres and formats consume collection share, circulation, and shelf space. Because shelf space is not directly tracked, the system should allow either direct input of shelf-space allocations or estimate shelf space from item dimensions or item counts, and present comparative and trend views to inform collection planning.

**Trace:** `conversations/conv_pines014_material_volume.eml`, `conversations/conv_pines016_shelf_space.eml`, `interview_cataloging_2009-05-08.txt`

### REQ-016 - Missing, Damaged and In-Transit Reporting

**Functional | High**

**The system shall generate missing and damaged item reports per branch and an in-transit report that lists items in transit beyond a configurable threshold (X days, default ~7), merging transit-to and transit-from data and optionally including item condition notes.**

Staff must audit missing/damaged items per branch and identify items stuck in transit. The in-transit report should allow a configurable days-threshold (recommended default 7), merge transit directions into one view, and include condition notes to inform recovery or replacement decisions.

**Trace:** `conversations/conv_pines019_020_missing_intransit.eml`, `early_draft_srs_galecia.txt`, `interview_cataloging_2009-05-08.txt`

### REQ-017 - Null Inclusion, Name-based Filtering and Report Metadata Display

**Functional | Medium**

**The system shall include null/blank fields explicitly in report results, support friendly name-based filters (resolving names to internal IDs), display the criteria/parameters used to generate each report alongside results, and allow saving/reusing of queries/templates.**

Excluding nulls can skew results; the system must show nulls explicitly. Filters should accept human-friendly values (e.g., survey name) and resolve them internally. For reproducibility and transparency, reports should display the criteria used and permit saving parameterized queries/templates for reuse.

**Trace:** `conversations/conv_pines018_item_transfer.eml`, `email_report_features.eml`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-018 - Patron Demographics and Inactive-Patron Reporting

**Functional | Critical**

**The system shall support demographic reporting grouped/filtered by attributes (configurable age ranges, zip code, county, home branch, patron type, preferred language), include null/blank values explicitly, and provide an inactive-patrons report (no activity within configurable X days) runnable at configurable organizational levels, exportable (CSV/Excel), with options to include mailing addresses and to exclude specified patron categories (staff, VIPs, do-not-contact); the report must support background processing and caching for very large patron databases.**

Libraries need demographic groupings for outreach while preserving privacy and ensuring accurate counts (nulls must be included). The inactive-patron report should be configurable for inactivity threshold, levels (system/home library/county), include addresses for mailings, allow exclusions, be exportable, and be designed to run as a background job with caching for millions of patrons.

**Trace:** `conversations/conv_pines023_patron_characteristics.eml`, `conversations/conv_pines024_inactive_patrons.eml`, `early_draft_srs_galecia.txt`, `survey_results_2009.txt`

### REQ-019 - Project Milestone: Draft Complete Requirements Document

**Functional | High**

**The project shall finalize a complete draft of the requirements document by September 1, 2009.**

Stakeholders set a delivery milestone for the requirements draft to align project scheduling and resource allocation. Documenting this deadline ensures project coordination and accountability toward producing a complete requirements specification.

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### REQ-020 - Purging / Weeding Utilities and Last-Copy Protection

**Functional | High**

**The system shall provide utilities to identify purge candidates using customizable and combinable criteria (status, duration, circulation history, last-copy status), produce read-only candidate and last-copy reports, support batch status conversions and deletions with explicit confirmations, support scheduling of purges, and provide undo where feasible.**

Mass purging must be precise and safe: staff should combine criteria to select candidates, preview read-only lists (including last-copy reports to prevent deleting unique items), confirm destructive actions through explicit steps, optionally schedule purges, and have undo capabilities where possible to avoid accidental loss.

**Trace:** `conversations/conv_pines021_item_purging.eml`, `interview_cataloging_2009-05-08.txt`

### REQ-021 - Real-time and Historical Reporting with Reporting Warehouse

**Functional | High**

**The system shall support real-time reporting for current state queries and historical reporting via a reporting warehouse that preserves date-stamped snapshots and aggregates for specified date ranges.**

Some operational decisions require current data while strategic analysis requires historical snapshots and aggregates. The architecture must distinguish between live real-time queries and historical reports sourced from a reporting warehouse that stores periodic snapshots and aggregates for efficient retrieval without affecting live systems.

**Trace:** `early_draft_srs_galecia.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-022 - Report Output Formats, Export and Integration (APIs)

**Functional | High**

**The system shall support exporting report output in common formats including Excel (.xls/.xlsx), HTML, and CSV, provide option to export JSON where appropriate, and expose APIs for programmatic access and integration with external systems.**

Different stakeholders consume reports in different formats; Excel and CSV are important for spreadsheet analysis and imports, HTML for web presentation, and JSON or APIs facilitate automated integration with other systems. The system should therefore provide multiple export formats and a documented API for external access.

**Trace:** `conversations/conv_pines015_capacity_interface.eml`, `conversations/conv_pines024_inactive_patrons.eml`, `early_draft_srs_galecia.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-023 - Report Template Management, Cloning, and Permission Automation

**Functional | High**

**The system shall allow administrators to create, modify, restrict, publish, clone, and manage report templates (including shared folders), provide fine-grained role/group-based permissions for creating/cloning/running/accessing reports, and automatically synchronize user permissions when their role changes.**

Administrators must govern canonical report templates while permitting authorized staff to run or safely customize them. The system should support cloning of templates to create variants, manage template visibility via shared folders, and implement fine-grained, role-driven permissions that automatically update when a user's role changes to reduce administrative overhead and maintain governance.

**Trace:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `evergreen_reference_2009.txt`, `survey_results_2009.txt`

### REQ-024 - Reporting Interfaces

**Functional | High**

**The system shall provide three reporting interfaces: canned (pre-defined) reports, on-demand (parameterized) reports, and open-template (fully customizable) reporting; administrators shall be able to create and manage canned and template reports for staff.**

Different user roles require different reporting modalities: stable canned reports for executives, parameterized on-demand reports for managers, and fully customizable templates for analysts. The system must expose all three interfaces and permit administrators to create, modify, publish, and manage the available canned and template reports so staff can run, schedule, or build reports as appropriate.

**Trace:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-025 - Scheduling, Queueing, Prioritization and Queue Visibility

**Functional | High**

**The system shall support scheduling of reports at flexible intervals (including hourly, daily, weekly, monthly), deliver scheduled output via email or stored output, queue background report jobs, expose queue visibility (position/status/ETA), allow cancellation of scheduled or running jobs, and permit prioritized jobs to jump the queue.**

Large or complex reports must be processed in background to avoid blocking users. Scheduling must include fine-grained intervals (including hourly) and email delivery. Users and admins must be able to see queue position, status, and ETA, cancel jobs, and allow administrators to prioritize critical requests for expedited processing.

**Trace:** `email_report_features.eml`, `evergreen_reference_2009.txt`, `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-026 - Transaction Grouping and Transaction Method Counts

**Functional | High**

**The system shall support grouping transactions by hour, terminal, branch, and system, and count check-ins and check-outs by method type (book-drop, staff, self-checkout, online/OPAC renewals, etc.) with both individual and cumulative counts.**

Operational analytics require grouping metrics across time, terminals, and branches and distinguishing transaction methods to identify peaks and workflow impacts. The system must provide grouped counts and breakdowns for each method type to support staffing and process improvements.

**Trace:** `meeting_tech_subcommittee_2009-06-30.txt`, `survey_results_2009.txt`

### REQ-027 - User Authentication, Role-Based Access Control and Auditability

**Functional | Critical**

**The system shall implement role/group-based access control (roles such as Global Admin, Local Admin, Library Manager, Staff, Patron), support optional streamlined staff login methods (card-based/RFID) while requiring authenticated identity with username/password fallback, automatically apply role-based permission changes, and always record the authenticated individual for auditing.**

Access must be governed by roles and security groups to manage permissions centrally. Optional convenient login methods may be supported but must not bypass individual authentication. The system must track and log which staff member is authenticated for audit trails and automatically synchronize permissions when roles change.

**Trace:** `early_draft_srs_galecia.txt`, `email_staff_login.eml`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-028 - User-Friendly Query Builder (Boolean / Picklist / Regex)

**Functional | Critical**

**The system shall provide a user-friendly query builder that enables design of queries across all record types and supports Boolean operators, picklists for values, and regular-expression matching.**

Non-technical staff must be empowered to construct complex queries without direct SQL. The query builder should expose selectable fields, value picklists, Boolean logic composition, and optional regex support. Administrators must be able to restrict access to specific tables/fields as required.

**Trace:** `early_draft_srs_galecia.txt`, `email_report_features.eml`, `survey_results_2009.txt`

### REQ-029 - Error Reporting and Diagnostics

**Non-functional | Medium**

**The system shall provide high-level, user-friendly error messages and detailed, low-level, query-specific diagnostic information for administrators (including table/field-level details when available).**

End users need clear, non-technical error messaging, while administrators and developers require detailed diagnostics to troubleshoot failed reports and system issues. Providing both increases maintainability and reduces downtime.

**Trace:** `early_draft_srs_galecia.txt`, `meeting_tech_subcommittee_2009-06-30.txt`

### REQ-030 - Performance Benchmarks, Concurrency and Background Processing

**Non-functional | High**

**The system shall meet defined performance benchmarks (response times under load), support high concurrency without degradation, and perform heavy report processing as queued/background tasks to avoid impact on interactive operations including during peak hours.**

Large consortia require predictable performance under concurrent usage. The system must be tested against performance benchmarks, and heavy analytical/reporting tasks must be handled by background processing or queued jobs so interactive services remain responsive, even during open hours.

**Trace:** `early_draft_srs_galecia.txt`, `meeting_minutes/meeting_2009-03-15_minutes.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

## Blacklist: conflicting or nonsensical candidates

### Draft Requirements Document Completion (project action)

**Rejected candidate:** Complete draft of requirements document: by September 1, 2009

**Reason:** nonsensical - This is a project management / meeting action item (deliverable deadline), not a software/system requirement. It does not specify system behavior and therefore is out of scope for the system requirements consolidation.

**Evidence:** Complete draft of requirements document: by September 1, 2009

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Consolidated Requirements List Distribution (project action)

**Rejected candidate:** Katherine to circulate consolidated requirements list

**Reason:** nonsensical - This is an administrative task for the working group, not a system capability. It does not describe functionality or constraints of the software and is therefore discarded from the system requirements.

**Evidence:** Katherine to circulate consolidated requirements list

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Ongoing Requirements Gathering (project action)

**Rejected candidate:** All members to continue gathering detailed report requirements

**Reason:** nonsensical - This directive assigns ongoing responsibilities to team members rather than describing a feature or constraint of the system itself, so it is not a system requirement.

**Evidence:** All members to continue gathering detailed report requirements

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Technical Architecture Section Drafting (project action)

**Rejected candidate:** George and Dana to draft technical architecture section

**Reason:** nonsensical - This is a task assignment within the working group for preparing documentation and not a software requirement; therefore it is outside the scope of system requirements.

**Evidence:** George and Dana to draft technical architecture section

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Reports Working Group Testing Role (process action)

**Rejected candidate:** Become the Reports testing group, through which all new Reports development would be filtered.

**Reason:** nonsensical - This defines an organizational process for the working group rather than a system capability. It is a governance/process directive and thus not a system requirement.

**Evidence:** Become the Reports testing group, through which all new Reports development would be filtered.

**Trace:** `meeting_minutes/meeting_2009-03-15_minutes.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Determine and create templates needed for all PINES libraries (project action)

**Rejected candidate:** Determine and create templates needed for all PINES libraries.

**Reason:** nonsensical - This is an operational action to be performed by the working group (deciding which templates to create), not a statement of system functionality. The system requirement to support templates is retained; this planning action is outside the requirements set.

**Evidence:** Determine and create templates needed for all PINES libraries.

**Trace:** `meeting_minutes/meeting_2009-03-15_minutes.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Document optimal Reports functionality within a future release (process)

**Rejected candidate:** Document optimal Reports functionality within a future Evergreen release.

**Reason:** nonsensical - This is a project/roadmap activity rather than a specific system capability; it relates to planning and documentation and is not a testable system requirement.

**Evidence:** Document optimal Reports functionality within a future Evergreen release.

**Trace:** `meeting_minutes/meeting_2009-03-15_minutes.txt`, `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Include new Marvel movie info

**Rejected candidate:** P.S. Does anyone know if the new Marvel movie is any good?

**Reason:** nonsensical - This statement is a casual, unrelated question about a movie, which has no bearing on the system requirements for shelf space and usage reporting.

**Evidence:** P.S. Does anyone know if the new Marvel movie is any good?

**Trace:** `conversations/conv_pines016_shelf_space.eml`

### Revert based on other criteria

**Rejected candidate:** Revert items to original location after a set period of time and/or based on other criteria

**Reason:** conflict - The linked requirement specifies revert after a set period of time and/or based on other criteria, making this proposal redundant and covered by the existing linked requirement.

**Evidence:** 'Ability to revert items to original location after a set period of time'

**Trace:** `conversations/conv_pines018_item_transfer.eml`

### Automated scheduling of purges

**Rejected candidate:** Can the purging utility be scheduled? Like, run automatically at the end of each year?

**Reason:** nonsensical - The linked requirements do not explicitly specify that purges should be scheduled automatically. While scheduling can be a useful feature, it is not clearly articulated or required by the core set of requirements and may lead to unintended data loss if not carefully managed.

**Evidence:** Took my kids to the zoo yesterday. The penguins were very active.

**Trace:** `conversations/conv_pines021_item_purging.eml`

### Data retention period for audit purposes

**Rejected candidate:** Data needs to be retained for 7 years for audit purposes

**Reason:** nonsensical - The source explicitly mentions a 7-year retention period, which is a specific compliance requirement, not a nonsensical or conflicting system requirement, but rather an implementation detail that the system must support. Therefore, this should not be blacklisted but recognized as a valid requirement if it were explicitly in the system requirements.

**Evidence:** "Some data needs to be retained for 7 years for audit purposes."

**Trace:** `email_financial_reports.eml`

### Streamlined login is optional, not just supported

**Rejected candidate:** The streamlined method should be optional but available.

**Reason:** nonsensical - The linked requirement specifies that the system supports or can support streamlined login methods as optional, which directly supports the proposal. No conflict exists; therefore, this should not be discarded.

**Evidence:** "The system should support BOTH methods - streamlined login (e.g. card swipe) AND traditional login (individual login and password). The streamlined method should be optional but available."; "The streamlined method should be optional but available."

**Trace:** `email_staff_login.eml`

### Real-Time Reporting Support

**Rejected candidate:** Real time reporting - does not exist

**Reason:** nonsensical - While current limitations exist, real-time reporting is a standard feature to be prioritized; stating it as 'does not exist' in a proposal to discard is nonsensical.

**Evidence:** "Several fine-grained reporting requirements from the King County specification are not met by Evergreen 1.4.0.4"

**Trace:** `evergreen_reference_2009.txt`

### Open Template Reporting Interface

**Rejected candidate:** Open Template Reporting - does not exist

**Reason:** nonsensical - Open template reporting is a common feature; proposing to discard because it does not exist ignores the requirement to implement it. Thus, it's not a valid requirement to blacklist.

**Evidence:** "Several fine-grained reporting requirements from the King County specification are not met by Evergreen 1.4.0.4"

**Trace:** `evergreen_reference_2009.txt`

### Historical Reporting Warehouse

**Rejected candidate:** Historical reporting warehouse - does not exist

**Reason:** nonsensical - Creating a historical reporting warehouse is a logical extension of reporting capabilities; stating it as 'does not exist' to blacklist is not aligned with the need to develop this feature.

**Evidence:** "Several fine-grained reporting requirements from the King County specification are not met by Evergreen 1.4.0.4"

**Trace:** `evergreen_reference_2009.txt`

### Use of a single, non-replicated production database for report generation

**Rejected candidate:** 'No separate reporting database/replica (reports run on production database)."'

**Reason:** nonsensical - Running reports on the production database can negatively impact system performance and availability, conflicting with the requirement to isolate reporting workloads.

**Evidence:** 'No separate reporting database/replica (reports run on production database).'

**Trace:** `evergreen_reference_2009.txt`

### Support for unsupported or incompatible browsers such as IE 5 or early Firefox versions

**Rejected candidate:** support IE 6.0+ and Firefox 2.0+

**Reason:** conflict - Supporting older, unsupported browser versions conflicts with modern standards and accessibility requirements, as well as the need for subsequent upgrades and maintenance.

**Evidence:** "support IE 6.0+ and Firefox 2.0+"

**Trace:** `interview_sysadmin_2009-05-10.txt`

### Management Processes shall operate on a Linux or Solaris server

**Rejected candidate:** Management Processes shall operate on a Linux or Solaris server.

**Reason:** conflict - The requirement limits the server OS unnecessarily. The unblacklisted, broader requirement states that the system shall be accessible via a web browser or Windows client, which inherently allows deployment on various server OS environments provided a web interface is supported.

**Evidence:** OE-2: Management Processes shall operate on a Linux or Solaris server. [Consensus: Both Linux and Solaris are acceptable. Most PINES installations use Linux, but some larger systems use Solaris.]

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Color-coding in UI for capacity levels

**Rejected candidate:** Maybe color-coding - green for under capacity, yellow for getting full, red for at/over capacity

**Reason:** nonsensical - While useful, this requirement is a UI presentation detail rather than a core, testable requirement. It is a typical enhancement rather than a fundamental requirement derived directly from the source discussion.

**Evidence:** "Maybe color-coding - green for under capacity, yellow for getting full, red for at/over capacity"

**Trace:** `conversations/conv_pines015_capacity_interface.eml`

### Nonsensical shelf space tracking in the system

**Rejected candidate:** Shelf space isn't directly tracked in the database.

**Reason:** nonsensical - Tracking shelf space directly in most library systems' databases is uncommon; instead, shelf space is generally estimated based on item dimensions or counts.

**Evidence:** "Shelf space isn't directly tracked in the database. We'd need to estimate based on item dimensions or use item count as a proxy."

**Trace:** `conversations/conv_pines016_shelf_space.eml`

### System should support age ranges in date of birth field

**Rejected candidate:** The age ranges need to be configurable too.

**Reason:** nonsensical - Support for configurable age ranges pertains to report configuration rather than the data type itself; age ranges are derived at query time from the birth_date field, and the requirement does not specify changing data types or storage formats for age ranges. This proposal likely misunderstands the technical implication of configurable age ranges.

**Evidence:** "The age ranges need to be configurable too. Like, 0-5, 6-10, 11-15, etc."

**Trace:** `conversations/conv_pines023_patron_characteristics.eml`

### Use Web-Browser Based Management Processes Exclusively

**Rejected candidate:** Management Processes shall be accessible through a web-browser or a Windows-compatible client.

**Reason:** nonsensical - This explicitly conflicts with the requirement that management processes shall be accessible through a web-browser or a Windows-compatible client. Stating 'exclusively' would contradict the acceptable alternative of a Windows client, and the source specifies the need for both options. Therefore, this proposal is nonsensical in the context of the requirements.

**Evidence:** OE-3: Management Processes shall be accessible through a web-browser or a Windows-compatible client.

**Trace:** `meeting_minutes/meeting_2009-07-20_minutes.txt`

### Historical Data Snapshot Feature

**Rejected candidate:** Historical reporting - I want to see what the data looked like on a specific date in the past, even if the shelving location has changed

**Reason:** nonsensical - The source specifies a need to view data on past dates, which is a common requirement for reporting and audit, and aligns with the requirement for historical data archives. The proposal does not conflict with or is redundant given the linked requirements for historical reporting and data snapshots.

**Evidence:** "Historical reporting - I want to see what the data looked like on a specific date in the past, even if the shelving location has changed"

**Trace:** `survey_results_2009.txt`

## Consistency review

- The source requirements include safety measures such as read-only candidate reports, explicit confirmation steps, and audit trails, which are aligned with the linked requirement specifications. No inconsistencies are apparent among the documented requirements and the linked requirements.
- The linked requirement explicitly states that the system shall log deletions, including denied attempts, which aligns with the need to track deletions for accountability and troubleshooting. The proposed system requirement to prevent any deletion directly conflicts with this by making records immutable and untrackable. This inconsistency should be addressed by choosing to allow deletions with proper logging rather than preventing deletions altogether.
- The source mentions 'configurable levels' and 'levels as needed,' which aligns with linked requirements specifying 'System, Home Library, County' levels; there is no apparent inconsistency. The source also specifies inclusion of mailing addresses, exclusion of specific patron types, and background processing, all of which are supported by linked requirements. No conflicting or ambiguous requirements are evident.
- The excerpt describes detailed reporting, audit, and management features which align with standard requirements, but specific data privacy or security requirements beyond reporting are not specified. No contradictions detected.
- The source specifies support for a large consortium environment but does not explicitly state the need for a disaster recovery plan, which could conflict with assumptions of high availability and data integrity.
- The requirement 'Separate Reporting Store and Non-Interference with OPAC' specifies that reports should not degrade OPAC performance, which conflicts with the 'Reporting Interfaces' requirement that implies the use of reporting activities. However, since the latter does not explicitly specify real-time constraints or impact on OPAC, these are not necessarily contradictory. No explicit contradiction is detected, but system design must ensure report activities do not interfere with OPAC if both are real-time or high load.
- The proposed requirement for shelf space estimation conflicts with the source, which states that shelf space is not directly tracked and should be estimated if needed. This indicates inconsistency with the source material.
- The source mentions the need for a missing/damaged items report and an in-transit report with configurable days, merging transit-to and transit-from, and including item condition notes. The linked requirements support these specifics explicitly. No conflicts or ambiguities are detected.
- The source mentions support for Boolean operators, picklists, and regex support, which aligns with the linked requirement for a user-friendly query builder. The ability to clone reports and have permissions automatically update based on roles also aligns with the 'Report Template Management, Cloning, and Permission Automation' requirement. The queue visibility discussion and the need to see report position and status also align with the linked 'Scheduling, Queueing, Prioritization and Queue Visibility' requirement. However, the source mentions specific enhancements such as queue position, count of reports ahead, submission time, and detailed status, which are more explicit than the linked requirements but do not conflict.
- No explicit secondary conflicts or contradictions are detected within the provided requirements set. All terms such as 'report,' 'system,' 'audit,' and 'library' appear to be used consistently across the descriptions.
