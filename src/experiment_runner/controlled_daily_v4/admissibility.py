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
import math
from pathlib import Path
from typing import Any

from experiment_runner.controlled_daily_v4.artifacts import STAGE_B_ARTIFACT_SCHEMA_VERSION
from experiment_runner.controlled_daily_v4.bootstrap import compute_is_normative_configuration
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

_DELTA_MCC_LOWER_DOMAIN = -2.0
_DELTA_MCC_UPPER_DOMAIN = 2.0
"""Dominio matemático de una DIFERENCIA de dos MCC (`interval_lower`/
`interval_upper` de `bootstrap.json`, que reportan un intervalo de
`MCC_candidato - MCC_baseline`, nunca un MCC aislado): `[-2, 2]`, no
`[-1, 1]` (revisión dirigida, hallazgo 2, segunda ronda) -- el MCC individual
vive en `[-1, 1]`, pero la resta de dos valores de ese rango puede alcanzar
`[-2, 2]` (por ejemplo, candidato=1.0, baseline=-1.0). Validar el intervalo
de ΔMCC contra el dominio de un MCC aislado rechazaba, incorrectamente,
intervalos matemáticamente válidos como `[1.1, 1.3]`."""


class StageBAdmissibilityError(ValueError):
    """El candidato leído estructuralmente no es admisible para esta
    ejecución concreta de la Etapa B. `reasons` enumera todos los motivos
    verificados, no solo el primero."""

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons) if self.reasons else "candidato no admisible")


