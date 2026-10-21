import json
import tempfile
import unittest
from pathlib import Path

from requirements_agent import (
    Audit,
    Consolidation,
    Discarded,
    Extraction,
    Requirement,
    bind_discarded_sources,
    build_graph,
    deduplicate_blacklist,
    load_sources,
    merge_exact_duplicates,
    render,
    split_source,
)


def req(name, source, statement):
    return Requirement(
        name=name,
        statement=statement,
        explanation=(
            "The system should provide this capability to staff. "
            "The behavior must remain consistent across library locations."
        ),
        category="Functional",
        priority="High",
        priority_reason="Stakeholders identify this as an operational need.",
        sources=[source],
        evidence=[statement],
    )


class FakeExtractor:
    def invoke(self, messages):
        source = messages[1][1].splitlines()[0].removeprefix("Source: ")
        return Extraction(
            requirements=[
                req(
                    "Report access",
                    "invented-name.txt",
                    "The system must allow staff to run authorized reports.",
                )
            ]
        )


class FakeConsolidator:
    def invoke(self, messages):
        candidates = json.loads(messages[1][1])
        return Consolidation(
            requirements=[Requirement.model_validate(item) for item in candidates]
        )


class FakeAuditor:
    def __init__(self):
        self.source_reviews = 0
        self.global_reviewed = False

    def invoke(self, messages):
        if "Complete requirements:" in messages[1][1]:
            self.global_reviewed = True
            return Audit(consistency_issues=["Resolve any remaining scope ambiguity."])
        self.source_reviews += 1
        if self.source_reviews == 1:
            source = messages[1][1].splitlines()[0].removeprefix("Exact source path: ")
            return Audit(
                missing=[
                    req(
                        "CSV exports",
                        "invented-source.txt",
                        "The system must export reports as CSV.",
                    )
                ],
                discarded=[
                    Discarded(
                        name="Nonsensical proposal",
                        proposal="unsupported proposal",
                        reason_type="nonsensical",
                        reason="It has no defined system behavior.",
                        sources=["wrong-source.txt"],
                        evidence=["unsupported proposal"],
                    )
                ],
            )
        return Audit()


