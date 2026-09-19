**Veredicto crítico:** sin hallazgos materiales abiertos en el snapshot limpio y congelado `a0d8bf7412bbb68448cf3bcec262097cd1571ab3`. `sc-01` queda habilitado para auditoría independiente. Esto no constituye PASS de auditoría, readiness ni autorización para ejecutar A/B/C.

- **CRIT-PREP-01:** corregido. `sc-01` ahora delimita CL01..10 y R/H/N/S sin depender de resultados favorables:
  - R `NOT_REQUIRED` solo para clasificación P20.
  - H `REQUIRED` para cuantificar correcciones supervisadas simuladas, sin atribuir beneficio humano real.
  - N `NOT_REQUIRED` mientras no se afirme detección sobre reserva independiente.
  - S `NOT_REQUIRED` para el alcance limitado a etiquetas y ruido de v3, sin inferir sensores ausentes.
  - CL10 admite resultados negativos válidos de A/B y onset no definido cuando el soporte no alcanza.
- **CRIT-PREP-02:** corregido. El catálogo de modelos, el probe de sandbox y su archivo de custodia registran identidad, fuente, comandos, hashes, resultados y limitaciones. El probe solo demuestra el comportamiento observado; no acredita aislamiento global de agentes.
- **Probe:** preservado sin alterar bytes en `readiness-linux-2026-09-19/read-only-probe.txt`, SHA-256 `5f32a4bf1e4462d70cd8d17d805e297d88629a9745c2a6459d32e5ed9b548976`, con cadena de traslado documentada.
- **Integridad:** `verification-final.json` contiene 33 entradas verificadas sin discrepancias. SHA-256 del manifiesto: `cb472972c26d9f205367592003cba3d7455543f76474ed1131955624d9df7c06`.
- **Validación independiente:** 48/48 pruebas aprobadas; checker formal con salida `scientific-closure checker: PASS (estructura; runtime no verificado)`; `git diff --check` limpio; árbol Git limpio. La reproducción suplementaria desde checkout limpio confirmó esos resultados.
- **Custodia:** no se modificaron UI, código experimental, protocolo v3, ADR ni resultados históricos; no se inspeccionaron holdouts; A/B/C y el ledger permanecieron cerrados.

Siguen abiertos, correctamente documentados y fuera del cierre crítico de este snapshot:

- `CRIT-CHK-01..04`: faltan Ruff/Black reproducibles y PASS de auditor.
- `CRIT-SUB-01` / `SC-GOV-006`: no está acreditado el enforcement efectivo de modelo, esfuerzo y sandbox para todos los roles.
- Raw/runtime original Linux, Docker e imagen ejecutable ausentes.
- ADR-0011, identidad ejecutable, adquisición/licencias y backup/recuperación independiente pendientes.

Estos bloqueos impiden readiness y campaña científica, pero no impiden someter `sc-01` a auditoría independiente.

