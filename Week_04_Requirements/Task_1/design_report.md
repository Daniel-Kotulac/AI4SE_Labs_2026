# Agentic Network Design Report

## 1. Purpose and scope

The network converts a directory of stakeholder documents into one structured
software requirements specification (SRS). Its design addresses the assignment's
OS1-OS9 output requirements: one document, unique IDs, duplicate control,
traceability, explanatory text, priorities, consistency, completeness, and a
blacklist for proposals rejected as conflicting or nonsensical.

The workflow is implemented in `requirements_agent.py` with LangGraph. It uses
three LLM roles and deterministic Python steps. The division of work keeps
source handling, trace assignment, validation, and final formatting
reproducible, while using language models for interpretation and review.

## 2. Network architecture

The graph has six nodes:

| Node | Type | Responsibility and design choice |
|---|---|---|
| **Ingest** | Deterministic | Recursively loads supported text and email files, extracts plain-text email content, and splits long documents into manageable chunks. Each chunk retains its relative source path. Deterministic ingestion avoids asking a model to discover files or establish provenance. |
| **Extract** | LLM 1, parallel by chunk | Produces source-supported requirement candidates, including a concise name, testable statement, explanation, category, priority, rationale, and evidence. Assigning each request to one source chunk makes extraction scalable and lets the workflow bind provenance itself. |
| **Consolidate** | LLM 2 | Reviews candidates across the entire corpus, combines semantic duplicates and their traces, and separates genuine rejected proposals from ordinary duplicates. Global consolidation is used so that similar needs in different documents can be compared together. |
| **Audit** | LLM 3, parallel by chunk plus global review | Compares every source chunk with its linked requirements to find omissions, then reviews the whole set for cross-document contradictions and terminology consistency. The same auditor model handles both scopes to keep review criteria consistent. |
| **Refine** | LLM 2 | If the audit identifies omissions, merges them into the requirement set and sends the graph through one more audit. The bounded feedback edge limits repeated calls and prevents an unending repair loop. |
| **Write** | Deterministic | Merges exact and near-identical same-name statements as a final safeguard, assigns stable sequential IDs, validates source references, and renders the SRS and blacklist to one Markdown file. |

The normal path is **Ingest → Extract → Consolidate → Audit → Write**. If the
first audit identifies missing requirements, the path is **Audit → Refine →
Audit → Write**. Extraction and per-chunk auditing use a thread pool with at
most four concurrent calls. This improves throughput without creating
unbounded API concurrency.

## 3. Models used

The default model configuration is:

| Role | Default model | Use |
|---|---|---|
| Extractor | `gpt-4o-mini` | Extract structured candidates from each source chunk. |
| Consolidator | `gpt-5-mini` | Consolidate candidates across documents and merge audited omissions. |
| Auditor | `gpt-4.1-nano` | Check source coverage and review global consistency. |

These are the defaults in the script, not a claim that the models are
interchangeable or that their output has been benchmarked for this corpus. Each
role can be overridden with `REQUIREMENTS_EXTRACTOR_MODEL`,
`REQUIREMENTS_CONSOLIDATOR_MODEL`, or `REQUIREMENTS_AUDITOR_MODEL`. The script
uses the configured OpenAI-compatible API key and optional base URL; it does not
store the key in the report or source code.

## 4. Design choices and rationale

### Separate extraction, consolidation, and auditing roles

The roles are separated because they have different objectives: extraction
favors coverage of each source, consolidation favors a concise non-duplicated
set, and auditing looks for omissions and contradictions. Combining them into
one prompt would make it harder to distinguish candidate generation from
verification and to repair omissions systematically.

### Structured model output

Pydantic schemas define the expected fields and constrained values, including
requirement categories, priority levels, and blacklist reason types. Structured
output is validated at the model boundary so malformed or incomplete responses
fail visibly instead of being written as a plausible-looking specification.

### Deterministic provenance and output

The workflow assigns a source path to extracted requirements based on the
actual chunk being processed. It validates traces against the loaded documents
and binds blacklist traces using evidence rather than trusting model-invented
filenames. Deterministic rendering makes IDs, priority explanations, sections,
and formatting consistent between runs.

