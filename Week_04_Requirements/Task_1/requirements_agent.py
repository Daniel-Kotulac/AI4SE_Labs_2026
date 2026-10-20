"""Agentic requirements-refinement workflow for a directory of source documents."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


# Paste your key here, or provide OPENAI_API_KEY as an environment variable.
# Environment-variable values take precedence.
API_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"

SUPPORTED_EXTENSIONS = {".txt", ".eml", ".md", ".rst", ".csv", ".html", ".htm", ".json"}
DEFAULT_CHUNK_SIZE = 12_000
DEFAULT_CHUNK_OVERLAP = 800
MAX_FEEDBACK_ROUNDS = 1
CONSOLIDATION_BATCH_SIZE = 50
MAX_CONSOLIDATION_PASSES = 3
MAX_CONSOLIDATION_WORKERS = 4


class Requirement(BaseModel):
    name: str = Field(description="Short descriptive title, not an ID")
    category: Literal["Functional", "Non-functional", "Constraint", "Assumption"]
    statement: str = Field(description="One clear, testable requirement")
    explanation: str = Field(description="A paragraph explaining scope and purpose")
    priority: Literal["Critical", "High", "Medium", "Low"]
    priority_rationale: str
    source_documents: list[str] = Field(min_length=1)
    evidence: list[str] = Field(min_length=1, description="Short supporting excerpts")


class DiscardedRequirement(BaseModel):
    name: str
    explanation: str
    source_documents: list[str] = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    requirements: list[Requirement]


class ConsolidationResult(BaseModel):
    requirements: list[Requirement]
    discarded: list[DiscardedRequirement] = Field(default_factory=list)


class ReviewResult(BaseModel):
    missing_requirements: list[Requirement] = Field(default_factory=list)
    discarded: list[DiscardedRequirement] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class SourceDocument(BaseModel):
    source_id: str
    text: str


class SourceChunk(BaseModel):
    source_id: str
    chunk_number: int
    text: str


class WorkflowState(TypedDict, total=False):
    input_dir: str
    output_path: str
    documents: list[SourceDocument]
    chunks: list[SourceChunk]
    requirements: list[Requirement]
    missing_requirements: list[Requirement]
    discarded: list[DiscardedRequirement]
    audit_notes: list[str]
    audit_round: int


class StructuredInvoker(Protocol):
    def invoke(self, input: list[tuple[str, str]]) -> object: ...


def _progress(message: str) -> None:
    print(f"[requirements] {message}", file=sys.stderr, flush=True)


def _read_document(path: Path, source_id: str) -> SourceDocument:
    if path.suffix.lower() == ".eml":
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        headers = "\n".join(
            f"{name}: {message.get(name)}"
            for name in ("From", "To", "Cc", "Subject", "Date")
            if message.get(name)
        )
        body_parts: list[str] = []
        parts = message.walk() if message.is_multipart() else [message]
        for part in parts:
            if part.get_content_type() != "text/plain":
                continue
            content = part.get_content()
            if isinstance(content, str):
                body_parts.append(content)
        body = "\n".join(body_parts)
        text = f"{headers}\n\n{body}".strip()
    else:
        text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"Source document is empty: {source_id}")
    return SourceDocument(source_id=source_id, text=text)


def load_documents(input_dir: Path) -> list[SourceDocument]:
    """Load supported text formats recursively, using relative paths as trace IDs."""
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {input_dir}")
    paths = sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not paths:
        raise ValueError(f"No supported text documents found in {input_dir}")
    documents = [
        _read_document(path, path.relative_to(input_dir).as_posix())
        for path in paths
    ]
    return documents


def chunk_document(
    document: SourceDocument,
    max_chars: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[SourceChunk]:
    """Split long source documents into bounded, slightly overlapping excerpts."""
    if max_chars < 1 or overlap < 0 or overlap >= max_chars:
        raise ValueError("Chunk size must be positive and overlap smaller than chunk size")
    if len(document.text) <= max_chars:
        return [SourceChunk(source_id=document.source_id, chunk_number=1, text=document.text)]
    chunks: list[SourceChunk] = []
    step = max_chars - overlap
    for index, start in enumerate(range(0, len(document.text), step), start=1):
        excerpt = document.text[start : start + max_chars]
        if excerpt:
            chunks.append(
                SourceChunk(source_id=document.source_id, chunk_number=index, text=excerpt)
            )
    return chunks


def _validate_sources(
    requirements: list[Requirement], valid_source_ids: set[str]
) -> list[Requirement]:
    checked: list[Requirement] = []
    for requirement in requirements:
        sources = sorted(set(requirement.source_documents))
        unknown = set(sources) - valid_source_ids
        if unknown:
            raise ValueError(
                f"Requirement {requirement.name!r} cites unknown documents: "
                + ", ".join(sorted(unknown))
            )
        if not sources:
            raise ValueError(f"Requirement {requirement.name!r} has no traceable source")
        checked.append(requirement.model_copy(update={"source_documents": sources}))
    return checked


def _requirement_payload(requirements: list[Requirement]) -> list[dict[str, object]]:
    return [requirement.model_dump() for requirement in requirements]


def _consolidate(
    model: StructuredInvoker, requirements: list[Requirement]
) -> tuple[list[Requirement], list[DiscardedRequirement]]:
    """Consolidate bounded batches concurrently and stop when another pass cannot help."""
    current = requirements
    discarded: list[DiscardedRequirement] = []
    for pass_number in range(1, MAX_CONSOLIDATION_PASSES + 1):
        batches = [
            current[index : index + CONSOLIDATION_BATCH_SIZE]
            for index in range(0, len(current), CONSOLIDATION_BATCH_SIZE)
        ]
        if not batches:
            return [], discarded
        _progress(
            f"Consolidating {len(current)} candidates "
            f"(pass {pass_number}/{MAX_CONSOLIDATION_PASSES}, {len(batches)} batch(es), "
            f"up to {min(MAX_CONSOLIDATION_WORKERS, len(batches))} in parallel)..."
        )
        combined: list[Requirement | None] = [None] * len(batches)
        with ThreadPoolExecutor(
            max_workers=min(MAX_CONSOLIDATION_WORKERS, len(batches))
        ) as executor:
            futures = {
                executor.submit(
                    model.invoke,
                    [
                        (
                            "system",
                            "Consolidate software requirements. Merge semantic duplicates while "
                            "combining all supporting source_documents and evidence. Keep every "
                            "distinct requirement. Preserve unresolved contradictions as separate "
                            "requirements and explain the conflict in the explanation. Only put "
                            "a proposal in discarded if it is nonsensical or clearly superseded; "
                            "explain why. Write a testable statement, a paragraph-long explanation, "
                            "and priority rationale. Use only source paths present in the input.",
                        ),
                        (
                            "human",
                            json.dumps(_requirement_payload(batch), ensure_ascii=False),
                        ),
                    ],
                ): batch_index
                for batch_index, batch in enumerate(batches)
            }
            for future in as_completed(futures):
                batch_index = futures[future]
                _progress(
                    f"Consolidation batch {batch_index + 1}/{len(batches)} completed."
                )
                current_result = ConsolidationResult.model_validate(future.result())
                combined[batch_index] = current_result.requirements
                discarded.extend(current_result.discarded)
        flattened = [requirement for batch in combined if batch for requirement in batch]
        if len(flattened) >= len(current):
            current = flattened
            _progress(
                "Consolidation stopped because another pass did not reduce the candidate count."
            )
            break
        current = flattened
        if len(current) <= CONSOLIDATION_BATCH_SIZE:
            break

    if current and len(current) <= CONSOLIDATION_BATCH_SIZE:
        _progress(f"Running final deduplication on {len(current)} candidates...")
        result = model.invoke(
            [
                (
                    "system",
                    "Perform a final semantic deduplication of this complete requirement set. "
                    "Retain all distinct requirements, merge duplicate evidence and source "
                    "documents, and preserve unresolved conflicts rather than silently choosing "
                    "one. Discard only clearly nonsensical or superseded proposals with reasons.",
                ),
                ("human", json.dumps(_requirement_payload(current), ensure_ascii=False)),
            ]
        )
        final = ConsolidationResult.model_validate(result)
        current = final.requirements
        discarded.extend(final.discarded)
    return current, discarded


def _format_requirement(index: int, requirement: Requirement) -> str:
    sources = ", ".join(f"`{source}`" for source in requirement.source_documents)
    evidence = "; ".join(f'"{quote}"' for quote in requirement.evidence)
    return (
        f"### REQ-{index:03d} - {requirement.name}\n\n"
        f"- **Category:** {requirement.category}\n"
        f"- **Priority:** {requirement.priority} - {requirement.priority_rationale}\n"
        f"- **Statement:** {requirement.statement}\n\n"
        f"{requirement.explanation}\n\n"
        f"- **Trace:** {sources}\n"
        f"- **Evidence:** {evidence}\n"
    )


def render_requirements_document(
    requirements: list[Requirement],
    discarded: list[DiscardedRequirement],
    source_ids: list[str],
    audit_notes: list[str] | None = None,
) -> str:
    """Render a single structured Markdown specification with stable IDs."""
    valid_source_ids = set(source_ids)
    checked = _validate_sources(requirements, valid_source_ids)
    checked.sort(key=lambda requirement: (requirement.category, requirement.name.casefold()))
    blacklist = _validate_discarded_sources(discarded, valid_source_ids)
    sections = [
        "# PINES Management Reporting System - Requirements Specification",
        "",
        "## Scope and source corpus",
        "",
        "This specification consolidates requirements for the PINES management "
        "reporting system from the source documents listed below.",
        "",
        *[f"- `{source}`" for source in sorted(source_ids)],
        "",
        "## Requirement priority scale",
        "",
        "- **Critical:** Explicitly described as critical or legally/audit essential; "
        "failure would create a material operational or compliance risk.",
        "- **High:** Core operational, accessibility, security, or performance need "
        "explicitly required by stakeholders.",
        "- **Medium:** Important capability or constraint that improves reporting or "
        "administration but is not identified as critical.",
        "- **Low:** Desirable, optional, or weakly evidenced capability.",
        "",
        "Priority is an evidence-based refinement of the source material; each item "
        "includes its individual rationale.",
        "",
        "## Requirements",
        "",
    ]
    sections.extend(
        _format_requirement(index, requirement)
        for index, requirement in enumerate(checked, 1)
    )
    sections.extend(["## Discarded / conflicting proposals", ""])
    if blacklist:
        for item in blacklist:
            sources = ", ".join(f"`{source}`" for source in item.source_documents)
            sections.append(f"### {item.name}")
            sections.append("")
            sections.append(item.explanation)
            sections.append("")
            sections.append(f"- **Trace:** {sources}")
            if item.evidence:
                sections.append(
                    "- **Evidence:** "
                    + "; ".join(f'"{quote}"' for quote in item.evidence)
                )
            sections.append("")
    else:
        sections.append(
            "No proposals were discarded by the refinement workflow. "
            "Unresolved conflicts are retained as separate requirements and called out "
            "in their explanations or the consistency review notes."
        )
        sections.append("")
    sections.extend(["## Consistency review notes", ""])
    if audit_notes:
        sections.extend(f"- {note}" for note in dict.fromkeys(audit_notes))
    else:
        sections.append("The final review identified no unresolved consistency issues.")
    sections.append("")
    return "\n".join(sections)


def _validate_discarded_sources(
    discarded: list[DiscardedRequirement], valid_source_ids: set[str]
) -> list[DiscardedRequirement]:
    result: list[DiscardedRequirement] = []
    for item in discarded:
        unknown = set(item.source_documents) - valid_source_ids
        if unknown:
            raise ValueError(
                f"Discarded proposal {item.name!r} cites unknown documents: "
                + ", ".join(sorted(unknown))
            )
        result.append(
            item.model_copy(
                update={"source_documents": sorted(set(item.source_documents))}
            )
        )
    return result


def build_workflow(
    *,
    extractor: StructuredInvoker,
    consolidator: StructuredInvoker,
    auditor: StructuredInvoker,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
):
    """Build the LangGraph network; models are injected to enable offline tests."""

    def ingest(state: WorkflowState) -> dict[str, object]:
        documents = load_documents(Path(state["input_dir"]))
        chunks = [
            chunk
            for document in documents
            for chunk in chunk_document(document, chunk_size, chunk_overlap)
        ]
        _progress(f"Loaded {len(documents)} document(s) into {len(chunks)} chunk(s).")
        return {"documents": documents, "chunks": chunks}

    def extract(state: WorkflowState) -> dict[str, object]:
        collected: list[Requirement] = []
        total_chunks = len(state["chunks"])
        for index, chunk in enumerate(state["chunks"], start=1):
            _progress(
                f"Extracting requirements from chunk {index}/{total_chunks}: "
                f"{chunk.source_id}"
            )
            result = extractor.invoke(
                [
                    (
                        "system",
                        "Extract atomic, non-duplicative software requirements from this source "
                        "excerpt. Include functional and non-functional requirements, constraints, "
                        "assumptions, priorities, explicit thresholds, and unresolved ambiguity. "
                        "Do not turn unrelated personal chatter into requirements. Use the exact "
                        "provided source path, cite a short verbatim evidence excerpt, and explain "
                        "each requirement in a paragraph. Do not infer a priority without a "
                        "priority rationale.",
                    ),
                    (
                        "human",
                        f"Source path: {chunk.source_id}\n"
                        f"Excerpt {chunk.chunk_number}:\n{chunk.text}",
                    ),
                ]
            )
            collected.extend(ExtractionResult.model_validate(result).requirements)
        valid_sources = {document.source_id for document in state["documents"]}
        if not collected:
            raise ValueError(
                "No requirements were extracted from the input documents; "
                "review the corpus or model response before generating output."
            )
        return {"requirements": _validate_sources(collected, valid_sources)}

    def consolidate(state: WorkflowState) -> dict[str, object]:
        requirements, discarded = _consolidate(consolidator, state["requirements"])
        if not requirements:
            raise ValueError("Consolidation removed every extracted requirement")
        return {"requirements": requirements, "discarded": discarded}

    def audit(state: WorkflowState) -> dict[str, object]:
        all_missing: list[Requirement] = []
        all_discarded: list[DiscardedRequirement] = []
        all_notes: list[str] = []
        requirements = state["requirements"]
        total_chunks = len(state["chunks"])
        for index, chunk in enumerate(state["chunks"], start=1):
            _progress(
                f"Auditing chunk {index}/{total_chunks}: {chunk.source_id} "
                f"(review round {state.get('audit_round', 0) + 1})"
            )
            local = [
                req for req in requirements if chunk.source_id in req.source_documents
            ]
            result = auditor.invoke(  # type: ignore[attr-defined]
                [
                    (
                        "system",
                        "Audit this source excerpt against the proposed requirements for "
                        "completeness, traceability, consistency, and contradictions. Identify "
                        "material requirements from the source that are missing. Ignore unrelated "
                        "personal chatter. Do not invent requirements. Retain competing stakeholder "
                        "needs unless evidence clearly shows one was superseded. Record a discarded "
                        "proposal and its reason when a conflict is clearly resolved or a statement "
                        "is nonsensical. Cite only the supplied source path.",
                    ),
                    (
                        "human",
                        f"Source path: {chunk.source_id}\n"
                        f"Source excerpt:\n{chunk.text}\n\n"
                        "Current requirements tied to this source:\n"
                        f"{json.dumps(_requirement_payload(local), ensure_ascii=False)}",
                    ),
                ]
            )
            reviewed = ReviewResult.model_validate(result)
            all_missing.extend(reviewed.missing_requirements)
            all_discarded.extend(reviewed.discarded)
            all_notes.extend(reviewed.issues)
        valid_sources = {document.source_id for document in state["documents"]}
        return {
            "missing_requirements": _validate_sources(all_missing, valid_sources),
            "discarded": state.get("discarded", []) + _validate_discarded_sources(
                all_discarded, valid_sources
            ),
            "audit_notes": all_notes,
            "audit_round": state.get("audit_round", 0) + 1,
        }

    def refine(state: WorkflowState) -> dict[str, object]:
        candidates = state["requirements"] + state.get("missing_requirements", [])
        _progress(
            f"Refining requirements with {len(state.get('missing_requirements', []))} "
            "audit finding(s)..."
        )
        requirements, newly_discarded = _consolidate(consolidator, candidates)
        return {
            "requirements": requirements,
            "missing_requirements": [],
            "discarded": state.get("discarded", []) + newly_discarded,
        }

    def route_after_audit(state: WorkflowState) -> Literal["refine", "render"]:
        needs_refinement = bool(state.get("missing_requirements"))
        if state.get("audit_round", 0) <= MAX_FEEDBACK_ROUNDS and needs_refinement:
            return "refine"
        return "render"

    def render(state: WorkflowState) -> dict[str, object]:
        final_candidates = state["requirements"] + state.get("missing_requirements", [])
        _progress("Preparing the final requirements document...")
        final_requirements, final_discarded = _consolidate(consolidator, final_candidates)
        if not final_requirements:
            raise ValueError("No requirements remain after final refinement")
        source_ids = [document.source_id for document in state["documents"]]
        content = render_requirements_document(
            final_requirements,
            state.get("discarded", []) + final_discarded,
            source_ids,
            state.get("audit_notes", []),
        )
        output_path = Path(state["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        _progress(
            f"Wrote {len(final_requirements)} requirement(s) to {output_path}."
        )
        return {"requirements": final_requirements, "discarded": state.get("discarded", []) + final_discarded}

    graph = StateGraph(WorkflowState)
    graph.add_node("ingest", ingest)
    graph.add_node("extract", extract)
    graph.add_node("consolidate", consolidate)
    graph.add_node("audit", audit)
    graph.add_node("refine", refine)
    graph.add_node("render", render)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "extract")
    graph.add_edge("extract", "consolidate")
    graph.add_edge("consolidate", "audit")
    graph.add_conditional_edges(
        "audit", route_after_audit, {"refine": "refine", "render": "render"}
    )
    graph.add_edge("refine", "audit")
    graph.add_edge("render", END)
    return graph.compile()


def _model_from_env(role: str, default_name: str, api_key: str, base_url: str | None):
    model_name = os.environ.get(f"REQUIREMENTS_{role.upper()}_MODEL", default_name)
    kwargs: dict[str, str] = {"model": model_name, "api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def run(input_dir: Path, output_path: Path) -> None:
    api_key = os.environ.get("OPENAI_API_KEY") or API_KEY
    if not api_key or api_key == "PASTE_YOUR_OPENAI_API_KEY_HERE":
        raise EnvironmentError(
            "Add your API key to API_KEY in requirements_agent.py or set "
            "OPENAI_API_KEY in the environment."
        )
    base_url = os.environ.get("OPENAI_BASE_URL")
    extractor = _model_from_env("extractor", "gpt-4o-mini", api_key, base_url).with_structured_output(
        ExtractionResult
    )
    consolidator = _model_from_env(
        "consolidator", "gpt-5-mini", api_key, base_url
    ).with_structured_output(ConsolidationResult)
    auditor = _model_from_env("auditor", "gpt-4.1-nano", api_key, base_url).with_structured_output(
        ReviewResult
    )
    workflow = build_workflow(
        extractor=extractor, consolidator=consolidator, auditor=auditor
    )
    workflow.invoke(
        {"input_dir": str(input_dir), "output_path": str(output_path)}
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refine source documents into a traceable software requirements specification."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory recursively containing text, Markdown, CSV, JSON, HTML, or EML sources.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("requirements.md"),
        help="Destination Markdown file (default: requirements.md).",
    )
    args = parser.parse_args(argv)
    try:
        run(args.input_dir, args.output)
    except (EnvironmentError, NotADirectoryError, ValueError, RuntimeError) as error:
        print(f"Requirements workflow failed: {error}", file=sys.stderr)
        return 1
    print(f"Requirements document written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
