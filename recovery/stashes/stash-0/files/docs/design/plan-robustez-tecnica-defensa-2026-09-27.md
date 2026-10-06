# Plan de robustez técnica y científica para defensa de maestría

**Fecha:** 2026-09-27

**Origen:** auditoría de arquitectura sobre el grafo indexado (`codebase-memory-mcp`,
`C-Repo-AAI_Hydric_Stress`, snapshot `57c0a86`) más relevamiento de estado de
`openspec/scientific-closure/`, `docs/seguimiento-tareas.md` y suites de test
(2026-09-27).

**Carácter del documento:** plan de ejecución para Codex. No es una spec OpenSpec,
no autoriza HU7/HU8 A/B/C ni reapertura de holdouts, no reemplaza
`docs/research/protocolo-experimental-v3.md` ni las decisiones registradas en
`openspec/scientific-closure/decisions.md`.

## 0. Restricción no negociable — leer antes de ejecutar cualquier tarea

El cierre científico HU7/HU8 sobre `controlled_daily_v4` **ya terminó, en FAIL,
de forma deliberada e irreversible** (GD-40, `openspec/scientific-closure/decisions.md`,
2026-09-22): la no conformidad se aceptó como "desviación histórica permanente e
irreparable", el holdout consumido no se reabre, y una confirmación futura
"requeriría datos nuevos y sería otro trabajo, no una reparación de esta campaña".

En consecuencia, ninguna tarea de este plan puede:

- reejecutar o revalidar A/B/C/H de `controlled_daily_v4`;
- abrir el holdout final;
- modificar `controlled_daily_v3` salvo bug metodológico demostrado (AGENTS.md);
- tratar el resultado FAIL como un error a corregir (no lo es: ausencia de mejora
  o resultado negativo válido no se "arregla").

Si una tarea de Track C requiere tocar algo de lo anterior, se detiene y se
registra como `BLOCKED`, no se reinterpreta el alcance.

## Track A — Cierre de hallazgos de la auditoría de arquitectura

Riesgo: bajo. No toca hipótesis, arquitectura ni experimentos.

### A1. Documentar la limitación del extractor de `codebase-memory-mcp`

El detector de "código muerto" del grafo no reconoce `Depends(...)` de FastAPI
ni callbacks referenciados en JSX (`onClick={fn}`). Se verificaron como falsos
positivos: `backend/app/config.py` / `dependencies.py` (funciones `is_*_enabled`,
`require_*_enabled`), y en frontend `ForecastCard.cancel`,
`RecalibrationPanel.handleRecalibrate`, `HistoricalReplayPage.resetClock`.

