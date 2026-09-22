"""Document checks only: no runner imports, datasets or scientific results."""

import copy
import json
import re
import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
GOV = ROOT / "openspec/scientific-closure"


def validate_state(change):
    """Reject invalid approvals and event chains without executing any task."""
    edges = {
        "PLANNED": {"APPROVED", "BLOCKED", "NOT_APPLICABLE"},
        "APPROVED": {"IN_PROGRESS", "BLOCKED"},
        "IN_PROGRESS": {"REVIEW", "BLOCKED"},
        "REVIEW": {"PASS", "FAIL", "BLOCKED"},
        "FAIL": {"IN_PROGRESS", "BLOCKED"},
        "BLOCKED": {"APPROVED"},
        "PASS": {"BLOCKED"},
        "NOT_APPLICABLE": {"BLOCKED"},
    }

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    status = change["status"]
    require(status in edges, "unknown status")
    require(isinstance(change["state_events"], list), "events must be a list")
    previous = "PLANNED"
    for event in change["state_events"]:
        require(isinstance(event, dict), "event must be an object")
        require(
            all(
                event.get(k) for k in ("from", "to", "actor", "timestamp_utc", "reason", "evidence")
            ),
            "incomplete event",
        )
        require(event["from"] == previous, "broken event chain")
        require(event["to"] in edges[previous], "illegal transition")
        previous = event["to"]
    require(previous == status, "last event does not match status")
    approved_states = {"APPROVED", "IN_PROGRESS", "REVIEW", "PASS"}
    if status in approved_states:
        require(change["approved_for_implementation"] is True, "approval flag required")
    if (
        status in approved_states
        or change["approved_for_implementation"]
        or change["scientific_execution_authorized"]
    ):
        approval = change["approval"]
        require(isinstance(approval, dict), "approval record required")
        require(
            all(approval.get(k) for k in ("actor", "timestamp_utc", "scope", "source")),
            "incomplete approval",
        )
    if status == "NOT_APPLICABLE":
        require(change["conditional"] is True, "only conditional changes can be inapplicable")
        require(
            bool(change.get("applicability_decision")), "audited applicability decision required"
        )
    if status in {"PASS", "NOT_APPLICABLE"}:
        audit = change["audit"]
        require(isinstance(audit, dict), "audit required")
        require(audit.get("verdict") == "PASS", "auditor PASS required")
        require(
            bool(audit.get("snapshot")) and bool(audit.get("evidence")),
            "audit identity/evidence required",
        )


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.requirements = json.loads((GOV / "requirements.json").read_text(encoding="utf-8"))[
            "requirements"
        ]
        self.changes = json.loads((GOV / "changes.json").read_text(encoding="utf-8"))["changes"]

    def test_requirement_ids_and_fields(self):
        ids = [r["id"] for r in self.requirements]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {f"SC-GOV-{i:03}" for i in range(1, 26)})
        for r in self.requirements:
            for field in ("title", "norm", "acceptance", "change", "task", "check", "evidence"):
                self.assertTrue(r[field].strip(), (r["id"], field))

    def test_spec_matrix_tasks_are_consistent(self):
        spec = (ROOT / "openspec/specs/scientific-closure/spec.md").read_text(encoding="utf-8")
        matrix = (GOV / "traceability.md").read_text(encoding="utf-8")
        for r in self.requirements:
            self.assertEqual(spec.count(f"### Requirement: {r['id']} "), 1)
            self.assertIn(f"#### Scenario: {r['id']} ", spec)
            self.assertIn(r["acceptance"], spec)
            self.assertEqual(matrix.count(f"| {r['id']} |"), 1)
            tasks = (ROOT / "openspec/changes" / r["change"] / "tasks.md").read_text(
                encoding="utf-8"
            )
            self.assertIn(f"{r['task']} ({r['id']})", tasks)
            self.assertIn(r["evidence"], tasks)

    def test_change_contracts_and_no_authorization(self):
        self.assertEqual(len(self.changes), 10)
        for c in self.changes:
            folder = ROOT / "openspec/changes" / c["id"]
            proposal = (folder / "proposal.md").read_text(encoding="utf-8")
            for heading in (
                "Dependencias",
                "Archivos autorizados",
                "Archivos excluidos",
                "Tareas y pruebas",
                "Evidencia esperada",
                "Aceptación",
                "Bloqueo",
                "Riesgos",
                "Rollback",
            ):
                self.assertIn(f"## {heading}", proposal)
            delta = (folder / "specs/scientific-closure/spec.md").read_text(encoding="utf-8")
            self.assertIn("## ADDED Requirements", delta)
            self.assertIn("#### Scenario:", delta)
            validate_state(c)
            self.assertTrue(c["extra_gate"])
            self.assertIn("openspec/scientific-closure/changes.json", c["orchestrator_paths"])
            self.assertIsInstance(c["state_events"], list)

    def test_rejects_fake_approval_and_non_object_events(self):
        record = copy.deepcopy(self.changes[0])
        record.update(
            status="APPROVED", approved_for_implementation=False, approval=None, state_events=["x"]
        )
        with self.assertRaises(ValueError):
            validate_state(record)
        record["state_events"] = [self.event("PLANNED", "APPROVED")]
        with self.assertRaises(ValueError):
            validate_state(record)

    @staticmethod
    def event(start, end):
        # Synthetic metadata for document validation, not campaign evidence.
        return dict(
            from_=start,
            to=end,
            actor="fixture",
            timestamp_utc="2000-01-01T00:00:00Z",
            reason="fixture",
            evidence="fixture",
            **{"from": start},
        )

    def test_accepts_documented_approval_without_scientific_permission(self):
        record = copy.deepcopy(self.changes[0])
        record.update(
            status="APPROVED",
            approved_for_implementation=True,
            approval=dict(
                actor="fixture",
                timestamp_utc="2000-01-01T00:00:00Z",
                scope="preparation only",
                source="fixture",
            ),
            state_events=[self.event("PLANNED", "APPROVED")],
        )
        validate_state(record)
        self.assertFalse(record["scientific_execution_authorized"])

    def test_rejects_illegal_or_incomplete_event_chains(self):
        for events, status in [
            ([self.event("PLANNED", "PASS")], "PASS"),
            ([self.event("APPROVED", "IN_PROGRESS")], "IN_PROGRESS"),
            ([self.event("PLANNED", "BLOCKED")], "PLANNED"),
            ([{"from": "PLANNED", "to": "BLOCKED"}], "BLOCKED"),
        ]:
            with self.subTest(events=events):
                record = copy.deepcopy(self.changes[0])
                record.update(status=status, state_events=events)
                with self.assertRaises(ValueError):
                    validate_state(record)

    def test_not_applicable_is_not_a_shortcut_for_core_changes(self):
        record = copy.deepcopy(self.changes[0])
        record.update(
            status="NOT_APPLICABLE", state_events=[self.event("PLANNED", "NOT_APPLICABLE")]
        )
        with self.assertRaises(ValueError):
            validate_state(record)

    def test_pass_requires_independent_audit_evidence(self):
        record = copy.deepcopy(self.changes[0])
        record.update(
            status="PASS",
            approved_for_implementation=True,
            audit=None,
            approval=dict(
                actor="fixture",
                timestamp_utc="2000-01-01T00:00:00Z",
                scope="preparation only",
                source="fixture",
            ),
            state_events=[
                self.event("PLANNED", "APPROVED"),
                self.event("APPROVED", "IN_PROGRESS"),
                self.event("IN_PROGRESS", "REVIEW"),
                self.event("REVIEW", "PASS"),
            ],
        )
        with self.assertRaises(ValueError):
            validate_state(record)

    def test_dependencies_and_terminal_gate(self):
        graph = {c["id"]: c["deps"] for c in self.changes}
        self.assertEqual(len(graph), len(self.changes))

        def visit(key, ancestors):
            self.assertNotIn(key, ancestors)
            self.assertIn(key, graph)
            for dep in graph[key]:
                visit(dep, ancestors | {key})

        for key in graph:
            visit(key, set())
        self.assertEqual(graph["sc-04-stage-b"], ["sc-03-stage-a"])
        self.assertEqual(graph["sc-05-stage-c"], ["sc-04-stage-b"])
        gates = {c["id"]: c["extra_gate"] for c in self.changes}
        self.assertIn("NO_VALID_SELECTION blocks B", gates["sc-04-stage-b"])
        self.assertIn("CANDIDATE_NOT_VALIDATED blocks C", gates["sc-05-stage-c"])
        self.assertIn("authorization A recorded", gates["sc-03-stage-a"])
        for key in (
            "sc-07-aux-regression",
            "sc-08-aux-hitl",
            "sc-09-aux-anomalies",
            "sc-10-aux-robustness",
        ):
            self.assertIn("NOT_REQUIRED/UNRESOLVED blocks execution", gates[key])
        synthesis = next(c for c in self.changes if c["id"] == "sc-06-scientific-synthesis")
        self.assertIn("UNRESOLVED blocks closure", synthesis["extra_gate"])

    def test_auxiliaries_are_conditional(self):
        conditional = [c for c in self.changes if c["conditional"]]
        self.assertEqual(len(conditional), 4)
        for c in conditional:
            self.assertIn("REQUIRED", c["goal"])
            self.assertIn("NOT_REQUIRED", c["accept"])
            self.assertIn("sc-01-evidence-scope", c["deps"])

    def test_agents_toml_fields_models_and_permissions(self):
        expected = {
            "scientific_explorer": ("gpt-5.6-terra", "medium", "read-only"),
            "scientific_implementer": ("gpt-5.6-sol", "medium", "workspace-write"),
            "scientific_critic": ("gpt-5.6-sol", "high", "read-only"),
            "scientific_auditor": ("gpt-5.6-sol", "xhigh", "read-only"),
            "evidence_checker": ("gpt-5.6-luna", "low", "read-only"),
        }
        found = {}
        for path in (ROOT / ".codex/agents").glob("*.toml"):
            a = tomllib.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(a["name"], path.stem)
            self.assertNotIn(a["name"], found)
            self.assertTrue(a["description"].strip())
            self.assertIn("holdouts cerrados", a["developer_instructions"])
            found[a["name"]] = tuple(
                a[k] for k in ("model", "model_reasoning_effort", "sandbox_mode")
            )
        self.assertEqual(found, expected)

    def test_project_toml_concurrency(self):
        config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
        self.assertIs(config["agents"]["enabled"], True)
        self.assertEqual(config["agents"]["max_concurrent_threads_per_session"], 4)

    def test_document_links_resolve(self):
        for path in GOV.glob("*.md"):
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" in link or link.startswith("#"):
                    continue
                target = (path.parent / link.split("#")[0]).resolve()
                self.assertTrue(target.is_relative_to(ROOT), (path.name, link))
                self.assertTrue(target.exists(), (path.name, link))

    def test_existing_and_planned_paths(self):
        for c in self.changes:
            for path in c["tests"]:
                self.assertTrue(path.startswith("tests/"))
                if not c["conditional"]:
                    self.assertTrue((ROOT / path).is_file(), path)
            for path in c["paths"]:
                self.assertNotIn("..", Path(path).parts)
                self.assertFalse(path.startswith(("frontend/", "backend/", "data/")))
                if not c["conditional"]:
                    self.assertTrue((ROOT / path).is_file(), path)

    def test_evidence_paths_and_safe_resume(self):
        evidence = [r["evidence"] for r in self.requirements]
        self.assertEqual(len(evidence), len(set(evidence)))
        for path in evidence:
            self.assertFalse(Path(path).is_absolute())
            self.assertNotIn("..", Path(path).parts)
        prompt = (GOV / "next-session.txt").read_text(encoding="utf-8")
        self.assertIn("NO ejecutar científicamente A/B/C", prompt)
        self.assertIn("feat/scientific-closure", prompt)


if __name__ == "__main__":
    unittest.main()
