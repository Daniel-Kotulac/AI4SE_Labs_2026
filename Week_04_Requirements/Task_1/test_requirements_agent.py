import json
import tempfile
import threading
import unittest
from pathlib import Path

from requirements_agent import (
    ConsolidationResult,
    ExtractionResult,
    Requirement,
    ReviewResult,
    SourceDocument,
    build_workflow,
    chunk_document,
    render_requirements_document,
    _consolidate,
)


def requirement(name, source, statement):
    return Requirement(
        name=name,
        category="Functional",
        statement=statement,
        explanation="The feature supports staff work and provides predictable access to "
        "reporting information across locations.",
        priority="Medium",
        priority_rationale="The source describes this as a needed staff capability.",
        source_documents=[source],
        evidence=[statement],
    )


class FakeExtractor:
    def invoke(self, _messages):
        return ExtractionResult(
            requirements=[
                requirement(
                    "Basic reporting",
                    "brief.txt",
                    "The system must provide reports for library staff.",
                )
            ]
        )


class FakeConsolidator:
    def invoke(self, messages):
        raw = json.loads(messages[1][1])
        return ConsolidationResult(
            requirements=[Requirement.model_validate(item) for item in raw]
        )


class FakeAuditor:
    def __init__(self):
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        if self.calls == 1:
            return ReviewResult(
                missing_requirements=[
                    requirement(
                        "CSV export",
                        "brief.txt",
                        "The system must export reports as CSV.",
                    )
                ]
            )
        return ReviewResult()


class ConcurrentConsolidator:
    def __init__(self):
        self.barrier = threading.Barrier(4)
        self.calls = 0
        self.lock = threading.Lock()

    def invoke(self, messages):
        self.barrier.wait(timeout=3)
        with self.lock:
            self.calls += 1
        raw = json.loads(messages[1][1])
        return ConsolidationResult(
            requirements=[Requirement.model_validate(item) for item in raw]
        )


class RequirementsAgentTests(unittest.TestCase):
    def test_chunking_preserves_source_and_covers_end(self):
        doc = SourceDocument(source_id="nested/source.txt", text="abcdefghij" * 10)
        chunks = chunk_document(doc, max_chars=30, overlap=5)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.source_id == doc.source_id for chunk in chunks))
        self.assertTrue(chunks[-1].text.endswith("j"))

    def test_render_assigns_unique_ids_and_traces(self):
        requirements = [
            Requirement(
                name="Accessible output",
                category="Non-functional",
                statement="The system must provide accessible HTML reports.",
                explanation="Reports must use semantic HTML to support assistive technology "
                "and allow staff with disabilities to use the reporting interface.",
                priority="High",
                priority_rationale="The source identifies accessibility as mandatory.",
                source_documents=["interview.txt"],
                evidence=["must comply with accessibility requirements"],
            ),
            Requirement(
                name="Role-based access",
                category="Functional",
                statement="The system must control report access by staff role.",
                explanation="Administrators must assign staff to roles so report permissions "
                "can be managed consistently across teams and locations.",
                priority="High",
                priority_rationale="Access control is an explicit administrative need.",
                source_documents=["email.eml"],
                evidence=["permissions through roles"],
            ),
        ]
        output = render_requirements_document(
            requirements, [], ["interview.txt", "email.eml"]
        )
        self.assertIn("### REQ-001", output)
        self.assertIn("### REQ-002", output)
        self.assertIn("`interview.txt`", output)
        self.assertIn("Requirement priority scale", output)
        self.assertIn("Discarded / conflicting proposals", output)

    def test_render_rejects_unknown_source(self):
        req = Requirement(
            name="Untraceable",
            category="Functional",
            statement="The system must do something.",
            explanation="This requirement has a description long enough to pass validation.",
            priority="Low",
            priority_rationale="No evidence.",
            source_documents=["missing.txt"],
            evidence=["an excerpt"],
        )
        with self.assertRaisesRegex(ValueError, "unknown documents"):
            render_requirements_document([req], [], ["known.txt"])

    def test_chunking_rejects_invalid_overlap(self):
        with self.assertRaises(ValueError):
            chunk_document(
                SourceDocument(source_id="source.txt", text="text"),
                max_chars=10,
                overlap=10,
            )

    def test_consolidation_batches_run_concurrently(self):
        candidates = [
            requirement(
                f"Requirement {index}",
                "brief.txt",
                f"The system must support feature number {index}.",
            )
            for index in range(157)
        ]
        model = ConcurrentConsolidator()

        consolidated, discarded = _consolidate(model, candidates)

        self.assertEqual(model.calls, 4)
        self.assertEqual(len(consolidated), len(candidates))
        self.assertEqual(discarded, [])

    def test_graph_refines_audit_omission(self):
        auditor = FakeAuditor()
        workflow = build_workflow(
            extractor=FakeExtractor(),
            consolidator=FakeConsolidator(),
            auditor=auditor,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "sources"
            input_dir.mkdir()
            (input_dir / "brief.txt").write_text("Reports are needed.", encoding="utf-8")
            output_path = root / "requirements.md"

            workflow.invoke(
                {"input_dir": str(input_dir), "output_path": str(output_path)}
            )

            output = output_path.read_text(encoding="utf-8")
        self.assertEqual(auditor.calls, 2)
        self.assertIn("Basic reporting", output)
        self.assertIn("CSV export", output)
        self.assertIn("brief.txt", output)


if __name__ == "__main__":
    unittest.main()
