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
| RK-05 | MITIGADO CON RESIDUAL | `provenance-and-licence-assessment.json`, decisión GD-13 con evidencia de fuente oficial | Fecha de adquisición `UNKNOWN`; términos históricos no verificados; `downloaded_service_version` `UNKNOWN` |
| RK-06 | PARCIALMENTE MITIGADO | `recovery-rehearsal.json`, `storage-and-backup-independence.json` | Segunda copia sigue siendo lógica: todas comparten device 2128. Bloqueo EXT-03 |
| RK-07 | ABIERTO — BLOQUEANTE | `code-identity-and-adr0011.json` precisa el estado exacto frente a `origin/main` actualizado | Condición 4 no satisfecha. Bloqueo EXT-01. Bloquea A, B y C |
| RK-08 | MITIGADO CON RESIDUAL | GD-12 vigente; `traceability.md` distingue estado del requisito y estado del change | H sigue `REQUIRED` y sin runner ni evidencia |
| RK-09 | PARCIALMENTE MITIGADO | `code-identity-and-adr0011.json`: `src/`, `docker/` y `pyproject.toml` en HEAD son byte-idénticos a `214735e` | La imagen no es inspeccionable; sin identidad de imagen verificada. Bloqueo EXT-02 |
| RK-10 | MITIGADO CON RESIDUAL | `agent-capabilities.json`: sustitución de modelos declarada; asignación de rutas con escritor único | Los perfiles `.codex/agents` no son cargables en este runtime; el modelo efectivo no es introspectable |
| RK-11 | MITIGADO | `role-sandbox-enforcement.json` y `tests/test_readonly_role_sandbox.py`: enforcement real verificado en Linux | El harness no coloca el proceso del subagente dentro del sandbox |
| RK-12 | ABIERTO | — | Los 994,22 s de la suite son sobre fixtures; no se extrapolan a tiempos científicos |
| RK-13 | NO APLICA TODAVÍA | — | No hubo campaña; el checkout ejecutable no fue modificado (`src/` intacto) |