class RequirementsWorkflowTests(unittest.TestCase):
    def test_merges_identical_statements_with_different_names(self):
        first = req(
            "Report access",
            "reports.txt",
            "The system must allow staff to run authorized reports.",
        )
        second = req(
            "Authorized report execution",
            "permissions.txt",
            "The system must allow staff to run authorized reports.",
        )

        merged = merge_exact_duplicates([first, second])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].sources, ["permissions.txt", "reports.txt"])
        self.assertEqual(merged[0].evidence, [first.statement])

    def test_blacklist_source_is_mapped_from_evidence_not_model_filename(self):
        source = {
            "name": "real.txt",
            "text": "Staff must not receive unauthorized account information.",
        }
        item = Discarded(
            name="Unauthorized data access",
            proposal="Staff must not receive unauthorized account information.",
            reason_type="conflict",
            reason="It conflicts with the access restrictions.",
            sources=["invented.txt"],
            evidence=["unauthorized account information"],
        )

        bound = bind_discarded_sources([item], [source])

        self.assertEqual(bound[0].sources, ["real.txt"])

    def test_excludes_blacklist_without_source_supported_proposal(self):
        sources = [
            {
                "name": "minutes.txt",
                "text": "The group discussed reports and multiple output formats.",
            }
        ]
        item = Discarded(
            name="Excel-only output",
            proposal="All reports must be generated in Excel format only.",
            reason_type="conflict",
            reason="This would restrict output formats.",
            sources=["minutes.txt"],
            evidence=["No mention of Excel-only output in the minutes."],
        )

        self.assertEqual(bind_discarded_sources([item], sources), [])

    def test_excludes_blacklist_candidate_that_duplicates_a_requirement(self):
        source = {
            "name": "reports.txt",
            "text": "The system must allow staff to run authorized reports.",
        }
        requirement = req(
            "Authorized reports",
            "reports.txt",
            "The system must allow staff to run authorized reports.",
        )
        item = Discarded(
            name="Authorized reports",
            proposal="The system must allow staff to run authorized reports.",
            reason_type="conflict",
            reason="Duplicate of a retained requirement.",
            sources=["reports.txt"],
            evidence=["The system must allow staff to run authorized reports."],
        )

        self.assertEqual(
            bind_discarded_sources([item], [source], [requirement]), []
        )

    def test_blacklist_deduplication_uses_proposal_not_display_name(self):
        first = Discarded(
            name="Rejected proposal",
            proposal="The system shall delete all records without authorization.",
            reason_type="nonsensical",
            reason="The proposal has no authorized scope.",
            sources=["deletion.txt"],
            evidence=["delete all records without authorization"],
        )
        second = Discarded(
            name="Rejected proposal",
            proposal="The system shall permanently remove transaction history.",
            reason_type="conflict",
            reason="It conflicts with the retention rule.",
            sources=["retention.txt"],
            evidence=["permanently remove transaction history"],
        )

        self.assertEqual(len(deduplicate_blacklist([first, second])), 2)

    def test_loads_nested_text_and_email_documents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "nested").mkdir()
            (root / "nested" / "a.txt").write_text("Text source", encoding="utf-8")
            (root / "mail.eml").write_text(
                "From: librarian@example.test\nSubject: Reports\n\nNeed CSV reports.",
                encoding="utf-8",
            )
            sources = load_sources(root)

        self.assertEqual([item["name"] for item in sources], ["mail.eml", "nested/a.txt"])
        self.assertIn("Need CSV reports.", sources[0]["text"])

    def test_split_source_preserves_source_across_chunks(self):
        long_source = {"name": "notes.txt", "text": ("A paragraph.\n\n" * 1000)}
        chunks = split_source(long_source)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk["source"] == "notes.txt" for chunk in chunks))
        self.assertTrue(all(chunk["text"] for chunk in chunks))

    def test_render_has_unique_ids_priority_scale_paragraph_and_blacklist(self):
        requirement = req(
            "Report access",
            "access.txt",
            "The system must allow staff to run authorized reports.",
        )
        discarded = Discarded(
            name="Unsafe public report access",
            proposal="Only authorized staff may access reports.",
            reason_type="conflict",
            reason="It conflicts with the explicitly required role permissions.",
            sources=["access.txt"],
            evidence=["Only authorized staff may access reports."],
        )
        document = render(
            [requirement, requirement],
            [discarded],
            ["access.txt"],
            ["Clarify which staff roles can export financial reports."],
        )

        self.assertEqual(document.count("### REQ-"), 1)
        self.assertIn("## Priority scale", document)
        self.assertIn("**Functional | High**", document)
        self.assertIn("The system should provide this capability to staff.", document)
        self.assertIn("## Blacklist: conflicting or nonsensical candidates", document)
        self.assertIn("**Rejected candidate:** Only authorized staff may access reports.", document)
        self.assertIn("**Reason:** conflict -", document)
        self.assertIn("**Evidence:** Only authorized staff may access reports.", document)
        self.assertIn("**Trace:** `access.txt`", document)
        self.assertIn("Clarify which staff roles", document)

    def test_graph_runs_completeness_refinement_and_consistency_review(self):
        auditor = FakeAuditor()
        graph = build_graph(FakeExtractor(), FakeConsolidator(), auditor)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_dir = root / "source"
            input_dir.mkdir()
            (input_dir / "needs.txt").write_text(
                "Staff need authorized reports and CSV export.", encoding="utf-8"
            )
            output = root / "requirements.md"

            graph.invoke({"input_dir": str(input_dir), "output": str(output)})
            result = output.read_text(encoding="utf-8")

        self.assertEqual(auditor.source_reviews, 2)
        self.assertTrue(auditor.global_reviewed)
        self.assertIn("### REQ-001", result)
        self.assertIn("Report access", result)
        self.assertIn("CSV exports", result)
        self.assertIn("**Trace:** `needs.txt`", result)
        self.assertNotIn("Nonsensical proposal", result)
        self.assertNotIn("invented-name.txt", result)
        self.assertNotIn("invented-source.txt", result)
        self.assertNotIn("wrong-source.txt", result)
        self.assertIn("Resolve any remaining scope ambiguity.", result)


if __name__ == "__main__":
    unittest.main()