### Duplicate handling versus blacklist handling

The consolidator is instructed to merge semantic duplicates and combine their
evidence and source traces. Duplicates are not rejected requirements. The
renderer additionally merges exact statement matches and very close statements
with the same name, provided their negation polarity agrees. Only proposals
judged genuinely conflicting with a more authoritative resolved requirement,
or nonsensical, belong on the blacklist; unresolved stakeholder alternatives
remain requirements and are reported as consistency issues.

Blacklist entries must include the exact source wording of the proposed
requirement and a supporting source quotation. Before rendering, the workflow
checks that both strings occur in an actual input document and derives the
trace from that document rather than trusting a model-provided filename.
Unsupported rejections, duplicates, open questions, unrelated conversation,
and global-review suggestions without source excerpts are excluded from the
blacklist. Exact and near-exact duplicates of retained requirements are also
excluded. A blacklist reason must explain the conflict with a resolved
requirement or why the source-derived proposal is nonsensical.

### Bounded completeness feedback

Every input chunk receives a completeness review. Any missing candidates are
merged into the specification and trigger one additional audit. Capping the
repair round prevents runaway model calls while providing a concrete
extract-audit-repair path for missed needs.

## 5. Output contract: OS1-OS9

| Assignment spec | How the network addresses it |
|---|---|
| **OS1 — Single structured document** | The deterministic writer creates one Markdown SRS. |
| **OS2 — Unique identification** | The writer sorts the final set and assigns sequential `REQ-001` identifiers. |
| **OS3 — No semantic duplicates** | The consolidator merges semantic duplicates across the corpus; deterministic safeguards merge exact statements and very close same-name statements. |
| **OS4 — Tracing** | Every requirement and blacklist entry carries validated relative source paths. |
| **OS5 — Name and explanation** | Requirements include a short descriptive name, testable statement, and explanatory paragraph. |
| **OS6 — Priority** | Each requirement is assigned Critical, High, Medium, or Low, with the scale explained in the SRS. |
| **OS7 — Consistency** | Per-source and global reviews identify contradictions and terminology issues. Unresolved conflicts are reported instead of arbitrarily discarded. |
| **OS8 — Completeness** | Every chunk is audited for omissions; missing candidates may be incorporated in one bounded refinement round. |
| **OS9 — Blacklist** | Rejected source-derived proposals require a conflict or nonsensical classification, explanation, evidence, and trace. Duplicate candidates are merged instead. |

## 6. Duplicate check of the current generated SRS

The latest `requirements.md` initially contained 86 entries. A review found
three overlapping staff-authentication/accountability entries and a separate
inactive-patron report detail that extended the same report requirement. These
were consolidated into two requirements with combined source traces, leaving
83 entries. Exact duplicate titles and statements were also checked. The
consolidator prompt now explicitly instructs the network to merge details that
extend the same capability without merging merely related, independently
testable capabilities. The closest remaining statement pair is the all-branch
capacity overview and its branch-level drill-down; these are complementary,
separately testable behaviors, so both remain.

This check is a useful review aid, not a proof that no semantic overlap exists.
The network's semantic consolidation remains model-assisted, and the SRS should
still be reviewed against stakeholder intent.

## 7. Running and testing

Install dependencies from the task directory:

```powershell
python -m pip install -r .\Week_04_Requirements\Task_1\requirements.txt
```

Put the API key in the ignored `.env` file beside the script, or provide
`OPENAI_API_KEY` in the environment. Run from the repository root:

```powershell
python .\Week_04_Requirements\Task_1\requirements_agent.py `
  --input-dir .\Week_04_Requirements\Task_1\data\corpus `
  --output .\Week_04_Requirements\Task_1\requirements.md
```

Progress announcements are printed to the terminal as each workflow stage
starts and completes. Offline tests do not make API calls:

```powershell
python -m unittest discover `
  -s .\Week_04_Requirements\Task_1 `
  -p "test_*.py" -v
```
