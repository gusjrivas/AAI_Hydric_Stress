"""Validación de ADMISIBILIDAD de un candidato congelado para una ejecución
concreta -- operación independiente del runner de la Etapa B, con contexto
explícito del consumidor.

Distinta e independiente de la lectura estructural (`transfer_contract.py`):
un artefacto puede leerse correctamente y aun así resultar inadmisible para
el modo de la ejecución que intenta consumirlo. Esta función no entrena, no
selecciona modelos y no abre ningún CSV crudo -- el contexto de datos y de
identidad del consumidor se recibe explícitamente como parámetro, nunca se
calcula ni se infiere aquí.

Distingue tres verificaciones que el protocolo exige no confundir:
identidad, integridad y compatibilidad (ver
`openspec/changes/implement-controlled-daily-v4-stage-b-c/proposal.md`,
"Precisión de la procedencia entre etapas"). Esta función NO confía en que
`contract` provenga necesariamente de `transfer_contract.load_frozen_config_contract`
(puede recibir un `FrozenConfigContract` construido directamente, como en los
tests): revalida por sí misma la huella del productor en vez de asumir que ya
fue validada.

Sobre el commit del productor -- DOS verificaciones distintas, que no deben
confundirse ni sustituirse entre sí:

(a) **Consistencia interna del productor**: el commit embebido en
    `frozen_config.json` (vía `contract.producer_code_identity`) debe
    coincidir con el de `code_version.json` en el mismo directorio -- ambos
    archivos deberían provenir de la misma corrida de A. Si difieren, es
    indicio de una mezcla de artefactos de corridas distintas.
(b) **Compatibilidad productor-consumidor**: el commit del productor (A) se
    compara explícitamente contra el commit de la ejecución consumidora (B),
    recibido en `consumer_code_identity`. Los commits pueden coincidir
    (caso normal) o diferir (por ejemplo, si B corre después de una
    corrección); si difieren y no existe una política de compatibilidad
    documentada que acredite esa diferencia, se rechaza explícitamente por
    "compatibilidad no acreditada" -- nunca se admite un cambio arbitrario
    solo porque el SHA tiene formato válido.

Ninguna de las dos sustituye a la otra: (a) sin (b), o (b) sin (a), deja
pasar exactamente el defecto que la otra existe para atrapar."""

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
from experiment_runner.controlled_daily_v4.environment import (
    capture_constraints_identity,
    validate_environment,
)
from experiment_runner.controlled_daily_v4.transfer_contract import (
    FrozenConfigContract,
    validate_fingerprint_reference,
)

_FINGERPRINT_CONSISTENCY_FIELDS = ("schema_version", "sha256", "n_rows", "scope")


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


