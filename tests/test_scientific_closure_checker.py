"""Pruebas positivas y negativas del checker formal; solo documentación."""

from __future__ import annotations

import copy
import hashlib
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

    def runtime_evidence(self) -> dict:
        agents = []
        for index, (name, (model, effort, sandbox)) in enumerate(CHECKER.REQUIRED_AGENTS.items()):
            profile = {
                "model": model,
                "reasoning_effort": effort,
                "sandbox_mode": sandbox,
            }
            agents.append(
                {
                    "name": name,
                    "configured": profile,
                    "effective": copy.deepcopy(profile),
                    "session_id": f"session-{index}",
                    "observed_at_utc": "2026-09-19T12:00:00Z",
                    "load_status": "loaded",
                    "sandbox_status": "enforced",
                    "observation": {
                        "command": f"inspect {name}",
                        "exit_code": 0,
                        "output_sha256": f"{index + 1:064x}",
                    },
                }
            )
        return {
            "schema_version": "runtime-agent-capabilities/v1",
            "collected_at_utc": "2026-09-19T12:00:00Z",
            "collector": {
                "session_id": "collector-session",
                "command": "collect capabilities",
                "exit_code": 0,
                "output_sha256": "f" * 64,
            },
            "agents": agents,
        }

    def write_runtime_evidence(self, payload: dict | str) -> Path:
        temp = Path(tempfile.mkdtemp(prefix="runtime-evidence-"))
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        path = temp / "agent-capabilities.json"
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            payload = copy.deepcopy(payload)
            payload["configuration_sha256"] = CHECKER.ClosureChecker.configuration_sha256(ROOT)
            observations = [("collector.out", payload.get("collector"))]
            agents = payload.get("agents")
            if isinstance(agents, list):
                observations.extend(
                    (f"agent-{index}.out", agent.get("observation"))
                    for index, agent in enumerate(agents)
                    if isinstance(agent, dict)
                )
            for name, observation in observations:
                if not isinstance(observation, dict):
                    continue
                raw = ("captured output " + name).encode("utf-8")
                (temp / name).write_bytes(raw)
                observation["output_path"] = name
                observation["output_sha256"] = hashlib.sha256(raw).hexdigest()
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def assert_runtime_error(self, payload: dict | str, code: str) -> None:
        path = self.write_runtime_evidence(payload)
        errors = CHECKER.ClosureChecker(ROOT, runtime_evidence=path).run()
        self.assertTrue(any(error.startswith(code + ":") for error in errors), errors)

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
        self.assertIn("runtime no verificado", completed.stdout)

    def test_runtime_evidence_passes_api_and_cli(self):
        path = self.write_runtime_evidence(self.runtime_evidence())
        checker = CHECKER.ClosureChecker(ROOT, runtime_evidence=path)
        self.assertEqual(checker.run(), [])
        self.assertEqual(checker.runtime_evidence_assurance, "referenced-evidence-consistency")
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(ROOT), "--runtime-evidence", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("no autoriza ejecución ni acredita readiness", completed.stdout)

    def test_runtime_evidence_explicit_model_substitution_passes(self):
        payload = self.runtime_evidence()
        agent = next(item for item in payload["agents"] if item["name"] == "scientific_implementer")
        agent["effective"]["model"] = "gpt-5.6-sol"
        agent["substitution"] = {
            "requested_model": "gpt-5.6",
            "requested_reasoning_effort": "medium",
            "effective_model": "gpt-5.6-sol",
            "effective_reasoning_effort": "medium",
            "reason": "backend rejected requested role before execution",
            "source": "orchestrator session report",
        }
        path = self.write_runtime_evidence(payload)
        self.assertEqual(CHECKER.ClosureChecker(ROOT, runtime_evidence=path).run(), [])

    def test_runtime_evidence_missing_fails(self):
        missing = ROOT / "does-not-exist-agent-capabilities.json"
        errors = CHECKER.ClosureChecker(ROOT, runtime_evidence=missing).run()
        self.assertTrue(any(error.startswith("RUNTIME-EVIDENCE:") for error in errors), errors)

    def test_runtime_evidence_malformed_fails(self):
        self.assert_runtime_error("{not-json", "RUNTIME-EVIDENCE")

    def test_runtime_evidence_schema_fails(self):
        payload = self.runtime_evidence()
        payload["schema_version"] = "runtime-agent-capabilities/v0"
        self.assert_runtime_error(payload, "SCHEMA")

    def test_runtime_evidence_missing_role_fails(self):
        payload = self.runtime_evidence()
        payload["agents"].pop()
        self.assert_runtime_error(payload, "ROLE")

    def test_runtime_evidence_duplicate_role_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][-1]["name"] = payload["agents"][0]["name"]
        self.assert_runtime_error(payload, "ROLE")

    def test_runtime_evidence_non_string_role_fails_without_exception(self):
        payload = self.runtime_evidence()
        payload["agents"][0]["name"] = ["scientific_explorer"]
        self.assert_runtime_error(payload, "ROLE")

    def test_runtime_evidence_config_divergence_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][0]["configured"]["model"] = "other-model"
        self.assert_runtime_error(payload, "CONFIG")

    def test_runtime_evidence_effective_divergence_without_substitution_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][0]["effective"]["model"] = "replacement-model"
        self.assert_runtime_error(payload, "SUBSTITUTION")

    def test_runtime_evidence_inconsistent_substitution_fails(self):
        payload = self.runtime_evidence()
        agent = payload["agents"][0]
        agent["effective"]["model"] = "replacement-model"
        agent["substitution"] = {
            "requested_model": agent["configured"]["model"],
            "requested_reasoning_effort": agent["configured"]["reasoning_effort"],
            "effective_model": "wrong-model",
            "effective_reasoning_effort": agent["effective"]["reasoning_effort"],
            "reason": "backend rejected requested role",
            "source": "session report",
        }
        self.assert_runtime_error(payload, "SUBSTITUTION")

    def test_runtime_evidence_sandbox_not_enforced_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][0]["sandbox_status"] = "requested"
        self.assert_runtime_error(payload, "SANDBOX")

    def test_runtime_evidence_load_not_loaded_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][0]["load_status"] = "unknown"
        self.assert_runtime_error(payload, "EFFECTIVE")

    def test_runtime_evidence_nonzero_exit_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][0]["observation"]["exit_code"] = 1
        self.assert_runtime_error(payload, "EFFECTIVE")

    def test_runtime_evidence_duplicate_session_fails(self):
        payload = self.runtime_evidence()
        payload["agents"][1]["session_id"] = payload["agents"][0]["session_id"]
        self.assert_runtime_error(payload, "ROLE")

    def test_runtime_evidence_configuration_digest_and_replay_fail(self):
        payload = self.runtime_evidence()
        path = self.write_runtime_evidence(payload)
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved["configuration_sha256"] = "0" * 64
        path.write_text(json.dumps(saved), encoding="utf-8")
        errors = CHECKER.ClosureChecker(ROOT, runtime_evidence=path).run()
        self.assertTrue(any(error.startswith("RUNTIME-EVIDENCE:") for error in errors), errors)

    def test_runtime_evidence_missing_forged_and_escape_output_fail(self):
        for output_path, output_hash in (
            ("missing.out", "0" * 64),
            ("../escape.out", "0" * 64),
        ):
            payload = self.runtime_evidence()
            path = self.write_runtime_evidence(payload)
            saved = json.loads(path.read_text(encoding="utf-8"))
            saved["collector"]["output_path"] = output_path
            saved["collector"]["output_sha256"] = output_hash
            path.write_text(json.dumps(saved), encoding="utf-8")
            errors = CHECKER.ClosureChecker(ROOT, runtime_evidence=path).run()
            self.assertTrue(any(error.startswith("RUNTIME-EVIDENCE:") for error in errors), errors)

    def test_json_wrong_types_fail_without_exception(self):
        mutations = (
            ("openspec/scientific-closure/requirements.json", lambda p: p["requirements"][0].__setitem__("id", []), "REQ-ID"),
            ("openspec/scientific-closure/changes.json", lambda p: p["changes"][0].__setitem__("deps", None), "DEPS"),
            ("openspec/scientific-closure/changes.json", lambda p: p["changes"][0].__setitem__("deps", [{}]), "DEPS"),
            ("openspec/scientific-closure/changes.json", lambda p: p["changes"][0].__setitem__("status", []), "STATE"),
            ("openspec/scientific-closure/changes.json", lambda p: p["changes"][0].__setitem__("state_events", ["truthy"]), "STATE"),
            ("openspec/scientific-closure/changes.json", lambda p: p["changes"][0].__setitem__("approval", "truthy"), "APPROVAL"),
            ("openspec/scientific-closure/changes.json", lambda p: p["changes"][0].__setitem__("audit", "truthy"), "AUDIT"),
        )
        for relative, mutate, code in mutations:
            with self.subTest(relative=relative, code=code):
                root = self.make_fixture()
                payload = self.load(root, relative)
                mutate(payload)
                self.save(root, relative, payload)
                self.assert_error(root, code)

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

    def test_title_norm_and_check_must_match_spec(self):
        for field in ("title", "norm", "check"):
            with self.subTest(field=field):
                root = self.make_fixture()
                payload = self.load(root, "openspec/scientific-closure/requirements.json")
                payload["requirements"][0][field] += " alterado"
                self.save(root, "openspec/scientific-closure/requirements.json", payload)
                self.assert_error(root, "SPEC")

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
