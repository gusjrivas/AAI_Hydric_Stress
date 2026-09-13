# Tareas — implement-controlled-daily-v4-stage-b-c

Ninguna tarea de este listado está completada. Este *change* es de código (cuando se
implemente); esta versión del archivo solo prepara la propuesta, el delta de
especificación y el propio checklist, sin escribir ningún módulo todavía. Las tareas
marcadas **[BLOQUEADA]** no deben iniciarse hasta que exista una decisión explícita
registrada en `docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`.

## Contrato de transferencia A→B

Dividido en dos partes que no deben mezclarse en una sola función: lectura/validación **estructural** (¿el artefacto se puede interpretar?) y validación de **admisibilidad** (¿este candidato puede usarse en esta ejecución concreta?). Ver `specs/experiment-runner/spec.md` de este *change* para el detalle de ambos requirements.

### Estructural (sin bloqueo — no depende de ninguna decisión abierta)

- [ ] Agregar `input_mode`, `scientific_run`, `schema_version` propio y referencia a `dataset_fingerprint` dentro de `frozen_config.json` (extensión de `artifacts.py`).
- [ ] Agregar `depth_role` (`primary_selection` | `sensitivity_only_no_selection_effect`) **únicamente en `frozen_config.json`** (propuesta por defecto de la Decisión 4), derivado de `--depth`. La existencia del campo no está bloqueada; solo su eventual duplicación en `selection_decision.json` es una pregunta abierta (Decisión 4), que no impide implementar la propuesta por defecto.
- [ ] Implementar la función de lectura/round-trip de `frozen_config.json` (reconstrucción de familia, hiperparámetros, `P20_train` final), exponiendo `input_mode`/`scientific_run`/`depth_role` sin decidir todavía si permiten continuar. Rechazo explícito de `schema_version` no soportado (estructural).
- [ ] Tests sintéticos: round-trip de escritura→lectura; rechazo de un `schema_version` no reconocido.

### Admisibilidad para una ejecución concreta (sin bloqueo — ver Decisión 4 solo para la ubicación de `depth_role`)

- [ ] Implementar la validación de admisibilidad en el punto de consumo de la Etapa B: acepta candidatos sintéticos cuando la ejecución que consume también es sintética (usando su propio registro de estado aislado, sin tocar el ledger científico); rechaza candidatos con `scientific_run=false`, con integridad no verificable, o con compatibilidad de procedencia fallida cuando la ejecución es científica (ver requirement "Compatibilidad de procedencia entre etapas" del delta).
- [ ] Implementar la verificación de integridad del autorreporte del productor (`code_identity`/`code_version.json`: commit presente, no marcado como inválido, `dirty=False` si el modo es científico) — sin comparar ese commit contra el commit actual de la ejecución consumidora; ambos pueden coincidir o diferir legítimamente, y ni la igualdad ni la diferencia entre ellos certifica nada por sí sola.
- [ ] Implementar la verificación de compatibilidad de procedencia: igualdad exacta de huella entre el conjunto de entrenamiento de B y el conjunto derivado de A (mismo período); para C, verificación de misma identidad de fuente/provenance que A (`provenance.py`/`manifest_reference.py`, mecanismo de H-01, reutilizado) más extensión de período según `STAGE_C_BOUNDS` — nunca una igualdad de huella entre C y A.
- [ ] Implementar el rechazo por `depth_role` en el punto de consumo de la Etapa B, siempre como error duro (no está bloqueado: la severidad y el punto de verificación ya están resueltos — ver Decisión 4). Solo si en el futuro se decide duplicar `depth_role` en `selection_decision.json` con verificación cruzada, esa parte adicional queda pendiente de esa decisión.
- [ ] Tests sintéticos: un candidato sintético es admisible para una ejecución de integración sintética (con su propio registro aislado); un candidato sintético se rechaza para una ejecución científica; un candidato con `scientific_run=true` pero integridad de código no verificable se rechaza igual; un candidato de B con huella de entrenamiento distinta de la de A se rechaza; un candidato de C cuya fuente/provenance no coincide con la de A se rechaza, mientras que uno cuya huella simplemente difiere de la de A por incorporar 2023 se acepta (no se exige igualdad); un candidato con `depth_role=sensitivity_only_no_selection_effect` se rechaza en el punto de consumo de la Etapa B, siempre como error duro.

## Baselines del protocolo (sección 13)

- [ ] Implementar `predict_majority_class_baseline` (aprende exclusivamente de las etiquetas del `train` autorizado — acceso legítimo y requerido, no una fuga), `predict_persistence_baseline_v4` (usa la humedad actual y `P20_train`; nunca consulta la humedad futura de la fila evaluada) y `predict_constant_stress_baseline` (predice `1` siempre, sin ajustar ningún parámetro), parametrizados por el `train` autorizado de cualquier etapa.
- [ ] Tests sintéticos: clase mayoritaria coincide con `argmax` del conteo de etiquetas de `train` (verificando que el acceso a esas etiquetas ocurre y es correcto, no prohibiéndolo); igualdad exacta con `P20_train` produce clase 0 en persistencia; ninguno de los tres baselines consulta `future_soil_moisture` de la fila evaluada; ninguno de los tres cambia su regla al variar las etiquetas del conjunto de evaluación (manteniendo fijas las de `train`).

## Etapa B