def _load_producer_json(
    producer_dir: Path, filename: str, error_cls: type[ValueError] = None
) -> dict[str, Any]:
    error_cls = error_cls or StageBAdmissibilityError
    path = producer_dir / filename
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise error_cls(
            [f"Falta el artefacto de evidencia del productor requerido: '{path}'"]
        ) from None
    except OSError as exc:
        raise error_cls([f"No se pudo leer '{path}': {exc}"]) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise error_cls([f"'{path}' no es JSON válido: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise error_cls([f"'{path}': el JSON raíz debe ser un objeto"])
    return payload


def _validate_bounded_metric(
    value: Any, label: str, reasons: list[str], *, lower: float = -1.0, upper: float = 1.0
) -> float | None:
    """Valida ESTRUCTURALMENTE un valor antes de interpretarlo como métrica
    numérica (hallazgo de revisión dirigida: 'validá estructuralmente los
    artefactos antes de interpretar sus valores'). Rechaza explícitamente:
    booleanos (`bool` es subclase de `int` en Python -- `isinstance(True, (int,
    float))` es verdadero y `True > 0` también, lo que aceptaba un booleano
    como si fuera un MCC válido), valores no numéricos, valores no finitos
    (`inf`/`-inf`/`nan`) y valores fuera del dominio matemático de la métrica
    (`[-1, 1]` para MCC/límites de intervalo). Devuelve el valor numérico
    validado, o `None` si se rechazó (y ya dejó el motivo en `reasons`)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        reasons.append(f"{label} no es un valor numérico válido (recibido {value!r})")
        return None
    numeric = float(value)
    if not math.isfinite(numeric):
        reasons.append(f"{label} no es finito (recibido {value!r})")
        return None
    if not (lower <= numeric <= upper):
        reasons.append(f"{label}={numeric!r} está fuera del dominio válido [{lower}, {upper}]")
        return None
    return numeric


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


class StageCAdmissibilityError(ValueError):
    """El veredicto de la Etapa B (y/o la evidencia que lo sustenta) no es
    admisible como habilitación de una ejecución concreta de la Etapa C.
    `reasons` enumera todos los motivos verificados, no solo el primero.

    Nunca se toca ningún dato de 2024-2025 desde este módulo: solo lee
    artefactos ya persistidos de A (vía `producer_dir`) y de B (vía
    `stage_b_dir`)."""

    def __init__(self, reasons: list[str]):
        self.reasons = list(reasons)
        super().__init__("; ".join(self.reasons) if self.reasons else "Etapa B no admisible")


def check_stage_c_admissibility(
    contract: FrozenConfigContract,
    *,
    stage_b_dir: str | Path,
    producer_dir: str | Path,
    consumer_input_mode: str,
    consumer_code_identity: dict[str, Any] | None = None,
    consumer_environment_issues: list[str] | None = None,
) -> None:
    """Decide si el veredicto `CANDIDATE_VALIDATED` de una corrida de la Etapa
    B (en `stage_b_dir`) habilita una ejecución concreta de la Etapa C sobre
    el candidato `contract` (leído estructuralmente desde `producer_dir`, el
    directorio de A referenciado por `stage_b_dir/producer_reference.json`).

    No entrena nada, no abre ningún ledger y NUNCA lee un CSV crudo: toda la
    evidencia que consulta ya está persistida localmente por A y B. La
    apertura efectiva del holdout (reserva + confirmación durable del ledger)
    es responsabilidad exclusiva de quien invoca, después de que esta función
    ya haya aceptado sin excepción.

    No acepta un `decision.json` aislado como evidencia suficiente: revalida
    la coherencia entre `decision.json`, `metrics.json` y `bootstrap.json` de
    B (recalcula la regla de aprobación desde los números persistidos, no
    confía únicamente en el campo `verdict`), y el linaje hasta el contrato
    congelado de A (`producer_reference.json` debe referenciar exactamente el
    mismo `frozen_config.json` que `contract` reconstruye)."""
    stage_b_dir = Path(stage_b_dir)
    producer_dir = Path(producer_dir)
    reasons: list[str] = []

    if contract.depth_role != DEPTH_ROLE_PRIMARY:
        raise StageCAdmissibilityError(
            [
                f"depth_role='{contract.depth_role}' no es admisible como insumo de la Etapa C: "
                "únicamente 'primary_selection' puede evaluarse en C"
            ]
        )
    if not contract.candidate_produced:
        raise StageCAdmissibilityError(
            [
                "La Etapa A no produjo ningún candidato congelado: la ausencia de candidato "
                "impide continuar"
            ]
        )

    producer_reference = _load_producer_json(
        stage_b_dir, "producer_reference.json", StageCAdmissibilityError
    )
    referenced_producer_dir = producer_reference.get("producer_dir")
    if referenced_producer_dir != str(producer_dir):
        reasons.append(
            f"'{stage_b_dir / 'producer_reference.json'}'.producer_dir="
            f"{referenced_producer_dir!r} no coincide con el directorio de A efectivamente "
            f"provisto ({str(producer_dir)!r}): el linaje hasta A no es verificable"
        )
    embedded_frozen_config = producer_reference.get("producer_frozen_config")
    if embedded_frozen_config != contract.raw:
        reasons.append(
            f"'{stage_b_dir / 'producer_reference.json'}'.producer_frozen_config no coincide "
            f"con el 'frozen_config.json' leído fresco desde '{producer_dir}': indicio de "
            "mezcla de artefactos de corridas distintas o de un directorio de A modificado "
            "después de que B consumiera el candidato"
        )

    schema_payload = _load_producer_json(
        stage_b_dir, "schema_version.json", StageCAdmissibilityError
    )
    if schema_payload.get("schema_version") != STAGE_B_ARTIFACT_SCHEMA_VERSION:
        reasons.append(
            f"'{stage_b_dir}': schema_version de B "
            f"({schema_payload.get('schema_version')!r}) no reconocido "
            f"(esperado {STAGE_B_ARTIFACT_SCHEMA_VERSION!r})"
        )

    resolved_config = _load_producer_json(
        stage_b_dir, "resolved_config.json", StageCAdmissibilityError
    )
    decision_payload = _load_producer_json(stage_b_dir, "decision.json", StageCAdmissibilityError)
    metrics_payload_b = _load_producer_json(stage_b_dir, "metrics.json", StageCAdmissibilityError)
    bootstrap_payload = _load_producer_json(stage_b_dir, "bootstrap.json", StageCAdmissibilityError)

    if decision_payload.get("verdict") != "CANDIDATE_VALIDATED":
        reasons.append(
            f"'{stage_b_dir / 'decision.json'}'.verdict="
            f"{decision_payload.get('verdict')!r} no es 'CANDIDATE_VALIDATED': la Etapa C no "
            "puede habilitarse (protocolo, sección 10)"
        )
    if decision_payload.get("predictions_available") is not True:
        reasons.append(
            f"'{stage_b_dir / 'decision.json'}'.predictions_available no es True: un veredicto "
            "CANDIDATE_VALIDATED sin predicciones disponibles es incoherente"
        )

    # Coherencia decisión/métricas/bootstrap: se RECALCULA la regla de
    # aprobación desde los números persistidos, nunca se confía únicamente en
    # el campo 'verdict' de decision.json (no aceptar un decision.json
    # aislado como evidencia suficiente).
    mcc_candidate_envelope = metrics_payload_b.get("mcc_candidate")
    if not isinstance(mcc_candidate_envelope, dict):
        reasons.append(
            f"'{stage_b_dir / 'metrics.json'}'.mcc_candidate no es un objeto estructurado "
            f"válido (recibido {mcc_candidate_envelope!r})"
        )
    elif mcc_candidate_envelope.get("status") != "defined":
        reasons.append(
            f"'{stage_b_dir / 'metrics.json'}'.mcc_candidate.status="
            f"{mcc_candidate_envelope.get('status')!r} no es 'defined': no sustenta "
            "'CANDIDATE_VALIDATED'"
        )
    else:
        mcc_value = _validate_bounded_metric(
            mcc_candidate_envelope.get("value"),
            f"'{stage_b_dir / 'metrics.json'}'.mcc_candidate.value",
            reasons,
        )
        if mcc_value is not None and mcc_value <= 0:
            reasons.append(
                f"'{stage_b_dir / 'metrics.json'}'.mcc_candidate.value={mcc_value!r} no cumple "
                "MCC_candidato_2023 > 0 requerido por 'CANDIDATE_VALIDATED'"
            )

    diagnostics: dict[str, Any] | None = None
    if bootstrap_payload.get("bootstrap_executed") is not True:
        reasons.append(
            f"'{stage_b_dir / 'bootstrap.json'}'.bootstrap_executed no es True: no hay "
            "intervalo bootstrap que sustente 'CANDIDATE_VALIDATED'"
        )
    else:
        # Dominio de ΔMCC (`[-2, 2]`), NUNCA el de un MCC aislado
        # (`[-1, 1]`) -- estos límites reportan una DIFERENCIA de dos MCC
        # (revisión dirigida, hallazgo 2, segunda ronda).
        lower_bound = _validate_bounded_metric(
            bootstrap_payload.get("interval_lower"),
            f"'{stage_b_dir / 'bootstrap.json'}'.interval_lower",
            reasons,
            lower=_DELTA_MCC_LOWER_DOMAIN,
            upper=_DELTA_MCC_UPPER_DOMAIN,
        )
        upper_bound = _validate_bounded_metric(
            bootstrap_payload.get("interval_upper"),
            f"'{stage_b_dir / 'bootstrap.json'}'.interval_upper",
            reasons,
            lower=_DELTA_MCC_LOWER_DOMAIN,
            upper=_DELTA_MCC_UPPER_DOMAIN,
        )
        if lower_bound is not None and upper_bound is not None:
            if lower_bound > upper_bound:
                reasons.append(
                    f"'{stage_b_dir / 'bootstrap.json'}': intervalo invertido "
                    f"(interval_lower={lower_bound!r} > interval_upper={upper_bound!r})"
                )
            elif lower_bound < -0.05:
                reasons.append(
                    f"'{stage_b_dir / 'bootstrap.json'}'.interval_lower={lower_bound!r} no "
                    "cumple el límite inferior >= -0.05 exigido por 'CANDIDATE_VALIDATED'"
                )

        diagnostics = bootstrap_payload.get("diagnostics")
        if not isinstance(diagnostics, dict):
            reasons.append(
                f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics ausente o no estructurado: "
                "no hay contabilidad de réplicas verificable que sustente el intervalo"
            )
        else:
            # Validación ESTRICTA y completa de los tres contadores
            # (revisión dirigida, hallazgo 1, segunda ronda): los tres deben
            # estar PRESENTES (nunca solo `replicas_valid` con los demás
            # ausentes) y ser enteros no booleanos no negativos -- solo
            # entonces se verifica `requested > 0`, `valid > 0`, y
            # `valid + discarded == requested`. Un contador ausente NUNCA se
            # trata como si fuera `0` ni se omite la verificación de
            # consistencia: se rechaza explícitamente antes de evaluar
            # cualquier otra condición sobre estos valores.
            def _nonnegative_int(value: Any) -> bool:
                return not isinstance(value, bool) and isinstance(value, int) and value >= 0

            replicas_valid = diagnostics.get("replicas_valid")
            replicas_requested = diagnostics.get("replicas_requested")
            replicas_discarded = diagnostics.get("replicas_discarded")
            invalid_counters = [
                counter_name
                for counter_name, counter_value in (
                    ("replicas_valid", replicas_valid),
                    ("replicas_requested", replicas_requested),
                    ("replicas_discarded", replicas_discarded),
                )
                if not _nonnegative_int(counter_value)
            ]
            if invalid_counters:
                reasons.append(
                    f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics: {invalid_counters} "
                    "ausente(s) o no son enteros no negativos válidos (recibido "
                    f"replicas_valid={replicas_valid!r}, "
                    f"replicas_requested={replicas_requested!r}, "
                    f"replicas_discarded={replicas_discarded!r})"
                )
            else:
                if replicas_requested <= 0:
                    reasons.append(
                        f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics.replicas_requested="
                        f"{replicas_requested!r} debe ser > 0"
                    )
                if replicas_valid <= 0 or 5 * replicas_valid < 4 * replicas_requested:
                    reasons.append(
                        f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics.replicas_valid="
                        f"{replicas_valid!r} no cumple el soporte de réplicas válidas "
                        "(>= 80 %) para el "
                        "intervalo bootstrap"
                    )
                if replicas_valid + replicas_discarded != replicas_requested:
                    reasons.append(
                        f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics: contabilidad de "
                        f"réplicas inconsistente (valid={replicas_valid!r} + discarded="
                        f"{replicas_discarded!r} != requested={replicas_requested!r})"
                    )

    if consumer_input_mode == INPUT_MODE_SYNTHETIC:
        if (
            contract.input_mode != INPUT_MODE_SYNTHETIC
            or resolved_config.get("scientific_run") is not False
            or resolved_config.get("input_mode") != INPUT_MODE_SYNTHETIC
        ):
            reasons.append(
                "Una ejecución de integración sintética de la Etapa C solo admite un candidato "
                "de A y una corrida de B ambos sintéticos (input_mode='synthetic', "
                "scientific_run=False), con coherencia explícita entre ambos campos de B"
            )
        if reasons:
            raise StageCAdmissibilityError(reasons)
        return

    if consumer_input_mode != INPUT_MODE_SCIENTIFIC:
        raise StageCAdmissibilityError(
            [f"input_mode de la ejecución consumidora desconocido: '{consumer_input_mode}'"]
        )

    # Una aprobación SINTÉTICA nunca habilita una Etapa C científica (decisión
    # operativa de este encargo, "Sobrescritura y autorización"). Se exige
    # coherencia EXPLÍCITA entre 'scientific_run' e 'input_mode' de la propia
    # ejecución de B -- un antecedente con input_mode='synthetic' pero
    # scientific_run=True (o viceversa) es internamente incoherente y nunca
    # habilita una Etapa C científica, aunque la bandera booleana sola diga
    # lo contrario (hallazgo de revisión dirigida).
    if resolved_config.get("scientific_run") is not True:
        reasons.append(
            f"'{stage_b_dir / 'resolved_config.json'}'.scientific_run no es True: una "
            "aprobación sintética de la Etapa B nunca habilita una Etapa C científica"
        )
    if resolved_config.get("input_mode") != INPUT_MODE_SCIENTIFIC:
        reasons.append(
            f"'{stage_b_dir / 'resolved_config.json'}'.input_mode="
            f"{resolved_config.get('input_mode')!r} no es 'scientific': incoherente con "
            "scientific_run declarado, no admisible como antecedente científico"
        )
    if contract.input_mode != INPUT_MODE_SCIENTIFIC or not contract.scientific_run:
        reasons.append(
            "El candidato de A no está marcado como científico en ambos ejes "
            f"(scientific_run={contract.scientific_run!r}, input_mode={contract.input_mode!r})"
        )

    # Una ejecución científica exige la configuración NORMATIVA de bootstrap
    # de B. La bandera `diagnostics.normative` declarada NUNCA es evidencia
    # suficiente por sí sola (revisión dirigida, hallazgo 1, tercera ronda):
    # se RECALCULA `bootstrap.compute_is_normative_configuration` sobre los
    # parámetros efectivos REALMENTE persistidos por esa réplica
    # (`replicas_requested`, `seed`, `block_length`) y se contrasta el
    # resultado contra la bandera declarada -- una configuración reducida,
    # ausente o contradictoria (por ejemplo, `normative=True` con
    # `replicas_requested=1`, `seed=0`, `block_length=1`) nunca habilita una
    # Etapa C científica, aunque la bandera booleana sola diga lo contrario.
    # Si `diagnostics` ya se rechazó arriba (ausente/no estructurado/
    # contadores inválidos), no se repite el motivo ni se intenta recalcular
    # sobre valores ya sabidos inválidos.
    if isinstance(diagnostics, dict):
        declared_normative = diagnostics.get("normative")
        diag_seed = diagnostics.get("seed")
        diag_block_length = diagnostics.get("block_length")

        def _valid_int(value: Any) -> bool:
            return not isinstance(value, bool) and isinstance(value, int)

        invalid_bootstrap_params = [
            param_name
            for param_name, param_value in (
                ("seed", diag_seed),
                ("block_length", diag_block_length),
            )
            if not _valid_int(param_value)
        ]
        if invalid_bootstrap_params:
            reasons.append(
                f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics: {invalid_bootstrap_params} "
                "ausente(s) o no son enteros válidos (recibido seed="
                f"{diag_seed!r}, block_length={diag_block_length!r}): no se puede verificar la "
                "configuración normativa real del bootstrap"
            )
        elif not _nonnegative_int(replicas_requested):
            # `replicas_requested` ya se rechazó arriba (contadores
            # inválidos): no se repite el motivo ni se recalcula sobre un
            # valor ya sabido inválido.
            pass
        else:
            recomputed_normative = compute_is_normative_configuration(
                replicas_requested, diag_seed, diag_block_length
            )
            if declared_normative is not True or not recomputed_normative:
                reasons.append(
                    f"'{stage_b_dir / 'bootstrap.json'}'.diagnostics no corresponde a la "
                    "configuración normativa real del bootstrap (recalculada a partir de "
                    f"replicas_requested={replicas_requested!r}, seed={diag_seed!r}, "
                    f"block_length={diag_block_length!r}: normativo={recomputed_normative!r}; "
                    f"declarado normative={declared_normative!r}): una ejecución científica de "
                    "la Etapa B exige la configuración normativa del protocolo (5000 réplicas, "
                    "semilla 20250109, bloques de 30 días) -- un bootstrap reducido, ausente o "
                    "contradictorio nunca habilita una Etapa C científica, aunque la bandera "
                    "declarada diga lo contrario"
                )
            else:
                # Coherencia con la configuración EFECTIVA registrada por B
                # en `resolved_config.json` (revisión dirigida, hallazgo 1,
                # tercera ronda): la semilla y el número de réplicas
                # efectivamente resueltos por la CLI de B deben coincidir con
                # los valores realmente consumidos por el bootstrap -- una
                # discrepancia es indicio de artefactos mezclados de corridas
                # distintas, aunque ambos luzcan normativos por separado.
                resolved_seed = resolved_config.get("seed")
                resolved_bootstrap_replicas = resolved_config.get("bootstrap_replicas")
                if resolved_seed is not None and resolved_seed != diag_seed:
                    reasons.append(
                        f"'{stage_b_dir / 'resolved_config.json'}'.seed={resolved_seed!r} no "
                        f"coincide con el seed efectivamente consumido por el bootstrap "
                        f"({diag_seed!r}): indicio de artefactos mezclados de corridas distintas"
                    )
                if (
                    resolved_bootstrap_replicas is not None
                    and resolved_bootstrap_replicas != replicas_requested
                ):
                    reasons.append(
                        f"'{stage_b_dir / 'resolved_config.json'}'.bootstrap_replicas="
                        f"{resolved_bootstrap_replicas!r} no coincide con replicas_requested "
                        f"efectivamente consumido por el bootstrap ({replicas_requested!r}): "
                        "indicio de artefactos mezclados de corridas distintas"
                    )

    # Evidencia de identidad del entrenamiento AUTORIZADO de B, requerida
    # explícitamente para el camino científico (revisión dirigida, hallazgo
    # 1, segunda ronda): se exige que exista y sea estructuralmente válida,
    # nunca que coincida con la huella del entrenamiento EXTENDIDO de C (ver
    # docstring del módulo) -- C amplía el período hasta 2023, por lo que su
    # propia huella (calculada en `stage_c_runner.py`) es deliberadamente
    # distinta.
    b_training_fingerprint = _load_producer_json(
        stage_b_dir, "training_dataset_fingerprint.json", StageCAdmissibilityError
    )
    try:
        validate_fingerprint_reference(
            b_training_fingerprint,
            f"'{stage_b_dir / 'training_dataset_fingerprint.json'}'",
        )
    except ValueError as exc:
        reasons.append(str(exc))

    b_code_identity = _load_producer_json(
        stage_b_dir, "code_version.json", StageCAdmissibilityError
    )
    if not b_code_identity.get("available"):
        reasons.append(
            "La identidad de código de la ejecución de B no está disponible "
            f"(reason={b_code_identity.get('reason')!r})"
        )
    if b_code_identity.get("dirty") is not False:
        reasons.append(
            "La identidad de código de la ejecución de B no reporta dirty=False "
            f"(dirty={b_code_identity.get('dirty')!r})"
        )
    b_commit = b_code_identity.get("commit")
    if not is_valid_full_sha(b_commit):
        reasons.append(
            f"La identidad de código de B no tiene un commit válido (commit={b_commit!r})"
        )

    if consumer_code_identity is None:
        reasons.append(
            "No se recibió la identidad de código de la ejecución consumidora de C (contexto "
            "explícito requerido)"
        )
    else:
        if not consumer_code_identity.get("available"):
            reasons.append(
                "La identidad de código de la ejecución consumidora de C no está disponible "
                f"(reason={consumer_code_identity.get('reason')!r})"
            )
        if consumer_code_identity.get("dirty") is not False:
            reasons.append(
                "La identidad de código de la ejecución consumidora de C no reporta "
                f"dirty=False (dirty={consumer_code_identity.get('dirty')!r})"
            )
        consumer_commit = consumer_code_identity.get("commit")
        if not is_valid_full_sha(consumer_commit):
            reasons.append(
                "La identidad de código de la ejecución consumidora de C no tiene un commit "
                f"válido (commit={consumer_commit!r})"
            )
        elif is_valid_full_sha(b_commit) and consumer_commit != b_commit:
            reasons.append(
                f"El commit de la ejecución de B ({b_commit!r}) difiere del commit de la "
                f"ejecución consumidora de C ({consumer_commit!r}) y no existe una política de "
                "compatibilidad documentada que acredite esa diferencia: se rechaza por "
                "compatibilidad no acreditada"
            )

    if consumer_environment_issues is None:
        reasons.append(
            "No se recibió evidencia de validación normativa del entorno de la ejecución "
            "consumidora de C (contexto explícito requerido)"
        )
    elif consumer_environment_issues:
        reasons.append(
            f"La ejecución consumidora de C registra fallas de validación de entorno: "
            f"{consumer_environment_issues}"
        )

    b_environment = _load_producer_json(stage_b_dir, "environment.json", StageCAdmissibilityError)
    if not b_environment.get("validated_before_training"):
        reasons.append(
            "La ejecución de B no registra validación normativa del entorno previa al "
            "entrenamiento"
        )
    if b_environment.get("validation_issues"):
        reasons.append(
            "La ejecución de B registra fallas de validación de entorno: "
            f"{b_environment['validation_issues']}"
        )
    constraints_identity = b_environment.get("constraints_identity")
    if not isinstance(constraints_identity, dict) or constraints_identity.get("exists") is not True:
        reasons.append(
            f"La ejecución de B no registra una identidad de 'constraints.txt' verificable "
            f"(constraints_identity={constraints_identity!r})"
        )
    else:
        recorded_sha256 = constraints_identity.get("sha256")
        if not is_valid_full_sha(recorded_sha256):
            reasons.append(
                f"El SHA-256 de 'constraints.txt' registrado por B no tiene formato válido "
                f"(sha256={recorded_sha256!r})"
            )
        else:
            current_constraints_identity = capture_constraints_identity()
            if (
                not current_constraints_identity["exists"]
                or current_constraints_identity["sha256"] != recorded_sha256
            ):
                reasons.append(
                    f"El SHA-256 de 'constraints.txt' registrado por B ({recorded_sha256!r}) no "
                    f"coincide con el archivo de referencia real "
                    f"({current_constraints_identity['sha256']!r})"
                )
    if not b_environment.get("packages"):
        reasons.append(
            "La ejecución de B no registra las versiones de paquetes efectivamente capturadas"
        )
    else:
        report = validate_environment(b_environment)
        if not report.ok:
            reasons.append(
                f"El entorno persistido de B no valida contra la referencia normativa "
                f"versionada: {report.issues}"
            )

    # Revalidación del vínculo HISTÓRICO A→B (revisión dirigida, hallazgo 2,
    # tercera ronda): reutiliza `check_stage_b_admissibility` -- el mismo
    # validador ya usado en la transición real A→B -- apuntado a la evidencia
    # PERSISTIDA de A (`producer_dir`) y de B (`stage_b_dir`), en vez de
    # confiar en que ya fue validada en su momento. Para esta comprobación
    # histórica, el productor es A y el CONSUMIDOR es la propia ejecución de
    # B ya persistida: se usa la identidad de código, el entorno y la huella
    # de entrenamiento REALES de B (`b_code_identity`, `b_environment`,
    # `b_training_fingerprint`, ya cargados arriba), nunca la identidad o el
    # entorno ACTUALES de la ejecución consumidora de C -- sustituir uno por
    # el otro dejaría pasar exactamente lo que esta revalidación existe para
    # atrapar (un `training_dataset_fingerprint.json` de B con `sha256`
    # distinto del de A, o un `producer_dir` al que le faltan
    # `code_version.json`/`environment.json`/`dataset_fingerprint.json`,
    # quedaban admitidos sin este llamado). Esta es una comprobación DISTINTA
    # de la compatibilidad B→C ya verificada arriba (identidad/entorno de la
    # ejecución consumidora de C contra B): ninguna sustituye a la otra.
    try:
        check_stage_b_admissibility(
            contract,
            producer_dir=producer_dir,
            consumer_input_mode=INPUT_MODE_SCIENTIFIC,
            consumer_code_identity=b_code_identity,
            consumer_environment_issues=b_environment.get("validation_issues"),
            consumer_training_dataset_fingerprint=b_training_fingerprint,
        )
    except StageBAdmissibilityError as exc:
        reasons.extend(f"Revalidación histórica A→B: {reason}" for reason in exc.reasons)

    if reasons:
        raise StageCAdmissibilityError(reasons)


__all__ = [
    "StageBAdmissibilityError",
    "StageCAdmissibilityError",
    "check_stage_b_admissibility",
    "check_stage_c_admissibility",
]
