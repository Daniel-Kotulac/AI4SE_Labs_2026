"""LangGraph network that turns a directory of source documents into an SRS."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
import json
import os
import re
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


EXTENSIONS = {".txt", ".eml", ".md", ".rst", ".csv", ".html", ".htm", ".json"}
CHUNK_CHARS = 10_000
MAX_PARALLEL_CALLS = 4
MAX_AUDIT_REPAIRS = 1
MAX_EXPLANATION_WORDS = 75


class Requirement(BaseModel):
    name: str = Field(description="A short descriptive name")
    statement: str = Field(description="One clear, testable requirement")
    explanation: str = Field(
        description="One informative paragraph of 2-4 complete sentences"
    )
    category: Literal["Functional", "Non-functional", "Constraint", "Assumption"]
    priority: Literal["Critical", "High", "Medium", "Low"]
    priority_reason: str
    sources: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)


class Discarded(BaseModel):
    name: str
    proposal: str = Field(
        description="Exact source wording of the rejected requirement candidate"
    )
    reason_type: Literal["conflict", "nonsensical"]
    reason: str
    sources: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(
        min_length=1,
        description="Exact source quotation supporting the classification",
    )


class Extraction(BaseModel):
    requirements: list[Requirement]


class Consolidation(BaseModel):
    requirements: list[Requirement]
    discarded: list[Discarded] = Field(default_factory=list)


class Audit(BaseModel):
    missing: list[Requirement] = Field(default_factory=list)
    discarded: list[Discarded] = Field(default_factory=list)
    consistency_issues: list[str] = Field(default_factory=list)


class Source(TypedDict):
    name: str
    text: str


class Chunk(TypedDict):
    source: str
    text: str


class State(TypedDict, total=False):
    input_dir: str
    output: str
    sources: list[Source]
    chunks: list[Chunk]
    requirements: list[Requirement]
    missing: list[Requirement]
    discarded: list[Discarded]
    issues: list[str]
    repairs: int


class Model(Protocol):
    def invoke(self, input: list[tuple[str, str]]) -> object: ...


def progress(message: str) -> None:
    print(f"[requirements] {message}", file=sys.stderr, flush=True)


def read_settings(path: Path | None = None) -> dict[str, str]:
    """Read simple KEY=VALUE settings without adding a dotenv dependency."""
    path = path or Path(__file__).with_name(".env")
    if not path.exists():
        return {}
    settings = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid setting at {path}:{number}; expected KEY=VALUE.")
        key, value = (part.strip() for part in line.split("=", 1))
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"Invalid setting name at {path}:{number}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        settings[key] = value
    return settings


def read_source(path: Path, source_name: str) -> Source:
    if path.suffix.lower() == ".eml":
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        headers = "\n".join(
            f"{key}: {message.get(key)}"
            for key in ("From", "To", "Cc", "Subject", "Date")
            if message.get(key)
        )
        parts = message.walk() if message.is_multipart() else [message]
        body = "\n".join(
            part.get_content()
            for part in parts
            if part.get_content_type() == "text/plain"
            and isinstance(part.get_content(), str)
        )
        text = f"{headers}\n\n{body}".strip()
    else:
        text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"Empty source document: {source_name}")
    return {"name": source_name, "text": text}


def load_sources(directory: Path) -> list[Source]:
    if not directory.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {directory}")
    paths = sorted(
        p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS
    )
    if not paths:
        raise ValueError(f"No supported source documents found in {directory}")
    return [
        read_source(path, path.relative_to(directory).as_posix()) for path in paths
    ]


def split_source(source: Source) -> list[Chunk]:
    """Split long documents near paragraph boundaries and retain their source path."""
    text = source["text"]
    chunks: list[Chunk] = []
    while text:
        if len(text) <= CHUNK_CHARS:
            part, text = text, ""
        else:
            cut = text.rfind("\n\n", 0, CHUNK_CHARS)
            if cut < CHUNK_CHARS // 2:
                cut = text.rfind("\n", 0, CHUNK_CHARS)
            if cut < CHUNK_CHARS // 2:
                cut = CHUNK_CHARS
            part, text = text[:cut], text[cut:].lstrip()
        chunks.append({"source": source["name"], "text": part.strip()})
    return chunks


def source_tag(requirement: Requirement, actual_source: str) -> Requirement:
    """Trust workflow source identity, not filenames generated by a model."""
    return requirement.model_copy(update={"sources": [actual_source]})


def validate_sources(
    requirements: list[Requirement], source_names: set[str]
) -> list[Requirement]:
    for item in requirements:
        unknown = set(item.sources) - source_names
        if not item.sources or unknown:
            raise ValueError(f"Invalid source trace for {item.name!r}: {sorted(unknown)}")
    return requirements


def bind_discarded_sources(
    items: list[Discarded],
    sources: list[Source],
    requirements: list[Requirement] | None = None,
) -> list[Discarded]:
    """Keep only proposals and evidence that can be verified in an input document."""

    def normalized(text: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

    bound = []
    for item in items:
        proposal = normalized(item.proposal)
        evidence = [normalized(quote) for quote in item.evidence]
        matches = {
            source["name"]
            for source in sources
            if len(proposal) >= 20
            and proposal in normalized(source["text"])
            and any(
                len(quote) >= 12 and quote in normalized(source["text"])
                for quote in evidence
            )
        }
        if matches and requirements:
            duplicate = any(
                (
                    proposal == normalized(requirement.statement)
                    or SequenceMatcher(
                        None, proposal, normalized(requirement.statement)
                    ).ratio()
                    >= 0.88
                )
                and bool(re.search(r"\bnot\b", proposal))
                == bool(re.search(r"\bnot\b", normalized(requirement.statement)))
                for requirement in requirements
            )
            if duplicate:
                progress(
                    f"Excluded blacklist candidate {item.name!r}: it duplicates "
                    "a retained requirement."
                )
                continue
        if not matches:
            progress(
                f"Excluded blacklist candidate {item.name!r}: its proposed "
                "requirement and supporting evidence could not both be verified "
                "in the cited source documents."
            )
            continue
        bound.append(item.model_copy(update={"sources": sorted(matches)}))
    return bound


def merge_exact_duplicates(requirements: list[Requirement]) -> list[Requirement]:
    """Merge exact or very close duplicate statements while preserving trace data."""
    merged: list[Requirement] = []
    for candidate in requirements:
        text = " ".join(candidate.statement.casefold().split())
        duplicate = next(
            (
                index
                for index, previous in enumerate(merged)
                if (
                    " ".join(previous.statement.casefold().split()) == text
                    or (
                        previous.name.casefold() == candidate.name.casefold()
                        and SequenceMatcher(
                            None,
                            " ".join(previous.statement.casefold().split()),
                            text,
                        ).ratio()
                        >= 0.9
                    )
                )
                and bool(re.search(r"\bnot\b", previous.statement.casefold()))
                == bool(re.search(r"\bnot\b", candidate.statement.casefold()))
            ),
            None,
        )
        if duplicate is None:
            merged.append(candidate)
            continue
        previous = merged[duplicate]
        merged[duplicate] = previous.model_copy(
            update={
                "sources": sorted(set(previous.sources + candidate.sources)),
                "evidence": list(dict.fromkeys(previous.evidence + candidate.evidence)),
            }
        )
    return merged


def compact_payload(requirements: list[Requirement]) -> str:
    fields = (
        "name",
        "statement",
        "explanation",
        "category",
        "priority",
        "priority_reason",
        "sources",
        "evidence",
    )
    return json.dumps(
        [{key: getattr(item, key) for key in fields} for item in requirements],
        ensure_ascii=False,
    )


def render(
    requirements: list[Requirement],
    discarded: list[Discarded],
    source_names: list[str],
    issues: list[str],
) -> str:
    """Write one compact SRS while retaining every requirement's trace."""
    known_sources = set(source_names)
    validate_sources(requirements, known_sources)
    validate_discarded_sources(discarded, known_sources)
    ordered = sorted(
        merge_exact_duplicates(requirements),
        key=lambda item: (item.category, item.name.casefold()),
    )
    out = [
        "# Software Requirements Specification",
        "",
        "## Priority scale",
        "",
        "- **Critical:** Explicitly critical or legally/audit essential.",
        "- **High:** Core operational, security, accessibility, or performance need.",
        "- **Medium:** Important capability, not identified as critical.",
        "- **Low:** Desirable, optional, or weakly evidenced.",
        "",
        "Priority is assigned from stakeholder emphasis, legal/compliance risk, "
        "and operational impact.",
        "",
        "## Source documents",
        "",
        *[f"- `{name}`" for name in sorted(source_names)],
        "",
        "## Requirements",
        "",
    ]
    for index, item in enumerate(ordered, 1):
        sources = ", ".join(f"`{name}`" for name in sorted(set(item.sources)))
        explanation = concise_paragraph(item.explanation)
        out.extend(
            [
                f"### REQ-{index:03d} - {item.name}",
                "",
                f"**{item.category} | {item.priority}**",
                "",
                f"**{item.statement}**",
                "",
                explanation,
                "",
                f"**Trace:** {sources}",
                "",
            ]
        )

    out.extend(["## Blacklist: conflicting or nonsensical candidates", ""])
    if discarded:
        for item in discarded:
            sources = ", ".join(f"`{name}`" for name in sorted(set(item.sources)))
            out.extend(
                [
                    f"### {item.name}",
                    "",
                    f"**Rejected candidate:** {item.proposal}",
                    "",
                    f"**Reason:** {item.reason_type} - {item.reason}",
                    "",
                    f"**Evidence:** {'; '.join(item.evidence)}",
                    "",
                    f"**Trace:** {sources}",
                    "",
                ]
            )
    else:
        out.extend(["No source-derived requirements were rejected as conflicting or nonsensical.", ""])

    out.extend(["## Consistency review", ""])
    out.extend(f"- {issue}" for issue in dict.fromkeys(issues))
    if not issues:
        out.append("No unresolved contradictions were identified.")
    out.append("")
    return "\n".join(out)