def _mismatched_fingerprint_fields(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """Campos requeridos (`schema_version`/`sha256`/`n_rows`/`scope`) donde
    `a` y `b` difieren -- una coincidencia de `sha256` sola no basta: dos
    huellas de la misma corrida deben coincidir en TODOS los metadatos
    requeridos, no solo en el hash."""
    return [field for field in _FINGERPRINT_CONSISTENCY_FIELDS if a.get(field) != b.get(field)]


def _validate_producer_fingerprint(
    fingerprint_ref: dict[str, Any], producer_dir: Path
) -> dict[str, Any]:
    """Revalida (no asume ya validado) que la referencia embebida y el
    artefacto hermano `dataset_fingerprint.json` tengan forma y contenido
    verificable -- nunca compara valores ausentes/`None` entre sí como si
    coincidieran, y nunca se conforma con que coincida únicamente el
    `sha256`: los cuatro metadatos requeridos deben coincidir entre sí."""
    try:
        validate_fingerprint_reference(fingerprint_ref, "producer.dataset_fingerprint_ref")
    except ValueError as exc:
        raise StageBAdmissibilityError([str(exc)]) from exc

    fingerprint_payload = _load_producer_json(producer_dir, "dataset_fingerprint.json")
    try:
        validate_fingerprint_reference(
            fingerprint_payload, f"'{producer_dir / 'dataset_fingerprint.json'}'"
        )
    except ValueError as exc:
        raise StageBAdmissibilityError([str(exc)]) from exc

    mismatched = _mismatched_fingerprint_fields(fingerprint_payload, fingerprint_ref)
    if mismatched:
        raise StageBAdmissibilityError(
            [
                "La huella de dataset embebida en frozen_config.json no coincide con "
                f"'{producer_dir / 'dataset_fingerprint.json'}' en {mismatched}: indicio de "
                "mezcla de artefactos de corridas distintas"
            ]
        )
    return fingerprint_payload


def check_stage_b_admissibility(
    contract: FrozenConfigContract,
    *,
    producer_dir: str | Path,
    consumer_input_mode: str,
    consumer_code_identity: dict[str, Any] | None = None,
    consumer_environment_issues: list[str] | None = None,
    consumer_training_dataset_fingerprint: dict[str, Any] | None = None,
) -> None:
    """Decide si `contract` (ya leído estructuralmente) es admisible como
    insumo de una ejecución concreta de la Etapa B. No devuelve nada: admite
    en silencio, o levanta `StageBAdmissibilityError` con todos los motivos
    de rechazo verificados.

    Puede leer artefactos de evidencia ya persistidos por el productor
    (`code_version.json`, `environment.json`, `dataset_fingerprint.json`, en
    `producer_dir`), pero nunca CSV crudos ni entrena nada. El contexto de la
    ejecución consumidora se recibe explícitamente y nunca se calcula aquí:

    - `consumer_code_identity`: identidad de código de la propia ejecución de
      B (misma forma que `code_identity.CodeIdentity`, serializada), exigida
      para el camino científico.
    - `consumer_environment_issues`: lista de incumplimientos de la
      validación normativa del entorno de B (`[]` si está todo validado;
      `None` significa "no se recibió", que se rechaza explícitamente, nunca
      se asume vacío).
    - `consumer_training_dataset_fingerprint`: huella del conjunto de
      entrenamiento autorizado de B, ya calculada por quien invoca -- esta
      función nunca la calcula ni abre CSV para obtenerla."""
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

    # `scientific_run=true` por sí solo no basta (spec.md): además de la
    # bandera, se exige explícitamente que el MODO declarado sea científico
    # (no solo que la bandera lo diga) -- un contrato con input_mode
    # inconsistente ya se rechaza en la lectura estructural, pero esta
    # función no depende de esa capa para su propia decisión.
    if not contract.scientific_run or contract.input_mode != INPUT_MODE_SCIENTIFIC:
        reasons.append(
            "El candidato no está marcado como científico en ambos ejes (scientific_run="
            f"{contract.scientific_run!r}, input_mode={contract.input_mode!r}): no admisible "
            "para una ejecución científica de la Etapa B"
        )

    producer_code_identity = contract.producer_code_identity
    if not producer_code_identity.get("available"):
        reasons.append(
            "La identidad de código del productor no está disponible "
            f"(reason={producer_code_identity.get('reason')!r})"
        )
    if producer_code_identity.get("dirty") is not False:
        reasons.append(
            "La identidad de código del productor no reporta dirty=False "
            f"(dirty={producer_code_identity.get('dirty')!r}); una corrida científica exige "
            "árbol limpio"
        )
    producer_commit = producer_code_identity.get("commit")
    if not is_valid_full_sha(producer_commit):
        reasons.append(
            f"La identidad de código del productor no tiene un commit válido "
            f"(commit={producer_commit!r})"
        )

    # (a) Consistencia INTERNA del productor: dos artefactos que A debería
    # haber escrito en la misma corrida deben coincidir entre sí. Esto NO
    # sustituye la comparación productor-consumidor de más abajo (b): ambas
    # verifican cosas distintas y ambas deben pasar.
    sibling_code_version = _load_producer_json(producer_dir, "code_version.json")
    if sibling_code_version != producer_code_identity:
        reasons.append(
            "La identidad de código embebida en frozen_config.json no coincide con "
            f"'{producer_dir / 'code_version.json'}': indicio de mezcla de artefactos de "
            "corridas distintas dentro del propio productor"
        )

    # (b) Compatibilidad PRODUCTOR-CONSUMIDOR: comparación real entre el
    # commit histórico de A y el commit actual de la ejecución consumidora
    # de B, recibido explícitamente -- nunca calculado ni sustituido por (a).
    if consumer_code_identity is None:
        reasons.append(
            "No se recibió la identidad de código de la ejecución consumidora (contexto "
            "explícito requerido; no se asume ni se omite esta verificación)"
        )
    else:
        if not consumer_code_identity.get("available"):
            reasons.append(
                "La identidad de código de la ejecución consumidora no está disponible "
                f"(reason={consumer_code_identity.get('reason')!r})"
            )
        if consumer_code_identity.get("dirty") is not False:
            reasons.append(
                "La identidad de código de la ejecución consumidora no reporta dirty=False "
                f"(dirty={consumer_code_identity.get('dirty')!r})"
            )
        consumer_commit = consumer_code_identity.get("commit")
        if not is_valid_full_sha(consumer_commit):
            reasons.append(
                "La identidad de código de la ejecución consumidora no tiene un commit válido "
                f"(commit={consumer_commit!r})"
            )
        elif is_valid_full_sha(producer_commit) and consumer_commit != producer_commit:
            reasons.append(
                f"El commit del productor ({producer_commit!r}) difiere del commit de la "
                f"ejecución consumidora ({consumer_commit!r}) y no existe una política de "
                "compatibilidad documentada que acredite esa diferencia: se rechaza por "
                "compatibilidad no acreditada"
            )

    if consumer_environment_issues is None:
        reasons.append(
            "No se recibió evidencia de validación normativa del entorno de la ejecución "
            "consumidora (contexto explícito requerido)"
        )
    elif consumer_environment_issues:
        reasons.append(
            "La ejecución consumidora registra fallas de validación de entorno: "
            f"{consumer_environment_issues}"
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
    # Una bandera aislada (`validated_before_training=True`) no alcanza, ni
    # tampoco que los diccionarios simplemente tengan contenido: se
    # revalida, con los mecanismos ya existentes, que ese contenido sea
    # REAL y coherente con la referencia normativa -- nunca sustituyendo el
    # entorno HISTÓRICO del productor (el que quedó persistido) por el de
    # esta ejecución.
    constraints_identity = environment_payload.get("constraints_identity")
    if not isinstance(constraints_identity, dict) or constraints_identity.get("exists") is not True:
        reasons.append(
            "El productor no registra una identidad de 'constraints.txt' verificable "
            f"(constraints_identity={constraints_identity!r})"
        )
    else:
        recorded_sha256 = constraints_identity.get("sha256")
        if not is_valid_full_sha(recorded_sha256):
            reasons.append(
                "El SHA-256 de 'constraints.txt' registrado por el productor no tiene formato "
                f"válido (sha256={recorded_sha256!r})"
            )
        else:
            current_constraints_identity = capture_constraints_identity()
            if (
                not current_constraints_identity["exists"]
                or current_constraints_identity["sha256"] != recorded_sha256
            ):
                reasons.append(
                    "El SHA-256 de 'constraints.txt' registrado por el productor "
                    f"({recorded_sha256!r}) no coincide con el archivo de referencia real "
                    f"({current_constraints_identity['sha256']!r})"
                )
    if not environment_payload.get("packages"):
        reasons.append(
            "El productor no registra las versiones de paquetes efectivamente capturadas "
            "(evidencia de entorno insuficiente)"
        )
    else:
        # Reutiliza `environment.validate_environment` (mecanismo ya
        # existente) sobre el propio entorno PERSISTIDO del productor,
        # contrastado contra la referencia normativa versionada
        # (manifiesto/constraints.txt) -- nunca contra el entorno de la
        # ejecución que está evaluando la admisibilidad.
        report = validate_environment(environment_payload)
        if not report.ok:
            reasons.append(
                "El entorno persistido del productor no valida contra la referencia normativa "
                f"versionada: {report.issues}"
            )

    fingerprint_ref = contract.producer_dataset_fingerprint_ref
    try:
        _validate_producer_fingerprint(fingerprint_ref, producer_dir)
    except StageBAdmissibilityError as exc:
        reasons.extend(exc.reasons)

    if consumer_training_dataset_fingerprint is None:
        reasons.append(
            "No se recibió explícitamente la huella del conjunto de entrenamiento autorizado "
            "de B (el contexto de datos del consumidor debe pasarse explícitamente, nunca "
            "recalcularse aquí)"
        )
    else:
        try:
            validate_fingerprint_reference(
                consumer_training_dataset_fingerprint, "consumer_training_dataset_fingerprint"
            )
        except ValueError as exc:
            reasons.append(str(exc))
        else:
            # B reentrena sobre el mismo período que A (protocolo): el
            # protocolo exige igualdad exacta de huella -- no solo del hash,
            # sino de TODOS los metadatos requeridos (`schema_version`,
            # `n_rows`, `scope`). Una discrepancia en cualquiera de ellos,
            # aun con el mismo `sha256`, es una contradicción que se
            # rechaza explícitamente, no una coincidencia parcial aceptable.
            mismatched = _mismatched_fingerprint_fields(
                consumer_training_dataset_fingerprint, fingerprint_ref
            )
            if mismatched:
                reasons.append(
                    "La huella del entrenamiento autorizado de la Etapa B "
                    f"({consumer_training_dataset_fingerprint!r}) difiere de la huella del "
                    f"conjunto derivado de A ({fingerprint_ref!r}) en {mismatched}: B reentrena "
                    "sobre el mismo período que A (protocolo), por lo que se exige igualdad "
                    "exacta -- no una extensión de período como en la Etapa C"
                )

    if reasons:
        raise StageBAdmissibilityError(reasons)


__all__ = ["StageBAdmissibilityError", "check_stage_b_admissibility"]
