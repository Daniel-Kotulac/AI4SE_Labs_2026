# Agentic Requirements Refinement Network — Design Report

## Goal

The network accepts a directory of mixed text sources and produces one Markdown
requirements specification. It does not depend on fixed corpus filenames, and
each requirement traces to one or more relative source paths and supporting
excerpts.

## Network design

The workflow is implemented with LangGraph in `requirements_agent.py`.

1. **Ingest (deterministic):** Recursively reads supported text formats
   (`.txt`, `.eml`, `.md`, `.rst`, `.csv`, `.html`, `.htm`, `.json`), normalizes
   email headers/body, and chunks long documents with source identity preserved.
2. **Extract (LLM):** Extracts atomic, evidenced requirements from every chunk,
   including constraints, assumptions, priorities, and ambiguities. Unrelated
   email chatter is explicitly excluded.
3. **Consolidate (LLM):** Merges semantic duplicates and combines their trace
   data. Independent batches are processed concurrently (up to four at a time)
   to reduce wall-clock time. The network stops after at most three passes and
   stops earlier when a pass no longer reduces the candidates. Distinct and
   unresolved conflicting requirements are retained; superseded or nonsensical
   proposals are recorded in a discard list.
4. **Audit (LLM):** Reviews every source excerpt against requirements linked to
   that source, identifies omissions and inconsistencies, and records
   discarded proposals where warranted.
5. **Refine (LLM feedback loop):** If the audit finds omissions or proposals to
   discard on its first pass, the network incorporates the missing items and
   consolidates again, then reruns the audit. The loop is bounded to one
   refinement round to prevent unbounded model calls.
6. **Render (deterministic):** Validates source references, assigns stable
   sequential requirement identifiers, sorts the output, and writes the
   structured Markdown document with the priority scale, source corpus,
   requirements, blacklist, and unresolved review notes.

## Models

The default model roles are configured separately and use three model names
from the assignment list:

| Role | Default model | Purpose |
|---|---|---|
| Extractor | `gpt-4o-mini` | Source-level requirement discovery |
| Consolidator | `gpt-5-mini` | Semantic deduplication and conflict preservation |
| Auditor | `gpt-4.1-nano` | Completeness, traceability, and consistency review |

The model names can be overridden with `REQUIREMENTS_EXTRACTOR_MODEL`,
`REQUIREMENTS_CONSOLIDATOR_MODEL`, and `REQUIREMENTS_AUDITOR_MODEL`. An
OpenAI-compatible endpoint can be set with `OPENAI_BASE_URL`.
Consolidation uses batches of up to 50 requirements and up to four concurrent
requests; this reduces waiting time but may issue multiple requests at once.

## Output decisions

- Identifiers use `REQ-001`, `REQ-002`, and so on, assigned after deterministic
  sorting.
- Every requirement includes its short name, category, testable statement,
  paragraph-long explanation, priority and rationale, source documents, and
  evidence excerpts.
- The priority scale is defined in the generated document: Critical, High,
  Medium, and Low.
- The blacklist retains proposals removed as superseded or nonsensical, with
  an explanation and source trace. Conflicts that cannot be responsibly
  resolved are retained as separate requirements and flagged.
- The final specification is a single Markdown file. The source corpus itself
  remains unchanged.

## Run instructions

Install dependencies from this directory:

```powershell
python -m pip install -r requirements.txt
```

For the simplest setup, open `requirements_agent.py` and replace
`PASTE_YOUR_OPENAI_API_KEY_HERE` in the `API_KEY` setting with your key. Save
the file, then run:

```powershell
python .\requirements_agent.py `
  --input-dir .\data\corpus `
  --output .\requirements.md
```

Alternatively, set `OPENAI_API_KEY` in PowerShell; an environment variable
takes precedence over the `API_KEY` value in the script:

```powershell
$env:OPENAI_API_KEY = "your-key"
python .\requirements_agent.py --input-dir .\data\corpus --output .\requirements.md
Remove-Item Env:OPENAI_API_KEY
```

For a compatible custom endpoint, set `OPENAI_BASE_URL` before running.
The program fails explicitly when the key, source directory, supported input,
or trace validation is invalid; it does not emit a success-shaped empty
specification. A key stored directly in source code can be exposed if that file
is shared or committed, so do not commit or publish the file with a real key.

## Validation and limitations

The deterministic loader, chunking, trace checks, and Markdown rendering can be
tested without API access. End-to-end content quality depends on the selected
models and their structured-output support. The final audit pass is bounded;
any remaining review findings are exposed in the generated document rather
than silently suppressed. The checked-in script contains only a placeholder
key value.
