"""Pruebas positivas y negativas del checker formal; solo documentación."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_scientific_closure.py"
SPEC = importlib.util.spec_from_file_location("scientific_closure_checker", SCRIPT)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


class CheckerTests(unittest.TestCase):
    def make_fixture(self) -> Path:
        temp = Path(tempfile.mkdtemp(prefix="scientific-closure-checker-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        for source in (
            ROOT / "openspec/scientific-closure",
            ROOT / "openspec/specs/scientific-closure",
            ROOT / ".codex",
        ):
            shutil.copytree(source, temp / source.relative_to(ROOT))
        for change in (ROOT / "openspec/changes").glob("sc-*"):
            shutil.copytree(change, temp / change.relative_to(ROOT))
        runbook = ROOT / "docs/research/scientific-closure-runbook.md"
        destination = temp / runbook.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runbook, destination)
        for change in self.load(temp, "openspec/scientific-closure/changes.json")["changes"]:
            for item in [*change["tests"], *change["paths"]]:
                if change["conditional"]:
                    continue
                path = temp / item
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)
        return temp

    @staticmethod
    def load(root: Path, relative: str) -> dict:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    @staticmethod
    def save(root: Path, relative: str, payload: dict) -> None:
        (root / relative).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def assert_error(self, root: Path, code: str) -> None:
        errors = CHECKER.ClosureChecker(root).run()
        self.assertTrue(any(error.startswith(code + ":") for error in errors), errors)

    def test_repository_passes(self):
        self.assertEqual(CHECKER.ClosureChecker(ROOT).run(), [])
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(ROOT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_duplicate_requirement_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/requirements.json")
        payload["requirements"][1]["id"] = payload["requirements"][0]["id"]
        self.save(root, "openspec/scientific-closure/requirements.json", payload)
        self.assert_error(root, "REQ-ID")

    def test_missing_acceptance_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/requirements.json")
        payload["requirements"][0]["acceptance"] = ""
        self.save(root, "openspec/scientific-closure/requirements.json", payload)
        self.assert_error(root, "REQ-FIELD")

    def test_matrix_mismatch_fails(self):
        root = self.make_fixture()
        path = root / "openspec/scientific-closure/traceability.md"
        path.write_text(path.read_text(encoding="utf-8").replace("| SC-GOV-001 |", "| SC-GOV-999 |", 1), encoding="utf-8")
        self.assert_error(root, "MATRIX")

    def test_missing_dependency_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        payload["changes"][1]["deps"] = ["sc-does-not-exist"]
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "DEPS")

    def test_dependency_cycle_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        payload["changes"][0]["deps"] = [payload["changes"][1]["id"]]
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "DEPS-CYCLE")

    def test_unknown_status_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        payload["changes"][0]["status"] = "GREEN"
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "STATE")

    def test_contradictory_scientific_approval_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        payload["changes"][0]["scientific_execution_authorized"] = True
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "APPROVAL")

    def test_b_cannot_advance_without_a_pass(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        stage_b = next(item for item in payload["changes"] if item["id"] == "sc-04-stage-b")
        stage_b.update(
            status="IN_PROGRESS",
            approved_for_implementation=True,
            approval={"actor": "fixture", "timestamp_utc": "2000-01-01T00:00:00Z", "scope": "fixture", "source": "fixture"},
            state_events=[
                {"from": "PLANNED", "to": "APPROVED", "actor": "fixture", "timestamp_utc": "2000-01-01T00:00:00Z", "reason": "fixture", "evidence": "fixture"},
                {"from": "APPROVED", "to": "IN_PROGRESS", "actor": "fixture", "timestamp_utc": "2000-01-01T00:00:01Z", "reason": "fixture", "evidence": "fixture"},
            ],
        )
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "DEPS-GATE")

    def test_missing_stage_gate_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        stage_c = next(item for item in payload["changes"] if item["id"] == "sc-05-stage-c")
        stage_c["extra_gate"] = "allow everything"
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "ABC-GATE")

    def test_invalid_agent_toml_fails(self):
        root = self.make_fixture()
        path = root / ".codex/agents/scientific_explorer.toml"
        path.write_text("name = [invalid", encoding="utf-8")
        self.assert_error(root, "TOML")

    def test_missing_agent_fails(self):
        root = self.make_fixture()
        (root / ".codex/agents/evidence_checker.toml").unlink()
        self.assert_error(root, "AGENT")

    def test_disabled_multiagent_fails(self):
        root = self.make_fixture()
        path = root / ".codex/config.toml"
        path.write_text(path.read_text(encoding="utf-8").replace("enabled = true", "enabled = false"), encoding="utf-8")
        self.assert_error(root, "AGENT-CONFIG")

    def test_invalid_reference_fails(self):
        root = self.make_fixture()
        payload = self.load(root, "openspec/scientific-closure/changes.json")
        payload["changes"][0]["paths"].append("../escape")
        self.save(root, "openspec/scientific-closure/changes.json", payload)
        self.assert_error(root, "REFERENCE")


if __name__ == "__main__":
    unittest.main()