- [ ] **[BLOQUEADA — decisión 1]** Implementar el bootstrap de `ΔMCC_B` reutilizando `bootstrap.paired_bootstrap_delta` sobre las predicciones evaluables de 2023, según la interpretación de segmentación que se apruebe.
- [ ] Implementar el reentrenamiento del candidato congelado (leído vía el contrato de transferencia) con `target_timestamp ≤ 2022-12-31`, evaluación única sobre 2023.
- [ ] Implementar el veredicto `CANDIDATE_VALIDATED`/`CANDIDATE_NOT_VALIDATED` exacto (protocolo, sección 10): `MCC_candidato_2023 > 0` **y** límite inferior del intervalo pareado de `ΔMCC_B ≥ −0.05`; monoclase en OOF de A o en 2023 ⇒ no validable.
- [ ] Reemplazar `holdout_status.json` (hoy literal constante) por un estado derivado real del veredicto persistido.
- [ ] Habilitar `--stage B` en la CLI, condicionado a la existencia de un `frozen_config.json` válido.
- [ ] Tests sintéticos: los 4 cuadrantes del veredicto; caso monoclase en 2023; verificación de que un `CANDIDATE_NOT_VALIDATED` deja el holdout cerrado de forma verificable; centinela de que ningún dato de 2024–2025 se toca durante la Etapa B.

## Etapa C

- [ ] **[BLOQUEADA — decisión 2]** Implementar el registro persistente (ledger) del holdout, keyado por la identidad estable del holdout (protocolo + sitio + profundidad + período — no por commit/candidato/`--output-dir`), con tres estados posibles por identidad de holdout (`AUSENTE`/`CONFIRMADA`/`INDETERMINADA`), inicialización explícita versionada en Git (estado inicial `AUSENTE`, nunca inferido de la ausencia del archivo) y un ledger sintético completamente separado del científico, según el diseño que se apruebe.
- [ ] **[BLOQUEADA — decisión 2]** Implementar la secuencia de apertura en este orden exacto, sin alterarlo: (1) verificar veredicto `CANDIDATE_VALIDATED` de B, autorización (`--authorized-by`) y precondiciones de entorno — sin tocar ningún dato de 2024–2025; (2) consultar el estado del ledger para esta identidad de holdout — proceder a reservar solo si es `AUSENTE`; rechazar de inmediato si es `CONFIRMADA` o `INDETERMINADA`, sin distinguir entre ambas a los efectos del rechazo; (3) si la reserva se obtiene, escribir el registro de apertura con `fsync` explícito del archivo (y del directorio, cuando el mecanismo lo permita) antes de considerarlo confirmado — **no reutilizar `artifacts._atomic_write_text` sin agregar el `fsync` que hoy no tiene**; (4) recién entonces, cargar y evaluar datos de 2024–2025; (5) escribir una marca de finalización separada al terminar de serializar los resultados.
- [ ] Implementar el reentrenamiento con `target_timestamp ≤ 2023-12-31` y `P20_train` recalculado en ese rango (paso 4 de la secuencia anterior).
- [ ] Implementar la evaluación única sobre `[2024-01-04, 2025-12-31]` (paso 4), condicionada a que los pasos 1-3 se hayan completado exitosamente y de forma durable.
- [ ] **[BLOQUEADA — decisión 3]** Definir la política de `--overwrite` para `--stage C` (prohibición incondicional, o confiar exclusivamente en el ledger de la decisión 2).
- [ ] Habilitar `--stage C` en la CLI, con las restricciones que resulten de las decisiones 2 y 3.
- [ ] Documentar y, donde sea posible, verificar con test sintético los dos estados terminales excepcionales, ambos sin reintento automático y sin borrado/reinicialización silenciosa del registro: (a) apertura confirmada (paso 3) sin marca de finalización (paso 5); (b) registro `INDETERMINADA` (interrupción durante los pasos 2-3). Ambos requieren intervención humana fuera de la CLI (ver Decisión 2 del documento de decisiones).
- [ ] Tests sintéticos: rechazo si no hay `CANDIDATE_VALIDATED` previo; la reserva del paso 2 rechaza una segunda apertura con la misma identidad de holdout cuando el estado es `CONFIRMADA`, aunque cambien el commit, el candidato congelado o `--output-dir`; la reserva también rechaza cuando el estado es `INDETERMINADA` (simulado forzando una interrupción a mitad del paso 2/3), sin borrar ni reinicializar ese registro; un fallo simulado *antes* de cualquier intento de reserva (estado `AUSENTE`) deja el holdout intacto y permite un reintento completo; un fallo simulado *después* de que el paso 3 se confirmó de forma durable (durante la evaluación o la escritura) deja el holdout marcado `CONFIRMADA` de forma permanente, sin reintento automático; una invocación posterior con la marca de finalización (paso 5) ya presente recupera el resultado existente en vez de reevaluar; el ledger sintético de un test de integración nunca modifica ni consulta el ledger científico.

## Integración y documentación

- [ ] Test de integración sintética de punta a punta A→B→C (con fixtures sintéticas, sin CSV reales) verificando que un `CANDIDATE_NOT_VALIDATED` en B detiene la cadena antes de tocar cualquier dato de 2024–2025.
- [ ] Completar los campos `stage_b_result`/`stage_c_result` del manifiesto de provenance (hoy `PENDING_BEFORE_EXECUTION`) únicamente cuando exista una ejecución real que los sustente — no antes.
- [ ] Actualizar `openspec/specs/experiment-runner/spec.md` (canónico) para reflejar las capacidades de B y C una vez que el código de este *change* esté integrado y verificado con pruebas sintéticas — el mismo criterio de "implementado" ya usado para la Etapa A (código integrado + verificación sintética, siguiendo el flujo OpenSpec del repositorio), **no** condicionado a que exista una ejecución científica real. Las ejecuciones científicas de A, B y C y sus resultados siguen pendientes por separado (ver la tarea anterior) y se documentan como tales independientemente de esta actualización — esta tarea no cierra ni da por completada ninguna ejecución real, solo el estado de implementación del código.
