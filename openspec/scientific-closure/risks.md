# Riesgos, limitaciones y bloqueos

| ID | Riesgo / evidencia | Control y responsable | Bloquea |
| --- | --- | --- | --- |
| RK-01 | Confundir tests con eficacia (EV-02/05) | Crítico exige artefactos reales autorizados | Cierre científico |
| RK-02 | Un sitio, reanálisis, proxy P20; UTC-3 versus LST y latencia | Auditor limita CL-01..03/09; no validación agronómica | Afirmaciones no respaldadas |
| RK-03 | Autocorrelación/soporte pequeño/comparaciones múltiples | Bloques/soporte fijos, sin significancia simultánea no corregida | Selección/interpretación si soporte falla |
| RK-04 | Custodia incompleta/manipulación administrativa | Registro único, backups, responsable; SQLite no protege del administrador | Etapa afectada y dependientes |
| RK-05 | Adquisición/licencia histórica desconocida | sc-02: evidencia documental o decisión explícita de admisibilidad conforme ADR | Ejecución mientras no se resuelva |
| RK-06 | Segunda copia y restauración no acreditadas | Ensayo fixtures y comprobación independiente antes de campaña | sc-02 y A |
| RK-07 | Precondición main de ADR-0011 frente a correcciones de rama | sc-02: decisión documentada sin hacer merge ni alterar main | A; no bloquea preparación |
| RK-08 | Forzar cuatro complementos o retirarlos por conveniencia | sc-01: evidencia→afirmación→brecha, revisar alcance total | Cierre global si UNRESOLVED |
| RK-09 | SHA de docs distinto a imagen, tag mutable | Identidad dual; usar ID inmutable verificado toda A/B/C | Ejecución si identidad no concuerda |
| RK-10 | Config TOML válida pero rol no cargado o permisos heredados | Verificar carga/modelo/sandbox efectivo; no lectores con escritura | Orquestación dependiente |
| RK-11 | Sandbox Windows no inicia procesos | Error reproducido setup refresh; no certificar independencia no realizada | Validaciones que necesiten ese entorno |
| RK-12 | Duración científica no medida | Medir pared/CPU/memoria al ejecutar; no extrapolar fixtures | No bloquea método; estimación pendiente |
| RK-13 | Cambiar código a mitad A/B/C o complementar mirando C | Único ejecutable congelado; auxiliares aislados sin alimentar selección | Campaña si ocurre |

Cada riesgo permanece abierto hasta evidencia de mitigación, no hasta redactar
un plan. Registro operativo: ID, estado, responsable, evidencia, siguiente acción,
fecha y cambios dependientes suspendidos. No reducir criterios después de resultados.

## Estado de mitigación al 2026-09-20

Ningún riesgo se cierra por haber redactado un plan. Esta tabla registra
únicamente mitigaciones con evidencia verificable en
`readiness-resolution-linux-2026-09-20/`.