def concise_paragraph(text: str) -> str:
    """Keep a complete paragraph, shortening only at sentence boundaries."""
    text = " ".join(text.split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected: list[str] = []
    for sentence in sentences:
        if len(" ".join(selected + [sentence]).split()) > MAX_EXPLANATION_WORDS:
            break
        selected.append(sentence)
    return " ".join(selected) if selected else text


def build_graph(extractor: Model, consolidator: Model, auditor: Model):
    """Build the five-node LangGraph pipeline with one bounded feedback edge."""

    def ingest(state: State) -> dict:
        progress(f"Reading source documents from {state['input_dir']}...")
        sources = load_sources(Path(state["input_dir"]))
        chunks = [chunk for source in sources for chunk in split_source(source)]
        progress(
            f"Input ready: loaded {len(sources)} documents and split them into "
            f"{len(chunks)} chunks."
        )
        return {"sources": sources, "chunks": chunks}

    def extract(state: State) -> dict:
        chunks = state["chunks"]

        def extract_chunk(chunk: Chunk) -> list[Requirement]:
            progress(f"Extracting {chunk['source']}.")
            result = extractor.invoke(
                [
                    (
                        "system",
                        "Extract every distinct software requirement supported by the source "
                        "excerpt. Include explicit functions, quality needs, constraints, "
                        "assumptions, thresholds, and unresolved stakeholder alternatives. "
                        "Ignore personal chatter. Do not infer implementation detail. Each "
                        "requirement needs a short name, testable statement, a complete "
                        "2-4-sentence explanatory paragraph, priority and brief rationale, "
                        "one short supporting quote, and the exact source path supplied.",
                    ),
                    ("human", f"Source: {chunk['source']}\n\n{chunk['text']}"),
                ]
            )
            return [
                source_tag(item, chunk["source"])
                for item in Extraction.model_validate(result).requirements
            ]

        progress(
            f"Starting requirement extraction from {len(chunks)} chunks "
            f"(up to {MAX_PARALLEL_CALLS} calls at once)..."
        )
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
            batches = list(pool.map(extract_chunk, chunks))
        requirements = [item for batch in batches for item in batch]
        if not requirements:
            raise ValueError("No requirements were extracted from the source corpus.")
        progress(f"Extraction complete: collected {len(requirements)} candidates.")
        return {"requirements": requirements}

    def consolidate(state: State) -> dict:
        source_names = {source["name"] for source in state["sources"]}
        progress(
            f"Consolidating {len(state['requirements'])} candidates across "
            f"{len(source_names)} documents; merging duplicates and identifying "
            "supported conflicts..."
        )
        result = consolidator.invoke(
            [
                (
                    "system",
                    "Refine the complete candidate set. Merge all semantically duplicate "
                    "requirements, including entries where one requirement adds filters, "
                    "options, exclusions, flags, or audit details to the same underlying "
                    "capability. Put those details into one complete requirement and combine "
                    "all supporting sources and evidence. Do not leave a base capability and "
                    "its detailed sub-requirement as separate entries. Do not merge merely "
                    "related capabilities that can be independently tested. Do not put "
                    "duplicates on the blacklist. Do not blacklist a merely rejected, "
                    "unsupported, speculative, or duplicate candidate. A blacklist entry "
                    "must be an actual proposed system requirement stated in the source, "
                    "not unrelated conversation, an open question, a missing requirement, "
                    "or a model-invented alternative. Include the exact source wording of "
                    "that candidate in `proposal` and an exact supporting quotation in "
                    "`evidence`. If the candidate wording cannot be quoted from an input "
                    "document, omit it. Blacklist only a source-derived requirement that "
                    "is genuinely nonsensical or conflicts with a more authoritative "
                    "resolved requirement. For conflicts, identify the conflicting "
                    "requirement and why its evidence is more authoritative. Preserve "
                    "unresolved alternatives as requirements and flag them instead. Keep "
                    "names concise, statements testable, and explanations to 2-4 complete "
                    "sentences.",
                ),
                ("human", compact_payload(state["requirements"])),
            ]
        )
        merged = Consolidation.model_validate(result)
        requirements = validate_sources(merged.requirements, source_names)
        discarded = bind_discarded_sources(
            merged.discarded, state["sources"], requirements
        )
        progress(
            f"Consolidation complete: {len(requirements)} requirements retained; "
            f"{len(discarded)} candidates placed on the blacklist."
        )
        return {"requirements": requirements, "discarded": discarded}

    def audit(state: State) -> dict:
        """Check every source chunk for omissions, evidence, and contradictions."""
        current = state["requirements"]
        chunks = state["chunks"]

        def audit_chunk(chunk: Chunk) -> Audit:
            progress(f"Auditing {chunk['source']}.")
            linked = [item for item in current if chunk["source"] in item.sources]
            result = auditor.invoke(
                [
                    (
                        "system",
                        "Compare the source excerpt against its linked requirements. Find material "
                        "requirements missing from the list; do not restate a requirement already "
                        "covered. Blacklist only an actual proposed system requirement stated in "
                        "the source that is genuinely nonsensical or demonstrably conflicts with "
                        "a better-supported resolved requirement. Do not blacklist an unsupported "
                        "rejection, duplicate, open question, missing requirement, unrelated "
                        "conversation, or a proposal invented by you. For each blacklist entry, "
                        "include the exact source wording as `proposal`, an exact supporting "
                        "quotation as `evidence`, and explain why the proposal is nonsensical or "
                        "what resolved requirement it conflicts with. If the source does not "
                        "contain the proposal, omit it. Flag unresolved ambiguity or conflicts "
                        "instead of blacklisting them.",
                    ),
                    (
                        "human",
                        f"Exact source path: {chunk['source']}\n\n"
                        f"Source excerpt:\n{chunk['text']}\n\n"
                        f"Linked requirements:\n{compact_payload(linked)}",
                    ),
                ]
            )
            return Audit.model_validate(result)

        progress(
            f"Starting completeness audit across {len(chunks)} chunks, then "
            "checking consistency across the complete requirement set..."
        )
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
            reviews = list(pool.map(audit_chunk, chunks))

        source_names = {source["name"] for source in state["sources"]}
        missing = [
            source_tag(item, chunk["source"])
            for chunk, review in zip(chunks, reviews)
            for item in review.missing
        ]
        discarded = list(state.get("discarded", []))
        for review in reviews:
            discarded.extend(review.discarded)
        progress("Checking for contradictions and terminology across all documents...")
        global_review_result = auditor.invoke(
            [
                (
                    "system",
                    "Review this complete requirement set for cross-document contradictions "
                    "and consistent terminology. Do not create blacklist entries in this global "
                    "review because the complete source text is not provided here. Do not "
                    "blacklist duplicates or unsupported candidates. If a conflict cannot be "
                    "resolved from the corpus, retain the requirements and report the unresolved "
                    "issue instead of choosing arbitrarily.",
                ),
                (
                    "human",
                    "Source paths:\n"
                    + json.dumps(sorted(source_names))
                    + "\n\nComplete requirements:\n"
                    + compact_payload(current),
                ),
            ]
        )
        global_review = Audit.model_validate(global_review_result)
        if global_review.discarded:
            progress(
                "Ignoring global blacklist suggestions because this review has no "
                "source excerpts to verify them against."
            )
        discarded = bind_discarded_sources(
            discarded, state["sources"], current + missing
        )
        validate_sources(missing, source_names)
        validate_discarded_sources(discarded, source_names)
        progress(
            f"Audit complete: found {len(missing)} potentially missing requirements, "
            f"{len(discarded)} blacklist entries, and "
            f"{len(global_review.consistency_issues) + sum(len(review.consistency_issues) for review in reviews)} "
            "consistency notes."
        )
        return {
            "missing": merge_exact_duplicates(missing),
            "discarded": deduplicate_blacklist(discarded),
            "issues": list(
                dict.fromkeys(
                    state.get("issues", [])
                    + [
                        issue
                        for review in reviews
                        for issue in review.consistency_issues
                    ]
                    + global_review.consistency_issues
                )
            ),
            "repairs": state.get("repairs", 0) + 1,
        }

    def refine(state: State) -> dict:
        """Merge audit additions and recheck them once; retain existing blacklist."""
        candidates = state["requirements"] + state.get("missing", [])
        progress(
            f"Refinement round: merging {len(state.get('missing', []))} "
            "audit-discovered requirements, then running the bounded recheck..."
        )
        result = consolidator.invoke(
            [
                (
                    "system",
                    "Merge audit-discovered omissions into the complete requirements set. "
                    "Deduplicate semantically, including candidates that add details to an "
                    "existing capability; combine their sources and evidence rather than "
                    "keeping a base requirement and a scoped sub-requirement separately. "
                    "Do not merge merely related, independently testable capabilities. Keep "
                    "every distinct requirement. Do not create blacklist entries for duplicates.",
                ),
                ("human", compact_payload(candidates)),
            ]
        )
        merged = Consolidation.model_validate(result)
        requirements = validate_sources(
            merged.requirements, {source["name"] for source in state["sources"]}
        )
        progress(f"Refinement complete: now tracking {len(requirements)} requirements.")
        return {
            "requirements": requirements,
            "missing": [],
        }

    def route(state: State) -> Literal["refine", "write"]:
        if state.get("missing") and state.get("repairs", 0) <= MAX_AUDIT_REPAIRS:
            return "refine"
        return "write"

    def write(state: State) -> dict:
        output = Path(state["output"])
        progress(
            f"Preparing final specification with {len(state['requirements'])} "
            "requirements, source traces, priorities, and blacklist..."
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        content = render(
            state["requirements"],
            state.get("discarded", []),
            [source["name"] for source in state["sources"]],
            state.get("issues", []),
        )
        output.write_text(content, encoding="utf-8")
        progress(f"Finished successfully. Wrote the specification to {output}.")
        return {}

    graph = StateGraph(State)
    for name, node in (
        ("ingest", ingest),
        ("extract", extract),
        ("consolidate", consolidate),
        ("audit", audit),
        ("refine", refine),
        ("write", write),
    ):
        graph.add_node(name, node)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "extract")
    graph.add_edge("extract", "consolidate")
    graph.add_edge("consolidate", "audit")
    graph.add_conditional_edges("audit", route, {"refine": "refine", "write": "write"})
    graph.add_edge("refine", "audit")
    graph.add_edge("write", END)
    return graph.compile()


def make_model(role: str, default: str, key: str, base_url: str | None) -> Model:
    kwargs = {"model": os.environ.get(f"REQUIREMENTS_{role.upper()}_MODEL", default), "api_key": key}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs).with_structured_output(
        {"extractor": Extraction, "consolidator": Consolidation, "auditor": Audit}[role]
    )


