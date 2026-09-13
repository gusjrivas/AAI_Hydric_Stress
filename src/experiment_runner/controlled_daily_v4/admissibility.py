"""Validación de ADMISIBILIDAD de un candidato congelado para una ejecución
concreta -- operación independiente del runner de la Etapa B, con contexto
explícito del consumidor.

Distinta e independiente de la lectura estructural (`transfer_contract.py`):
un artefacto puede leerse correctamente y aun así resultar inadmisible para
el modo de la ejecución que intenta consumirlo. Esta función no entrena, no
selecciona modelos y no abre ningún CSV crudo -- el contexto de datos del
consumidor (la huella de su propio conjunto de entrenamiento autorizado) se
recibe explícitamente como parámetro, nunca se calcula aquí.

Distingue tres verificaciones que el protocolo exige no confundir:
identidad, integridad y compatibilidad (ver
`openspec/changes/implement-controlled-daily-v4-stage-b-c/proposal.md`,
"Precisión de la procedencia entre etapas").

Sobre el commit del productor: esta función NUNCA compara el commit de la
ejecución consumidora (Etapa B) contra el commit histórico del productor
(Etapa A) -- ninguna de las dos relaciones (igualdad o diferencia) certifica
ni descarta nada por sí sola (spec.md, escenario "`scientific_run=true` por
sí solo no basta"). La única comparación de commit que SÍ realiza es una
verificación de CONSISTENCIA INTERNA entre dos artefactos que el productor
debería haber escrito en la misma corrida (`frozen_config.json` y
`code_version.json` del mismo directorio): si difieren, es evidencia de una
mezcla de artefactos de corridas distintas, no una comparación productor
vs. consumidor -- de ahí que una diferencia sin política de compatibilidad
documentada se rechace explícitamente."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiment_runner.controlled_daily_v4.code_identity import is_valid_full_sha
from experiment_runner.controlled_daily_v4.config import (
    DEPTH_ROLE_PRIMARY,
    INPUT_MODE_SCIENTIFIC,
    INPUT_MODE_SYNTHETIC,
)
from experiment_runner.controlled_daily_v4.transfer_contract import FrozenConfigContract


class StageBAdmissibilityError(ValueError):
    """El candidato leído estructuralmente no es admisible para esta
    ejecución concreta de la Etapa B. `reasons` enumera todos los motivos
    verificados, no solo el primero."""

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons) if self.reasons else "candidato no admisible")


def _load_producer_json(producer_dir: Path, filename: str) -> dict[str, Any]:
    path = producer_dir / filename
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise StageBAdmissibilityError(
            [f"Falta el artefacto de evidencia del productor requerido: '{path}'"]
        ) from None
    except OSError as exc:
        raise StageBAdmissibilityError([f"No se pudo leer '{path}': {exc}"]) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StageBAdmissibilityError([f"'{path}' no es JSON válido: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise StageBAdmissibilityError([f"'{path}': el JSON raíz debe ser un objeto"])
    return payload


def check_stage_b_admissibility(
    contract: FrozenConfigContract,
    *,
    producer_dir: str | Path,
    consumer_input_mode: str,
    consumer_training_dataset_fingerprint: dict[str, Any] | None = None,
) -> None:
    """Decide si `contract` (ya leído estructuralmente) es admisible como
    insumo de una ejecución concreta de la Etapa B. No devuelve nada: admite
    en silencio, o levanta `StageBAdmissibilityError` con todos los motivos
    de rechazo verificados.

    Puede leer artefactos de evidencia ya persistidos por el productor
    (`code_version.json`, `environment.json`, `dataset_fingerprint.json`, en
    `producer_dir`), pero nunca CSV crudos ni entrena nada. La huella del
    entrenamiento autorizado del consumidor (`consumer_training_dataset_fingerprint`)
    debe recibirse explícitamente -- esta función nunca la calcula."""
    producer_dir = Path(producer_dir)

    # Restricción de profundidad: siempre error duro, verificado en este
    # punto de consumo (nunca en la lectura estructural), y nunca combinado
    # con otros motivos -- un candidato de sensibilidad jamás sustituye al
    # principal, sin excepción posible.
    if contract.depth_role != DEPTH_ROLE_PRIMARY:
        raise StageBAdmissibilityError(
            [
                f"depth_role='{contract.depth_role}' no es admisible como insumo de la Etapa B: "
                "únicamente 'primary_selection' puede congelarse en B; un candidato de "
                "sensibilidad no sustituye al principal"
            ]
        )

    if not contract.candidate_produced:
        raise StageBAdmissibilityError(
            [
                "La Etapa A no produjo ningún candidato congelado: la ausencia de candidato "
                "impide continuar"
            ]
        )

    if consumer_input_mode == INPUT_MODE_SYNTHETIC:
        if contract.input_mode != INPUT_MODE_SYNTHETIC:
            raise StageBAdmissibilityError(
                [
                    "Una ejecución de integración sintética solo admite candidatos con "
                    f"input_mode='synthetic' (recibido input_mode={contract.input_mode!r})"
                ]
            )
        # Admitido: flujo sintético completo con candidato explícitamente
        # sintético en ambos extremos, sin tocar ningún registro científico.
        return

    if consumer_input_mode != INPUT_MODE_SCIENTIFIC:
        raise StageBAdmissibilityError(
            [f"input_mode de la ejecución consumidora desconocido: '{consumer_input_mode}'"]
        )

    reasons: list[str] = []

    # `scientific_run=true` por sí solo no basta (spec.md): se verifican,
    # además, integridad del autorreporte del productor y compatibilidad de
    # procedencia -- ninguna sustituye a la otra.
    if not contract.scientific_run:
        reasons.append(
            "El candidato tiene scientific_run=false: no admisible para una ejecución "
            "científica de la Etapa B"
        )

    code_identity = contract.producer_code_identity
    if not code_identity.get("available"):
        reasons.append(
            "La identidad de código del productor no está disponible "
            f"(reason={code_identity.get('reason')!r})"
        )
    if code_identity.get("dirty") is not False:
        reasons.append(
            "La identidad de código del productor no reporta dirty=False "
            f"(dirty={code_identity.get('dirty')!r}); una corrida científica exige árbol limpio"
        )
    commit = code_identity.get("commit")
    if not is_valid_full_sha(commit):
        reasons.append(
            f"La identidad de código del productor no tiene un commit válido (commit={commit!r})"
        )

    # Consistencia interna entre dos artefactos que el productor escribió en
    # la MISMA corrida (nunca una comparación contra el commit de esta
    # ejecución consumidora -- ver docstring del módulo). Los commits
    # 'pueden coincidir' (caso normal, misma corrida): si difieren, es
    # evidencia de una mezcla de artefactos de corridas distintas, y sin una
    # política de compatibilidad documentada que la acredite, se rechaza.
    sibling_code_version = _load_producer_json(producer_dir, "code_version.json")
    if sibling_code_version != code_identity:
        reasons.append(
            "La identidad de código embebida en frozen_config.json no coincide con "
            f"'{producer_dir / 'code_version.json'}': indicio de mezcla de artefactos de "
            "corridas distintas, sin política de compatibilidad documentada que la acredite"
        )

    environment_payload = _load_producer_json(producer_dir, "environment.json")
    if not environment_payload.get("validated_before_training"):
        reasons.append(
            "El productor no registra evidencia de validación normativa del entorno previa "
            "al entrenamiento"
        )
    if environment_payload.get("validation_issues"):
        reasons.append(
            "El productor registra fallas de validación de entorno: "
            f"{environment_payload['validation_issues']}"
        )

    fingerprint_payload = _load_producer_json(producer_dir, "dataset_fingerprint.json")
    fingerprint_ref = contract.producer_dataset_fingerprint_ref
    if fingerprint_payload.get("sha256") != fingerprint_ref.get("sha256"):
        reasons.append(
            "La huella de dataset embebida en frozen_config.json no coincide con "
            f"'{producer_dir / 'dataset_fingerprint.json'}': indicio de mezcla de artefactos "
            "de corridas distintas"
        )

    if consumer_training_dataset_fingerprint is None:
        reasons.append(
            "No se recibió explícitamente la huella del conjunto de entrenamiento autorizado "
            "de B (el contexto de datos del consumidor debe pasarse explícitamente, nunca "
            "recalcularse aquí)"
        )
    else:
        consumer_sha256 = consumer_training_dataset_fingerprint.get("sha256")
        producer_sha256 = fingerprint_ref.get("sha256")
        if consumer_sha256 != producer_sha256:
            reasons.append(
                "La huella del entrenamiento autorizado de la Etapa B "
                f"({consumer_sha256!r}) difiere de la huella del conjunto derivado de A "
                f"({producer_sha256!r}): B reentrena sobre el mismo período que A "
                "(protocolo), por lo que el protocolo exige igualdad exacta de huella -- no "
                "una extensión de período como en la Etapa C"
            )

    if reasons:
        raise StageBAdmissibilityError(reasons)


__all__ = ["StageBAdmissibilityError", "check_stage_b_admissibility"]