| ID | Estado | Evidencia de mitigación | Residual |
| --- | --- | --- | --- |
| RK-01 | ABIERTO | — | 486 pruebas verdes son evidencia técnica; la síntesis lo declara explícitamente y no atribuye eficacia |
| RK-02 | ABIERTO por diseño | — | Sitio único, reanálisis y proxy P20 son límites estructurales, no corregibles en esta campaña |
| RK-03 | ABIERTO | — | Sin corrida, no hay soporte que evaluar |
| RK-04 | ABIERTO | `recovery-rehearsal.json` (ensayo con fixtures, backup SQLite por API sobre base quiescente, contenido verificado) | Sin independencia física; custodia histórica no reconciliada |
| RK-05 | MITIGADO CON RESIDUAL | `provenance-and-licence-assessment.json`, decisión GD-13 con evidencia de fuente oficial | Fecha de adquisición `UNKNOWN`; términos históricos no verificados; `downloaded_service_version` `UNKNOWN`. **Corrección 2026-09-20 (C-08):** la condición 2 de ADR-0011 está resuelta **en sustancia**, no contra el manifiesto, que conserva `PENDING_CONFIRMATION`. El riesgo no se cierra por la decisión GD-13 |
| RK-06 | PARCIALMENTE MITIGADO | `recovery-rehearsal.json`, `storage-and-backup-independence.json`; topología reverificada el 2026-09-20 | Segunda copia sigue siendo lógica: todas comparten device 2128. Bloqueo EXT-03. Precisión añadida (E-04): el sistema de archivos raíz está respaldado por `ext4.vhdx` dentro del volumen C:, de modo que montar `/dev/sdd` no está demostrado que logre independencia física; el insumo faltante es almacenamiento no respaldado por el mismo volumen del host |
| RK-07 | ABIERTO — BLOQUEANTE | `code-identity-and-adr0011.json` precisa el estado exacto frente a `origin/main` actualizado; reverificado el 2026-09-20 | Condición 4 no satisfecha. Bloqueo EXT-01. Bloquea A, B y C. Precisión añadida: además de la sección de soporte ausente, la sección 4 del protocolo en `main` afirma un contrato de features falso, y `scientific-closure-decisions.md` y `scientific-closure-runbook.md` no existen en `main`. La divergencia es normativa, no cosmética |
| RK-08 | MITIGADO CON RESIDUAL | GD-12 vigente; `traceability.md` distingue estado del requisito y estado del change | H sigue `REQUIRED` y sin runner ni evidencia |
| RK-09 | PARCIALMENTE MITIGADO | Identidad de árboles y blobs reverificada el 2026-09-20: `src` (tree `0308057…`), `docker` (tree `84230fc…`) y `pyproject.toml` (blob `da4a2e9…`) en HEAD son byte-idénticos a `214735e` | La imagen no es inspeccionable **desde esta distro**; la imagen sí fue ejecutada el 2026-09-19 desde el host Windows (GD-21). Sin identidad de imagen verificada aquí. Bloqueo EXT-02, que además impide ejecutar A/B/C porque el runbook los invoca a través de `docker` |
| RK-10 | **ABIERTO — MATERIALIZADO** | `agent-capabilities.json`: sustitución de modelos declarada; asignación de rutas con escritor único | **Corrección 2026-09-20 (C-13):** el estado anterior `MITIGADO CON RESIDUAL` describía como residual un peligro que **ocurrió**: los perfiles `.codex/agents` no son cargables en este runtime y el modelo efectivo no es introspectable. Eso es exactamente el riesgo RK-10, no su residuo. Sostiene la degradación de SC-GOV-006 a `BLOCKED`. En esta sesión los tres roles lectores corrieron en contextos separados con solo lectura **instruida**, no impuesta |
| RK-11 | **MITIGADO CON RESIDUAL** | `role-sandbox-enforcement.json` y `tests/test_readonly_role_sandbox.py` (11 pruebas), reejecutado PASS de forma independiente el 2026-09-20 | **Corrección 2026-09-20 (C-13):** el `MITIGADO` sin calificar excedía la evidencia. El alcance verificado es solo lectura y ausencia de red **para procesos Linux**, con las dos vías de interop WSL conocidas cerradas; **no** es aislamiento absoluto y el propio registro declara que no se excluye una tercera capa. Las dos vías halladas (A-01 y NF-01) fueron encontradas por revisores independientes, no por las pruebas del mecanismo. Además el harness no coloca el proceso del subagente dentro del sandbox |
| RK-12 | ABIERTO | — | Los 994,22 s de la suite son sobre fixtures; no se extrapolan a tiempos científicos |
| RK-13 | NO APLICA TODAVÍA | — | No hubo campaña; el checkout ejecutable no fue modificado (`src/` intacto) |

## Riesgos añadidos por la verificación independiente — 2026-09-20

| ID | Riesgo / evidencia | Estado | Residual |
| --- | --- | --- | --- |
| RK-14 | Incumplimiento de la cláusula «no push en preparación»: dos pushes verificados en el reflog (C-02, GD-19) | ABIERTO — REGISTRADO, NO SUBSANADO | Los dos pushes existen y no pueden deshacerse sin reescribir historia publicada, lo que está prohibido. La instrucción vigente autoriza push hacia adelante; la ratificación del incumplimiento anterior corresponde al responsable |
| RK-15 | Revisión sin red: los tres revisores de la sesión anterior no pudieron consultar el estado remoto y ninguno detectó RK-14, aunque el reflog es local | ABIERTO | Toda revisión futura debe inspeccionar `git reflog show refs/remotes/<upstream>` y `git ls-remote` de forma explícita, no inferir el estado remoto de los documentos |
| RK-16 | Herramienta de validación que resuelve a un binario del host y valida un directorio distinto del repositorio, produciendo un resultado no reproducible (E-01, GD-20) | MITIGADO CON RESIDUAL | Documentada la precondición de `PATH`. Residual: cualquier herramienta invocada por nombre en este entorno puede resolver al binario de Windows; verificar la ruta absoluta antes de registrar un resultado |
| RK-17 | Estado terminal (`NOT_APPLICABLE`) atribuido a requisitos sobre una decisión de suficiencia no auditada (C-09, GD-23) | MITIGADO | Las tres filas se degradaron a `BLOCKED`. Residual: la decisión de fondo R/N/S `NOT_REQUIRED` sigue vigente y sigue pendiente de auditoría independiente |