def run(input_dir: Path, output: Path) -> None:
    progress("Starting the requirements workflow.")
    settings = read_settings()
    key = os.environ.get("OPENAI_API_KEY") or settings.get("OPENAI_API_KEY")
    if not key or key == "PASTE_YOUR_KEY_HERE":
        raise EnvironmentError(
            f"Set OPENAI_API_KEY in {Path(__file__).with_name('.env')} or the environment."
        )
    base_url = os.environ.get("OPENAI_BASE_URL") or settings.get("OPENAI_BASE_URL")
    progress("API configuration found; initializing the extraction, consolidation, and audit models.")
    graph = build_graph(
        make_model("extractor", "gpt-4o-mini", key, base_url),
        make_model("consolidator", "gpt-5-mini", key, base_url),
        make_model("auditor", "gpt-4.1-nano", key, base_url),
    )
    graph.invoke({"input_dir": str(input_dir), "output": str(output)})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("requirements.md"))
    args = parser.parse_args()
    try:
        run(args.input_dir, args.output)
    except (EnvironmentError, NotADirectoryError, ValueError, RuntimeError) as exc:
        print(f"Requirements workflow failed: {exc}", file=sys.stderr)
        return 1
    return 0


def validate_discarded_sources(
    items: list[Discarded], source_names: set[str]
) -> list[Discarded]:
    for item in items:
        unknown = set(item.sources) - source_names
        if not item.sources or unknown:
            raise ValueError(f"Invalid blacklist trace for {item.name!r}: {sorted(unknown)}")
    return items


def deduplicate_blacklist(items: list[Discarded]) -> list[Discarded]:
    """Merge repeated source proposals, not merely entries with similar names."""
    merged: dict[str, Discarded] = {}
    for item in items:
        key = " ".join(re.findall(r"[a-z0-9]+", item.proposal.casefold()))
        previous = merged.get(key)
        if previous is None:
            merged[key] = item
            continue
        merged[key] = previous.model_copy(
            update={
                "sources": sorted(set(previous.sources + item.sources)),
                "evidence": list(dict.fromkeys(previous.evidence + item.evidence)),
            }
        )
    return list(merged.values())


if __name__ == "__main__":
    raise SystemExit(main())
