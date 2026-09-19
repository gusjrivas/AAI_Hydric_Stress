Veredicto principal: **BLOCKED**

Objeto auditado: rama `feat/scientific-closure`, snapshot limpio `a0d8bf7412bbb68448cf3bcec262097cd1571ab3`, upstream `origin/feat/scientific-closure`, observado el `2026-09-19T08:34:25Z`.

Veredicto acotado `sc-01-evidence-scope`: **PASS**

Veredicto readiness integral para ejecutar A: **BLOCKED**

Rol asignado: `scientific_auditor`, `gpt-5.6-sol`, esfuerzo `xhigh`, sandbox nominal `read-only`. Modelo y esfuerzo efectivos no son introspectables. El sandbox efectivo heredado permite escritura (`danger-full-access`); mantuve conducta de solo lectura. Esta degradación bloquea SC-GOV-006/CRIT-SUB-01 para readiness, aunque no impidió inspeccionar independientemente el snapshot.

Comprobaciones personales:

- Ruta, rama, HEAD y upstream correctos; árbol limpio antes y después.
- 33/33 pruebas del checker: PASS.
- Suite combinada: 48/48 pruebas: PASS.
- Checker formal: `PASS (estructura; runtime no verificado)`.
- 17 JSON y seis TOML parseados correctamente.
- Manifiesto de 33 archivos en `verification-final.json`: cero discrepancias de hash o tamaño.
- `git diff --check`: PASS.
- Diff desde `329cb60` sobre `frontend`, `backend`, `src`, `data`, `docs/research` y `docs/adr`: vacío.
- Reproducción suplementaria en clon limpio revisada: mismo HEAD, 48/48 y checker estructural PASS; usa Python 3.14.4 del host y no acredita reproducción científica.
- Hashes preservados:
  - protocolo v3: `3d8528e89eb235c94e71d536706292b99badc5c29557a71e917d641898940892`
  - protocolo v4: `e3fa7b6644171d0f80cfca6f3088e3e1fec44a0a6e63990deb05c26af5f8218a`
  - ADR-0011: `a8dabbc4b85367d5fb473195972870fb5c7de43ed5726a99910e3fed8c83d9cb`
  - referencia v3 JSON/tabla: `b876d21c…b45a` / `29639c48…d47c`
  - probe archivado: 131 bytes, modo `0755`, `5f32a4bf…976`
- Artefactos principales:
  - `verification-final.json`: `cb472972c26d9f205367592003cba3d7455543f76474ed1131955624d9df7c06`
  - `claims-assessment.json`: `2c42d693a8cfd21aa6fd09ce00ba401aaa53d4c1ce683d24e6a47ebb5463a0dd`
  - `inventory.json`: `a917ed693815ca5d127c156e56941b5c213353047bea919881877bfea4d67030`
  - `preservation.json`: `944262470a34b91f5a1296f8c520a5239125d7fbaf274b1e33639bb8ed8f31d5`
  - `session-identity.json`: `e4e554231cd4633dfa9cf2cd536db1045ae9432509e8ce6a6c149101e19f6eae`

Fundamento del PASS acotado:

- SC-GOV-001, 003, 004 y 005 quedan satisfechos en el snapshot.
- CL-01..10 están presentes, diferenciando evidencia referenciada, faltantes y evidencia científica futura.
- No se afirman resultados futuros ni se reducen hipótesis tácitamente.
- R=`NOT_REQUIRED` se limita a clasificación P20.
- H=`REQUIRED` para cuantificar correcciones simuladas y no acredita beneficio humano real.
- N=`NOT_REQUIRED` excluye detección reservada, anomalías reales y fallas reales.
- S=`NOT_REQUIRED` se limita a etiquetas escasas y ruido históricos, excluyendo sensores ausentes.
- CL-10 admite terminales negativos válidos y soporte insuficiente, exige H auditado y no certifica HU1 ni la tesis completa.
- No quedan afirmaciones `UNRESOLVED`.
- No encontré hallazgos materiales reproducibles dentro del alcance documental de `sc-01`.

Bloqueos reproducibles de readiness:

- `AUD-READ-01`, crítico, SC-GOV-009/013/014: `/home/gus/work/AAI_Hydric_Stress_scientific_runtime` y `/home/gus/work/AAI_Hydric_Stress_external_data/raw` están ausentes. No puede verificarse custodia original, primer intento, estado real de holdouts, datos ni hashes. Crear raíces nuevas no resolvería la historia.
- `AUD-READ-02`, crítico, SC-GOV-009/020: Docker, socket Docker, Ruff, Black y npx no están disponibles. La imagen referenciada `sha256:55bc923e…b297af`, el ejecutable `214735e…bf3`, dependencias, lint, formato y OpenSpec estricto no pudieron verificarse en este entorno.
- `AUD-READ-03`, crítico, SC-GOV-006: no existe evidencia de carga y aislamiento efectivo de los cinco roles. El probe demuestra EROFS solo para una invocación aislada del CLI; no acredita los canales de herramientas de las sesiones.
- `AUD-READ-04`, alto, SC-GOV-017: adquisición efectiva, versión histórica y licencia aplicable de NASA POWER continúan desconocidas. Las páginas oficiales actuales no prueban la procedencia de los CSV históricos.
- `AUD-READ-05`, alto, SC-GOV-018: no hay segunda copia independiente, backup reconciliado ni ensayo de restauración acreditado.
- `AUD-READ-06`, crítico, ADR-0011 condición 4: `git merge-base --is-ancestor 214735e… origin/main` devuelve 1 y el protocolo difiere. La precondición de estar incorporado en `main` no está satisfecha en la referencia local disponible.
- `AUD-READ-07`, alto: `sc-02-runtime-readiness` sigue `PLANNED`; faltan `authorizations.json`, `agent-capabilities.json`, `execution-manifest.json`, `provenance-assessment.json`, `recovery-rehearsal.json`, `checkpoints.json` y `structural-validation.json` auditables.
- `AUD-READ-08`, alto: CRIT-CHK-01..04 no pueden cerrarse sin Ruff/Black y auditoría del alcance completo del checker.

No se ejecutaron A/B/C ni auxiliares, no se inicializó ledger, no se inspeccionaron holdouts y no se produjeron métricas científicas. El PASS de `sc-01` permite registrar ese change como cerrado por el orquestador; no habilita `sc-02`, A ni ninguna apertura hasta resolver y auditar los bloqueos anteriores.