- Agregar una nota breve en este mismo archivo de plan (sección "Notas de
  cierre" al final, tras ejecutar) o en un comentario de una línea en el README
  de auditorías si existe uno — **no crear un documento nuevo solo para esto**.
- No requiere cambio de código.

### A2. Blindar `OperationalRepository` (`src/human_feedback/operational_repository.py`)

Concentración real de dependencias: alto fan-in cruzando backend, tests y
`docker/producer-preview/prepare.py`. No se propone refactor (fuera de alcance
sin pedido explícito), sí blindaje antes de que alguien lo toque sin saber el
blast radius:

- Revisar que exista cobertura de test sobre la interfaz pública de
  `OperationalRepository` (no solo sobre los 3 llamadores directos detectados:
  `backend/app/dependencies.get_operational_repository` y
  `docker/producer-preview/prepare.py` x2). Si falta cobertura de algún método
  público, agregar tests — no cambiar la implementación.
- Documentar en un docstring corto (una línea, solo si no existe ya) que esta
  clase es punto de alto acoplamiento y cambios de firma requieren revisar
  todos los llamadores vía `grep -rn "OperationalRepository"`, no solo vía el
  grafo (por la limitación de A1 con patrones indirectos).

### A3. Cerrar el punto de "código muerto" sin acción

No hay dead code real confirmado tras verificación manual. No ejecutar ninguna
eliminación de código a partir de resultados del grafo sin confirmar primero
con `grep` (lección de A1).

## Track B — Robustez técnica general (backend/frontend)

Riesgo: bajo. Mejora defendibilidad ante preguntas de jurado sobre calidad de
ingeniería, sin tocar resultados experimentales.

### B1. Medir cobertura de tests (sin gate estricto todavía)

Estado relevado: 894 tests backend pasan (3 skipped), 162 tests frontend pasan
(vitest, 23 archivos), `npm run build` limpio. No hay `pytest-cov` ni
`.coveragerc` configurado — no hay visibilidad de qué % de código está cubierto.

- Agregar `pytest-cov` a las dependencias de test y un `.coveragerc` (o
  configuración equivalente en `pyproject.toml`) que excluya migraciones,
  fixtures y código generado.
- Correr la suite completa con cobertura y guardar el reporte (no fijar un
  umbral mínimo todavía — primero medir, luego decidir si hace falta un gate,
  eso es una decisión de HU4/HU6 fuera de este plan).
- Reportar el % global y los 3-5 módulos con menor cobertura en
  `docs/seguimiento-tareas.md`, sin implicar que baja cobertura sea per se un
  bug.

### B2. Cerrar pendiente conocido de `add-causal-historical-replay` (HU7/HU8)

Documentado en `docs/seguimiento-tareas.md` como pendiente no bloqueante:
`GET /replay/history` no distingue `medida` / `imputada` / `no_determinado`
por fila.

- Ubicar el endpoint (`backend/app/routers/replay.py` según hallazgo de
  auditoría) y el modelo de respuesta Pydantic asociado.
- Agregar el campo de distinción por fila si el dato de origen ya lo permite
  (`data_ingestion.schema` u origen equivalente). Si el dato de origen no lo
  distingue, documentar la limitación explícitamente en la respuesta/schema en
  vez de inferir el valor (regla de AGENTS.md: "prohibido completar evidencia
  faltante mediante inferencias" aplica también a este tipo de dato).
- Agregar test que cubra explícitamente una fila medida y una imputada.

### B3. Probar escritura concurrente de feedback para la misma predicción

Pendiente documentado, no probado: dos escrituras concurrentes de feedback
sobre la misma predicción (`human-feedback`, HU5).

- Escribir un test de concurrencia (dos requests simultáneas o secuencia que
  fuerce condición de carrera) contra el endpoint de feedback.
- Si aparece una condición de carrera real, corregir con el mecanismo mínimo
  necesario (lock optimista o constraint de base de datos) — no rediseñar el
  flujo de feedback.

### B4. Validación de contratos backend↔`data_ingestion.schema`

Verificar puntualmente (no auditoría exhaustiva) que los modelos Pydantic de
request/response en los routers reflejan los nombres de columnas de
`data_ingestion.schema`, como exige la skill `backend-python-fastapi-mlflow`.
Si se encuentra una discrepancia de nombres, corregirla; si no se encuentra
ninguna, cerrar el punto sin cambios.

## Track C — Robustez científica dentro del alcance permitido por GD-40

Riesgo: requiere criterio. No hay cambios de código en este track, solo
verificación editorial/documental.

### C1. Verificar consistencia de la posición de defensa

- Contrastar `docs/research/thesis-defense-position.md` contra
  `openspec/scientific-closure/decisions.md` (GD-40) y el README canónico de
  `openspec/scientific-closure/` para confirmar que no hay contradicciones de
  fecha, alcance o redacción entre los tres documentos.
- Si se detecta una inconsistencia, reportarla como hallazgo — no resolverla
  unilateralmente reescribiendo la posición de defensa sin que el usuario la
  revise, dado que es contenido de defensa de tesis.

### C2. Verificar que `add-causal-historical-replay` no excede su alcance declarado

Este change (HU7/HU8) opera sobre `base-seed4` / `controlled_daily_v3`, no
sobre `controlled_daily_v4`. Confirmar que ningún archivo tocado por B2/B3
(Track B) introduce una dependencia accidental hacia artefactos de
`controlled_daily_v4` o hacia el holdout. Si aparece alguna referencia,
detener y reportar como `BLOCKED`, no removerla sin entender por qué está.

### C3. No generar nueva narrativa científica

Este plan no produce afirmaciones nuevas sobre desempeño de modelos,
comparaciones A/B/C, ni conclusiones. Cualquier necesidad de ese tipo que
surja durante la ejecución se registra como fuera de alcance y se deriva al
protocolo formal de `openspec/scientific-closure/` (roles R/H/N/S), no se
resuelve dentro de este plan.

## Reglas de ejecución para Codex

- Un cambio acotado por tarea (A1-A3, B1-B4, C1-C3 son unidades independientes;
  no mezclar varias en un solo commit).
- Antes de tocar código: leer `AGENTS.md`, la spec de la capacidad afectada en
  `openspec/specs/`, y el ADR correspondiente (0003 backend-facade, 0009
  contratos temporales, 0013 backend-ui-productor según la tarea).
- Ejecutar los tests afectados después de cada tarea; no avanzar a la
  siguiente con tests rotos.
- No hacer push, merge, PR, rebase, tag ni release sin aprobación explícita
  del usuario en cada caso — la aprobación de una tarea no autoriza las
  siguientes.
- No tocar `.codex/agents/*.toml` (roles del protocolo scientific-closure) ni
  invocar `scientific_explorer`/`scientific_implementer`/`evidence_checker`/
  `scientific_critic`/`scientific_auditor` para nada de este plan — Track C es
  documental, no requiere el protocolo formal de cierre.
- Registrar cada tarea completada en `docs/seguimiento-tareas.md` siguiendo el
  formato existente (HU/capacidad, fase CRISP-DM, impacto, evidencia).

## Orden sugerido

1. A3 (cierre sin acción, 5 min) → A1 (nota breve, 15 min).
2. B1 (medir cobertura, base para priorizar) → B4 (validación de contratos,
   acotado) → A2 (blindaje de tests sobre `OperationalRepository`).
3. B2 y B3 (requieren entender el dato de origen y el flujo de escritura;
   hacer después de tener cobertura visible de B1 para saber si ya hay tests
   parciales que reutilizar).
4. C1 y C2 al final, como verificación de cierre — no bloquean A/B.
