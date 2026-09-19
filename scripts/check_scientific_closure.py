#!/usr/bin/env python3
"""Validador material de la gobernanza de cierre científico.

Solo inspecciona documentación y configuración versionadas. No importa runners,
no abre datos y no crea artefactos de campaña.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path


ALLOWED_STATES = {
    "PLANNED",
    "APPROVED",
    "IN_PROGRESS",
    "REVIEW",
    "PASS",
    "FAIL",
    "BLOCKED",
    "NOT_APPLICABLE",
}
EDGES = {
    "PLANNED": {"APPROVED", "BLOCKED", "NOT_APPLICABLE"},
    "APPROVED": {"IN_PROGRESS", "BLOCKED"},
    "IN_PROGRESS": {"REVIEW", "BLOCKED"},
    "REVIEW": {"PASS", "FAIL", "BLOCKED"},
    "FAIL": {"IN_PROGRESS", "BLOCKED"},
    "BLOCKED": {"APPROVED"},
    "PASS": {"BLOCKED"},
    "NOT_APPLICABLE": {"BLOCKED"},
}
REQUIRED_AGENTS = {
    "scientific_explorer": ("gpt-5.6-terra", "medium", "read-only"),
    "scientific_implementer": ("gpt-5.6", "medium", "workspace-write"),
    "scientific_critic": ("gpt-5.6", "high", "read-only"),
    "scientific_auditor": ("gpt-5.6", "xhigh", "read-only"),
    "evidence_checker": ("gpt-5.6-luna", "low", "read-only"),
}
PROPOSAL_HEADINGS = {
    "Dependencias",
    "Archivos autorizados",
    "Archivos excluidos",
    "Tareas y pruebas",
    "Evidencia esperada",
    "Aceptación",
    "Bloqueo",
    "Riesgos",
    "Rollback",
}


class ClosureChecker:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.gov = self.root / "openspec/scientific-closure"
        self.errors: list[str] = []
        self.requirements: list[dict] = []
        self.changes: list[dict] = []

    def error(self, code: str, message: str) -> None:
        self.errors.append(f"{code}: {message}")

    def read_text(self, relative: str) -> str:
        path = self.root / relative
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self.error("FILE", f"{relative}: {exc}")
            return ""

    def read_json(self, relative: str) -> dict:
        text = self.read_text(relative)
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            self.error("JSON", f"{relative}: {exc}")
            return {}
        if not isinstance(value, dict):
            self.error("JSON", f"{relative}: la raíz debe ser un objeto")
            return {}
        return value

    def run(self) -> list[str]:
        required = self.read_json("openspec/scientific-closure/requirements.json")
        changes = self.read_json("openspec/scientific-closure/changes.json")
        self.requirements = required.get("requirements", [])
        self.changes = changes.get("changes", [])
        if not isinstance(self.requirements, list):
            self.error("REQ-SCHEMA", "requirements debe ser una lista")
            self.requirements = []
        if not isinstance(self.changes, list):
            self.error("CHANGE-SCHEMA", "changes debe ser una lista")
            self.changes = []
        self.check_requirements()
        self.check_changes()
        self.check_agents()
        self.check_links()
        self.check_runbook()
        return self.errors

    def check_requirements(self) -> None:
        spec = self.read_text("openspec/specs/scientific-closure/spec.md")
        matrix = self.read_text("openspec/scientific-closure/traceability.md")
        ids = [r.get("id") for r in self.requirements if isinstance(r, dict)]
        if len(ids) != len(set(ids)):
            self.error("REQ-ID", "hay identificadores de requisito duplicados")
        expected = {f"SC-GOV-{number:03}" for number in range(1, 26)}
        if set(ids) != expected:
            self.error("REQ-ID", f"se esperaban SC-GOV-001..025; observados={sorted(set(ids))}")
        evidence_paths: list[str] = []
        for requirement in self.requirements:
            if not isinstance(requirement, dict):
                self.error("REQ-SCHEMA", "cada requisito debe ser un objeto")
                continue
            rid = requirement.get("id", "<sin-id>")
            for field in ("title", "norm", "acceptance", "change", "task", "check", "evidence"):
                value = requirement.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error("REQ-FIELD", f"{rid}: falta {field}")
            if not isinstance(requirement.get("acceptance"), str) or not requirement.get("acceptance", "").strip():
                continue
            if spec.count(f"### Requirement: {rid} ") != 1:
                self.error("SPEC", f"{rid}: debe aparecer una vez en la spec")
            if f"#### Scenario: {rid} " not in spec:
                self.error("SPEC", f"{rid}: falta escenario")
            if requirement["acceptance"] not in spec:
                self.error("SPEC", f"{rid}: acceptance no coincide con la spec")
            if matrix.count(f"| {rid} |") != 1:
                self.error("MATRIX", f"{rid}: debe aparecer una vez en trazabilidad")
            expected_cells = (
                f"{requirement.get('change')} / {requirement.get('task')}",
                requirement.get("check", ""),
                requirement.get("evidence", ""),
            )
            row = next((line for line in matrix.splitlines() if line.startswith(f"| {rid} |")), "")
            for cell in expected_cells:
                if cell and cell not in row:
                    self.error("MATRIX", f"{rid}: fila no contiene {cell!r}")
            change = requirement.get("change", "")
            task_file = self.root / "openspec/changes" / change / "tasks.md"
            if not task_file.is_file():
                self.error("TASK", f"{rid}: no existe {task_file.relative_to(self.root)}")
            else:
                task_text = task_file.read_text(encoding="utf-8")
                if f"{requirement.get('task')} ({rid})" not in task_text:
                    self.error("TASK", f"{rid}: tarea no vinculada")
                if requirement.get("evidence", "") not in task_text:
                    self.error("TASK", f"{rid}: evidencia no vinculada")
            evidence = requirement.get("evidence")
            if isinstance(evidence, str):
                evidence_paths.append(evidence)
                path = Path(evidence)
                if path.is_absolute() or ".." in path.parts:
                    self.error("EVIDENCE", f"{rid}: ruta de evidencia insegura {evidence}")
        if len(evidence_paths) != len(set(evidence_paths)):
            self.error("EVIDENCE", "las rutas de evidencia deben ser únicas")

    def check_changes(self) -> None:
        mapping: dict[str, dict] = {}
        for change in self.changes:
            if not isinstance(change, dict):
                self.error("CHANGE-SCHEMA", "cada change debe ser un objeto")
                continue
            cid = change.get("id")
            if not isinstance(cid, str) or not cid:
                self.error("CHANGE-ID", "change sin id")
                continue
            if cid in mapping:
                self.error("CHANGE-ID", f"id duplicado: {cid}")
            mapping[cid] = change
        if len(mapping) != 10:
            self.error("CHANGE-ID", f"se esperaban 10 changes; observados={len(mapping)}")
        for cid, change in mapping.items():
            self.check_change_files(cid, change)
            self.check_state(cid, change)
            deps = change.get("deps")
            if not isinstance(deps, list):
                self.error("DEPS", f"{cid}: deps debe ser lista")
                continue
            for dep in deps:
                if dep not in mapping:
                    self.error("DEPS", f"{cid}: dependencia inexistente {dep}")
            if change.get("status") in {"IN_PROGRESS", "REVIEW", "PASS", "FAIL"}:
                unmet = [dep for dep in deps if mapping.get(dep, {}).get("status") != "PASS"]
                if unmet:
                    self.error("DEPS-GATE", f"{cid}: avanzó con dependencias sin PASS: {unmet}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(cid: str) -> None:
            if cid in visiting:
                self.error("DEPS-CYCLE", f"ciclo detectado en {cid}")
                return
            if cid in visited or cid not in mapping:
                return
            visiting.add(cid)
            for dep in mapping[cid].get("deps", []):
                visit(dep)
            visiting.remove(cid)
            visited.add(cid)

        for cid in mapping:
            visit(cid)
        expected_deps = {
            "sc-04-stage-b": ["sc-03-stage-a"],
            "sc-05-stage-c": ["sc-04-stage-b"],
        }
        for cid, deps in expected_deps.items():
            if mapping.get(cid, {}).get("deps") != deps:
                self.error("ABC", f"{cid}: dependencias A→B→C inválidas")
        gates = {cid: str(change.get("extra_gate", "")) for cid, change in mapping.items()}
        for cid, token in (
            ("sc-03-stage-a", "authorization A recorded"),
            ("sc-04-stage-b", "NO_VALID_SELECTION blocks B"),
            ("sc-05-stage-c", "CANDIDATE_NOT_VALIDATED blocks C"),
        ):
            if token not in gates.get(cid, ""):
                self.error("ABC-GATE", f"{cid}: falta gate {token!r}")

    def check_change_files(self, cid: str, change: dict) -> None:
        folder = self.root / "openspec/changes" / cid
        proposal = folder / "proposal.md"
        tasks = folder / "tasks.md"
        delta = folder / "specs/scientific-closure/spec.md"
        for path in (proposal, tasks, delta):
            if not path.is_file():
                self.error("OPEN-SPEC", f"{cid}: falta {path.relative_to(self.root)}")
        if proposal.is_file():
            text = proposal.read_text(encoding="utf-8")
            for heading in PROPOSAL_HEADINGS:
                if f"## {heading}" not in text:
                    self.error("OPEN-SPEC", f"{cid}: falta sección {heading}")
            acceptance = change.get("accept")
            if isinstance(acceptance, str) and acceptance not in text:
                self.error("CONSISTENCY", f"{cid}: aceptación diverge de changes.json")
        if delta.is_file():
            text = delta.read_text(encoding="utf-8")
            if "## ADDED Requirements" not in text or "#### Scenario:" not in text:
                self.error("OPEN-SPEC", f"{cid}: delta incompleto")
        tests = change.get("tests", [])
        paths = change.get("paths", [])
        if not isinstance(tests, list) or not isinstance(paths, list):
            self.error("CHANGE-SCHEMA", f"{cid}: tests/paths deben ser listas")
            return
        for item in [*tests, *paths]:
            if not isinstance(item, str) or Path(item).is_absolute() or ".." in Path(item).parts:
                self.error("REFERENCE", f"{cid}: ruta inválida {item!r}")
        if not change.get("conditional"):
            for item in tests:
                if isinstance(item, str) and not (self.root / item).is_file():
                    self.error("REFERENCE", f"{cid}: test inexistente {item}")

    def check_state(self, cid: str, change: dict) -> None:
        status = change.get("status")
        if status not in ALLOWED_STATES:
            self.error("STATE", f"{cid}: estado no permitido {status!r}")
            return
        events = change.get("state_events")
        if not isinstance(events, list):
            self.error("STATE", f"{cid}: state_events debe ser lista")
            return
        previous = "PLANNED"
        for event in events:
            if not isinstance(event, dict):
                self.error("STATE", f"{cid}: evento no es objeto")
                continue
            missing = [key for key in ("from", "to", "actor", "timestamp_utc", "reason", "evidence") if not event.get(key)]
            if missing:
                self.error("STATE", f"{cid}: evento incompleto {missing}")
                continue
            if event["from"] != previous or event["to"] not in EDGES.get(previous, set()):
                self.error("STATE", f"{cid}: transición ilegal {event['from']}→{event['to']}")
            previous = event["to"]
        if previous != status:
            self.error("STATE", f"{cid}: cadena termina en {previous}, registro dice {status}")
        approved = change.get("approved_for_implementation")
        scientific = change.get("scientific_execution_authorized")
        approval = change.get("approval")
        if not isinstance(approved, bool) or not isinstance(scientific, bool):
            self.error("APPROVAL", f"{cid}: flags de aprobación deben ser booleanos")
        approval_needed = status in {"APPROVED", "IN_PROGRESS", "REVIEW", "PASS"} or approved or scientific
        if approval_needed:
            if not isinstance(approval, dict) or any(not approval.get(key) for key in ("actor", "timestamp_utc", "scope", "source")):
                self.error("APPROVAL", f"{cid}: aprobación incompleta")
        elif approval is not None:
            self.error("APPROVAL", f"{cid}: aprobación contradictoria sin flags/estado")
        if status in {"APPROVED", "IN_PROGRESS", "REVIEW", "PASS"} and approved is not True:
            self.error("APPROVAL", f"{cid}: estado aprobado sin approved_for_implementation")
        if scientific and not approved:
            self.error("APPROVAL", f"{cid}: autorización científica sin implementación aprobada")
        if status == "PLANNED" and (approved or scientific):
            self.error("APPROVAL", f"{cid}: PLANNED no puede tener permisos activos")
        if status == "NOT_APPLICABLE" and not change.get("conditional"):
            self.error("STATE", f"{cid}: solo complementos pueden ser NOT_APPLICABLE")
        if status in {"PASS", "NOT_APPLICABLE"}:
            audit = change.get("audit")
            if not isinstance(audit, dict) or audit.get("verdict") != "PASS" or not audit.get("snapshot") or not audit.get("evidence"):
                self.error("AUDIT", f"{cid}: PASS/NOT_APPLICABLE requiere auditoría PASS identificada")

    def check_agents(self) -> None:
        config_path = self.root / ".codex/config.toml"
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            self.error("TOML", f".codex/config.toml: {exc}")
            config = {}
        agents_config = config.get("agents", {}) if isinstance(config, dict) else {}
        if agents_config.get("enabled") is not True:
            self.error("AGENT-CONFIG", "agents.enabled debe ser true")
        limit = agents_config.get("max_concurrent_threads_per_session")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 4:
            self.error("AGENT-CONFIG", "max_concurrent_threads_per_session debe estar entre 1 y 4")
        directory = self.root / ".codex/agents"
        observed: dict[str, tuple[str, str, str]] = {}
        for path in sorted(directory.glob("*.toml")):
            try:
                payload = tomllib.loads(path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                self.error("TOML", f"{path.relative_to(self.root)}: {exc}")
                continue
            name = payload.get("name")
            if name != path.stem:
                self.error("AGENT", f"{path.name}: name debe coincidir con el archivo")
            if name in observed:
                self.error("AGENT", f"agente duplicado {name}")
            if not str(payload.get("description", "")).strip() or not str(payload.get("developer_instructions", "")).strip():
                self.error("AGENT", f"{path.name}: description/instructions faltantes")
            observed[name] = (
                payload.get("model"),
                payload.get("model_reasoning_effort"),
                payload.get("sandbox_mode"),
            )
        if observed != REQUIRED_AGENTS:
            self.error("AGENT", f"perfiles/configuración inesperados: {observed}")

    def check_links(self) -> None:
        for path in self.gov.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                relative = link.split("#", 1)[0]
                if not relative:
                    continue
                target = (path.parent / relative).resolve()
                try:
                    target.relative_to(self.root)
                except ValueError:
                    self.error("LINK", f"{path.name}: enlace sale del repositorio: {link}")
                    continue
                if not target.exists():
                    self.error("LINK", f"{path.name}: enlace inexistente: {link}")

    def check_runbook(self) -> None:
        runbook = self.read_text("docs/research/scientific-closure-runbook.md")
        operations = self.read_text("openspec/scientific-closure/operations.md")
        required_runbook = (
            "## A, solo tras nueva autorización",
            "## B, solo tras autorización y A admisible",
            "## C, autorización adicional y B validada",
            "No ejecutar automáticamente A→B→C",
            "PREPARED_NOT_AUTHORIZED",
        )
        positions = [runbook.find(token) for token in required_runbook[:3]]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            self.error("RUNBOOK", "A/B/C faltan o no están ordenadas")
        for token in required_runbook[3:]:
            if token not in runbook:
                self.error("RUNBOOK", f"falta control {token!r}")
        for token in (
            "APPROVED → IN_PROGRESS requiere dependencias PASS",
            "READY_FOR_AUTONOMOUS_EXECUTION",
            "No push en esta sesión",
        ):
            if token not in operations:
                self.error("CONSISTENCY", f"operations.md carece de {token!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = ClosureChecker(args.root).run()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"scientific-closure checker: FAIL ({len(errors)} incumplimientos)", file=sys.stderr)
        return 1
    print("scientific-closure checker: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
