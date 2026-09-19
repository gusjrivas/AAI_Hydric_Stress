#!/usr/bin/env python3
"""Validador material de la gobernanza de cierre científico.

Solo inspecciona documentación y configuración versionadas. No importa runners,
no abre datos y no crea artefactos de campaña.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from pathlib import Path
from typing import Any


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
RUNTIME_SCHEMA_VERSION = "runtime-agent-capabilities/v1"
MAX_RUNTIME_EVIDENCE_BYTES = 1024 * 1024
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
HEX40_RE = re.compile(r"^[0-9a-fA-F]{40}$")
UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
SCIENTIFIC_EXECUTION_CHANGES = {
    "sc-03-stage-a",
    "sc-04-stage-b",
    "sc-05-stage-c",
    "sc-07-aux-regression",
    "sc-08-aux-hitl",
    "sc-09-aux-anomalies",
    "sc-10-aux-robustness",
}
CONFIGURATION_PATHS = (
    ".codex/config.toml",
    ".codex/agents/scientific_explorer.toml",
    ".codex/agents/scientific_implementer.toml",
    ".codex/agents/scientific_critic.toml",
    ".codex/agents/scientific_auditor.toml",
    ".codex/agents/evidence_checker.toml",
    "scripts/check_scientific_closure.py",
)


class ClosureChecker:
    def __init__(self, root: Path, runtime_evidence: Path | None = None):
        self.root = root.resolve()
        self.runtime_evidence = runtime_evidence
        self.gov = self.root / "openspec/scientific-closure"
        self.errors: list[str] = []
        self.requirements: list[dict] = []
        self.changes: list[dict] = []
        self.runtime_evidence_assurance = (
            "not-supplied" if runtime_evidence is None else "referenced-evidence-consistency"
        )
        self.reported_repository_commit: str | None = None

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
        if self.runtime_evidence is not None:
            self.check_runtime_evidence()
        self.check_links()
        self.check_runbook()
        return self.errors

    def check_requirements(self) -> None:
        spec = self.read_text("openspec/specs/scientific-closure/spec.md")
        matrix = self.read_text("openspec/scientific-closure/traceability.md")
        ids: list[str] = []
        for requirement in self.requirements:
            if isinstance(requirement, dict) and isinstance(requirement.get("id"), str):
                ids.append(requirement["id"])
            elif isinstance(requirement, dict):
                self.error("REQ-ID", "cada id de requisito debe ser string")
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
            fields_valid = True
            for field in ("title", "norm", "acceptance", "change", "task", "check", "evidence"):
                value = requirement.get(field)
                if not isinstance(value, str) or not value.strip():
                    self.error("REQ-FIELD", f"{rid}: falta {field}")
                    fields_valid = False
            if not fields_valid:
                continue
            if not isinstance(rid, str) or not rid.strip():
                continue
            if any(
                not isinstance(requirement.get(field), str) or not requirement[field].strip()
                for field in ("title", "norm", "acceptance", "check")
            ):
                continue
            title = requirement["title"]
            heading = f"### Requirement: {rid} {title}"
            heading_matches = list(re.finditer(rf"(?m)^{re.escape(heading)}$", spec))
            if len(heading_matches) != 1:
                self.error("SPEC", f"{rid}: header exacto debe aparecer una vez en la spec")
                section = ""
            else:
                start = heading_matches[0].end()
                next_heading = re.search(r"(?m)^### Requirement: ", spec[start:])
                end = start + next_heading.start() if next_heading else len(spec)
                section = spec[start:end]
            if f"#### Scenario: {rid} " not in spec:
                self.error("SPEC", f"{rid}: falta escenario")
            for field, label in (
                ("norm", "norm"),
                ("acceptance", "acceptance"),
                ("check", "check"),
            ):
                if requirement[field] not in section:
                    self.error("SPEC", f"{rid}: {label} no coincide con la spec")
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
            change = requirement.get("change")
            task = requirement.get("task")
            if not isinstance(change, str) or not isinstance(task, str):
                continue
            task_file = self.root / "openspec/changes" / change / "tasks.md"
            if not task_file.is_file():
                self.error("TASK", f"{rid}: no existe {task_file.relative_to(self.root)}")
            else:
                task_text = task_file.read_text(encoding="utf-8")
                if f"{task} ({rid})" not in task_text:
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
                if not isinstance(dep, str):
                    self.error("DEPS", f"{cid}: cada dependencia debe ser string")
                elif dep not in mapping:
                    self.error("DEPS", f"{cid}: dependencia inexistente {dep}")
            change_status = change.get("status")
            if isinstance(change_status, str) and change_status in {"IN_PROGRESS", "REVIEW", "PASS", "FAIL"}:
                unmet = [
                    dep for dep in deps
                    if isinstance(dep, str) and mapping.get(dep, {}).get("status") != "PASS"
                ]
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
            deps = mapping[cid].get("deps")
            if isinstance(deps, list):
                for dep in deps:
                    if isinstance(dep, str):
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
        if not isinstance(status, str) or status not in ALLOWED_STATES:
            self.error("STATE", f"{cid}: estado no permitido {status!r}")
            return
        events = change.get("state_events")
        if not isinstance(events, list):
            self.error("STATE", f"{cid}: state_events debe ser lista")
            return
        previous = "PLANNED"
        terminal_seen = False
        for event in events:
            if not isinstance(event, dict):
                self.error("STATE", f"{cid}: evento no es objeto")
                continue
            invalid = [
                key for key in ("from", "to", "actor", "reason", "evidence")
                if not self._is_nonempty_string(event.get(key))
            ]
            if invalid:
                self.error("STATE", f"{cid}: campos de evento deben ser strings no vacíos: {invalid}")
                continue
            self._check_timestamp(event.get("timestamp_utc"), f"{cid}.state_events.timestamp_utc")
            if event["from"] != previous or event["to"] not in EDGES.get(previous, set()):
                self.error("STATE", f"{cid}: transición ilegal {event['from']}→{event['to']}")
            previous = event["to"]
            terminal_seen = terminal_seen or previous in {"PASS", "NOT_APPLICABLE"}
        if previous != status:
            self.error("STATE", f"{cid}: cadena termina en {previous}, registro dice {status}")
        approved = change.get("approved_for_implementation")
        scientific = change.get("scientific_execution_authorized")
        approval = change.get("approval")
        if not isinstance(approved, bool) or not isinstance(scientific, bool):
            self.error("APPROVAL", f"{cid}: flags de aprobación deben ser booleanos")
        approval_needed = status in {"APPROVED", "IN_PROGRESS", "REVIEW", "PASS"} or approved or scientific
        if approval_needed:
            if not isinstance(approval, dict):
                self.error("APPROVAL", f"{cid}: aprobación incompleta")
            else:
                for key in ("actor", "scope", "source"):
                    if not self._is_nonempty_string(approval.get(key)):
                        self.error("APPROVAL", f"{cid}: approval.{key} debe ser string no vacío")
                self._check_timestamp(approval.get("timestamp_utc"), f"{cid}.approval.timestamp_utc")
        elif approval is not None:
            self.error("APPROVAL", f"{cid}: aprobación contradictoria sin flags/estado")
        if status in {"APPROVED", "IN_PROGRESS", "REVIEW", "PASS"} and approved is not True:
            self.error("APPROVAL", f"{cid}: estado aprobado sin approved_for_implementation")
        if scientific and not approved:
            self.error("APPROVAL", f"{cid}: autorización científica sin implementación aprobada")
        if scientific and cid not in SCIENTIFIC_EXECUTION_CHANGES:
            self.error("APPROVAL", f"{cid}: scientific_execution_authorized no está permitido")
        if status == "PLANNED" and (approved or scientific):
            self.error("APPROVAL", f"{cid}: PLANNED no puede tener permisos activos")
        if status == "NOT_APPLICABLE" and not change.get("conditional"):
            self.error("STATE", f"{cid}: solo complementos pueden ser NOT_APPLICABLE")
        audit = change.get("audit")
        if status in {"PASS", "NOT_APPLICABLE"} or terminal_seen:
            if not isinstance(audit, dict) or audit.get("verdict") != "PASS" or not self._is_nonempty_string(audit.get("snapshot")) or not self._is_nonempty_string(audit.get("evidence")):
                self.error("AUDIT", f"{cid}: PASS/NOT_APPLICABLE requiere auditoría PASS identificada")

        elif audit is not None and not isinstance(audit, dict):
            self.error("AUDIT", f"{cid}: audit debe ser objeto o null")

    def check_agents(self) -> None:
        config_path = self.root / ".codex/config.toml"
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            self.error("TOML", f".codex/config.toml: {exc}")
            config = {}
        agents_config = config.get("agents", {}) if isinstance(config, dict) else {}
        if not isinstance(agents_config, dict):
            self.error("AGENT-CONFIG", "agents debe ser un objeto TOML")
            agents_config = {}
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
            if not isinstance(name, str):
                self.error("AGENT", f"{path.name}: name debe ser string")
                continue
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

    @staticmethod
    def _is_nonempty_string(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _is_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    def _check_timestamp(self, value: Any, location: str) -> None:
        if not self._is_nonempty_string(value) or not UTC_TIMESTAMP_RE.fullmatch(value):
            self.error("SCHEMA", f"{location}: timestamp debe ser ISO-8601 UTC terminado en Z")
            return
        try:
            datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError:
            self.error("SCHEMA", f"{location}: timestamp UTC inválido")

    def _check_hash(self, value: Any, location: str) -> None:
        if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
            self.error("SCHEMA", f"{location}: output_sha256 debe ser hexadecimal de 64 caracteres")

    @staticmethod
    def configuration_sha256(root: Path) -> str:
        digest = hashlib.sha256()
        for relative in CONFIGURATION_PATHS:
            path_bytes = relative.encode("utf-8")
            content = (root / relative).read_bytes()
            digest.update(len(path_bytes).to_bytes(8, "big"))
            digest.update(path_bytes)
            digest.update(len(content).to_bytes(8, "big"))
            digest.update(content)
        return digest.hexdigest()

    def _check_output_sidecar(self, output_path: Any, expected_hash: Any, location: str) -> None:
        if not self._is_nonempty_string(output_path):
            self.error("SCHEMA", f"{location}.output_path: debe ser ruta relativa no vacía")
            return
        relative = Path(output_path)
        if relative.is_absolute() or ".." in relative.parts:
            self.error("RUNTIME-EVIDENCE", f"{location}.output_path: ruta insegura")
            return
        assert self.runtime_evidence is not None
        path = self.runtime_evidence.parent / relative
        try:
            metadata = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError("no es un archivo regular")
            if metadata.st_size > MAX_RUNTIME_EVIDENCE_BYTES:
                raise OSError("excede el límite de 1 MiB")
            raw = path.read_bytes()
        except OSError as exc:
            self.error("RUNTIME-EVIDENCE", f"{location}.output_path: {exc}")
            return
        if len(raw) > MAX_RUNTIME_EVIDENCE_BYTES:
            self.error("RUNTIME-EVIDENCE", f"{location}.output_path: excede el límite de 1 MiB")
        elif isinstance(expected_hash, str) and hashlib.sha256(raw).hexdigest() != expected_hash.lower():
            self.error("RUNTIME-EVIDENCE", f"{location}.output_sha256: no coincide con el sidecar")

    def _check_observation(self, value: Any, location: str) -> None:
        if not isinstance(value, dict):
            self.error("SCHEMA", f"{location}: debe ser un objeto")
            return
        expected = {"command", "exit_code", "output_path", "output_sha256"}
        if set(value) != expected:
            self.error("SCHEMA", f"{location}: campos esperados={sorted(expected)}")
        if not self._is_nonempty_string(value.get("command")):
            self.error("SCHEMA", f"{location}.command: debe ser string no vacío")
        exit_code = value.get("exit_code")
        if not self._is_integer(exit_code) or exit_code != 0:
            self.error("EFFECTIVE", f"{location}.exit_code: debe ser entero 0")
        self._check_hash(value.get("output_sha256"), f"{location}.output_sha256")
        self._check_output_sidecar(value.get("output_path"), value.get("output_sha256"), location)

    def _read_runtime_evidence(self) -> dict[str, Any] | None:
        path = self.runtime_evidence
        assert path is not None
        try:
            stat = path.stat()
        except OSError as exc:
            self.error("RUNTIME-EVIDENCE", f"{path}: no se puede acceder: {exc}")
            return None
        if not path.is_file() or not os.path.isfile(path):
            self.error("RUNTIME-EVIDENCE", f"{path}: debe ser un archivo regular")
            return None
        if stat.st_size > MAX_RUNTIME_EVIDENCE_BYTES:
            self.error("RUNTIME-EVIDENCE", f"{path}: excede el límite de 1 MiB")
            return None
        try:
            raw = path.read_bytes()
            if len(raw) > MAX_RUNTIME_EVIDENCE_BYTES:
                self.error("RUNTIME-EVIDENCE", f"{path}: excede el límite de 1 MiB")
                return None
            text = raw.decode("utf-8")
            value = json.loads(text)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("RUNTIME-EVIDENCE", f"{path}: evidencia UTF-8 JSON inválida: {exc}")
            return None
        if not isinstance(value, dict):
            self.error("SCHEMA", "runtime evidence: la raíz debe ser un objeto")
            return None
        return value

    def check_runtime_evidence(self) -> None:
        """Valida evidencia externa; no demuestra readiness ni autoriza ejecución."""
        payload = self._read_runtime_evidence()
        if payload is None:
            return
        expected_top = {"schema_version", "collected_at_utc", "configuration_sha256", "collector", "agents"}
        allowed_top = expected_top | {"repository_commit"}
        if not expected_top.issubset(payload) or not set(payload).issubset(allowed_top):
            self.error("SCHEMA", f"runtime evidence: campos esperados={sorted(expected_top)}")
        if payload.get("schema_version") != RUNTIME_SCHEMA_VERSION:
            self.error("SCHEMA", f"schema_version debe ser {RUNTIME_SCHEMA_VERSION!r}")
        self._check_timestamp(payload.get("collected_at_utc"), "collected_at_utc")
        self._check_hash(payload.get("configuration_sha256"), "configuration_sha256")
        try:
            actual_configuration = self.configuration_sha256(self.root)
        except OSError as exc:
            self.error("RUNTIME-EVIDENCE", f"configuration_sha256: no se pudo calcular: {exc}")
        else:
            reported_configuration = payload.get("configuration_sha256")
            if isinstance(reported_configuration, str) and reported_configuration.lower() != actual_configuration:
                self.error("RUNTIME-EVIDENCE", "configuration_sha256 no coincide con la configuración actual")
        repository_commit = payload.get("repository_commit")
        if repository_commit is not None:
            if not isinstance(repository_commit, str) or not HEX40_RE.fullmatch(repository_commit):
                self.error("SCHEMA", "repository_commit debe ser hexadecimal de 40 caracteres")
            else:
                self.reported_repository_commit = repository_commit.lower()
        collector = payload.get("collector")
        if not isinstance(collector, dict):
            self.error("SCHEMA", "collector: debe ser un objeto")
        else:
            expected_collector = {"session_id", "command", "exit_code", "output_path", "output_sha256"}
            if set(collector) != expected_collector:
                self.error("SCHEMA", f"collector: campos esperados={sorted(expected_collector)}")
            if not self._is_nonempty_string(collector.get("session_id")):
                self.error("SCHEMA", "collector.session_id: debe ser string no vacío")
            self._check_observation(
                {key: collector.get(key) for key in ("command", "exit_code", "output_path", "output_sha256")},
                "collector",
            )

        agents = payload.get("agents")
        if not isinstance(agents, list):
            self.error("SCHEMA", "agents: debe ser una lista")
            return
        if len(agents) != len(REQUIRED_AGENTS):
            self.error("ROLE", f"agents: se esperaban exactamente {len(REQUIRED_AGENTS)} roles")
        observed_names: list[str] = []
        invalid_names = False
        for agent in agents:
            name = agent.get("name") if isinstance(agent, dict) else None
            if isinstance(name, str) and name:
                observed_names.append(name)
            else:
                invalid_names = True
        if invalid_names:
            self.error("ROLE", "agents: cada name debe ser string no vacío")
        if len(observed_names) != len(set(observed_names)):
            self.error("ROLE", "agents: hay nombres duplicados")
        if set(observed_names) != set(REQUIRED_AGENTS):
            self.error("ROLE", f"agents: roles esperados={sorted(REQUIRED_AGENTS)}")

        session_ids: list[str] = []
        for index, agent in enumerate(agents):
            location = f"agents[{index}]"
            if not isinstance(agent, dict):
                self.error("SCHEMA", f"{location}: debe ser un objeto")
                continue
            name = agent.get("name")
            required = REQUIRED_AGENTS.get(name) if isinstance(name, str) else None
            if required is None:
                continue
            expected_agent = {
                "name", "configured", "effective", "session_id", "observed_at_utc",
                "load_status", "sandbox_status", "observation",
            }
            allowed_agent = expected_agent | {"substitution"}
            if not expected_agent.issubset(agent) or not set(agent).issubset(allowed_agent):
                self.error("SCHEMA", f"{location}: campos faltantes o extra")
            session_id = agent.get("session_id")
            if not self._is_nonempty_string(session_id):
                self.error("SCHEMA", f"{location}.session_id: debe ser string no vacío")
            else:
                session_ids.append(session_id)
            self._check_timestamp(agent.get("observed_at_utc"), f"{location}.observed_at_utc")
            if agent.get("load_status") != "loaded":
                self.error("EFFECTIVE", f"{location}.load_status: debe ser 'loaded'")
            if agent.get("sandbox_status") != "enforced":
                self.error("SANDBOX", f"{location}.sandbox_status: debe ser 'enforced'")
            self._check_observation(agent.get("observation"), f"{location}.observation")

            keys = {"model", "reasoning_effort", "sandbox_mode"}
            configured = agent.get("configured")
            effective = agent.get("effective")
            if not isinstance(configured, dict) or set(configured) != keys:
                self.error("CONFIG", f"{location}.configured: campos inválidos")
                configured = {}
            if not isinstance(effective, dict) or set(effective) != keys:
                self.error("EFFECTIVE", f"{location}.effective: campos inválidos")
                effective = {}
            expected_config = dict(zip(("model", "reasoning_effort", "sandbox_mode"), required))
            if configured != expected_config:
                self.error("CONFIG", f"{location}.configured: no coincide con el TOML de {name}")
            for key in keys:
                if not self._is_nonempty_string(effective.get(key)):
                    self.error("EFFECTIVE", f"{location}.effective.{key}: debe ser string no vacío")
            if effective.get("sandbox_mode") != expected_config["sandbox_mode"]:
                self.error("SANDBOX", f"{location}.effective.sandbox_mode: debe coincidir con configured")

            changed = any(
                effective.get(key) != expected_config[key]
                for key in ("model", "reasoning_effort")
            )
            substitution = agent.get("substitution")
            if changed:
                expected_substitution = {
                    "requested_model", "requested_reasoning_effort", "effective_model",
                    "effective_reasoning_effort", "reason", "source",
                }
                if not isinstance(substitution, dict) or set(substitution) != expected_substitution:
                    self.error("SUBSTITUTION", f"{location}: divergencia efectiva requiere substitution completa")
                else:
                    expected_values = {
                        "requested_model": expected_config["model"],
                        "requested_reasoning_effort": expected_config["reasoning_effort"],
                        "effective_model": effective.get("model"),
                        "effective_reasoning_effort": effective.get("reasoning_effort"),
                    }
                    if any(substitution.get(key) != value for key, value in expected_values.items()):
                        self.error("SUBSTITUTION", f"{location}.substitution: valores inconsistentes")
                    for key in ("reason", "source"):
                        if not self._is_nonempty_string(substitution.get(key)):
                            self.error("SUBSTITUTION", f"{location}.substitution.{key}: debe ser string no vacío")
            elif substitution is not None:
                self.error("SUBSTITUTION", f"{location}: substitution sin divergencia efectiva")

        if len(session_ids) != len(set(session_ids)):
            self.error("ROLE", "agents: session_id debe ser único para cada rol")

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
    parser.add_argument(
        "--runtime-evidence",
        type=Path,
        help="JSON externo de capacidades efectivas; solo valida formato y consistencia",
    )
    args = parser.parse_args(argv)
    errors = ClosureChecker(args.root, runtime_evidence=args.runtime_evidence).run()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"scientific-closure checker: FAIL ({len(errors)} incumplimientos)", file=sys.stderr)
        return 1
    if args.runtime_evidence is None:
        print("scientific-closure checker: PASS (estructura; runtime no verificado)")
    else:
        print(
            "scientific-closure checker: PASS "
            "(runtime con formato/consistencia verificados; no autoriza ejecución ni acredita readiness)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
