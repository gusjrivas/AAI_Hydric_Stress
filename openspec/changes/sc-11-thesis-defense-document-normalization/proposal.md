# Normalizar la narrativa documental para tesis y defensa

## Why

Los resultados de `controlled_daily_v4` y del complemento H están preservados,
pero varios puntos de entrada conservan estados intermedios que contradicen el
cierre administrativo fijado por GD-40. La tesis necesita una narrativa única,
honesta y defendible que distinga evidencia numérica real de confirmación
protocolar.

## What Changes

- Se agrega una cabecera vigente que supersede, sin borrar, los estados
  históricos incompatibles.
- Se fija como estado canónico: RB-05 ejecutada con veredicto `FAIL`;
  `sc-06-scientific-synthesis`, `SC-GOV-025` y `GF` en `FAIL`; H ejecutado y
  auditado; R/N/S `NOT_APPLICABLE` a nivel requisito y sus changes bloqueados
  por gate negativo.
- B y C se presentan exclusivamente como evidencia retrospectiva exploratoria,
  nunca como validación confirmatoria.
- Se incorpora una posición breve para la defensa de tesis.
- Tras la crítica `CRIT-SC11-01..03`, la posición separa tres carriles de
  evidencia, documenta la semántica real de alerta del ensamble y distingue el
  review v2/histórico de la recalibración legacy/HU5.

No se ejecuta ninguna campaña, no se inspeccionan valores reservados, no se
reabre el holdout y no se modifica evidencia histórica.

## Trazabilidad

- HU afectadas: HU7 y HU8.
- Capacidades: `scientific-closure` (gobernanza y narrativa) y
  `experiment-runner` (resultados referenciados, sin modificar contratos).
- CRISP-DM: evaluación y documentación.
- Memoria: capítulos 2, 3, 4 y 5.
- Configuración experimental: sin impacto.
- Hipótesis, alcance y arquitectura: sin cambios.

## Dependencias y autoridad

Este cambio documental parte de decisiones y evidencia ya registradas: RB-03,
la ejecución y auditoría de H, RB-05 con veredicto `FAIL`, y GD-40. La
instrucción explícita de normalización autoriza únicamente las rutas listadas
en este change. No modifica `changes.json` ni se autoaprueba.

## Archivos autorizados

- `openspec/changes/sc-11-thesis-defense-document-normalization/`
- `openspec/scientific-closure/README.md`
- `openspec/scientific-closure/current-execution-checkpoint.md`
- `openspec/scientific-closure/next-session.txt`
- `openspec/scientific-closure/traceability.md`
- `openspec/scientific-closure/claims.md`
- `docs/research/scientific-closure-synthesis-2026-09-22.md`
- `docs/research/thesis-defense-position.md`
- `openspec/changes/sc-06-scientific-synthesis/tasks.md`

## Archivos excluidos

Todos los no listados, en especial `changes.json`, `src/`, `tests/`, UI,
protocolos v3/v4, evidencia científica, ledgers, resultados y `.codebase-memory`.

## Acceptance

- Todos los puntos de entrada expresan el mismo estado vigente.
- Ninguna frase vigente afirma que B o C confirman la hipótesis o que la
  campaña cumplió la secuencia de gates.
- Los registros históricos permanecen visibles y marcados como superseded.
- No quedan tareas experimentales v4 pendientes ni instrucciones de reabrir o
  repetir el holdout.
- La posición de defensa separa contribuciones, resultados, límites y
  afirmaciones prohibidas.
- La posición incluye una tabla autocontenida de v3, v4 A/B/C/H y ensamble
  demostrativo, sin transferir autoridad científica entre carriles.
- Declara que la alerta vigente usa el promedio aritmético de tres
  probabilidades con umbral 0,5; votos/categoría son metadata, mayoría queda
  pendiente y `display_probability` no está calificada.
- Distingue el registro de review v2/histórico, que no modifica bundles ni
  recalibra, del endpoint legacy/HU5 manual de un solo modelo y de H simulado.

## Validation

- `git diff --check`
- búsquedas dirigidas de estados y expresiones contradictorias
- validación OpenSpec estricta del change, si el CLI disponible lo permite

## Rollback

Revertir solamente este delta documental. Nunca alterar ni eliminar evidencia,
eventos o informes históricos para cambiar el sentido del veredicto.
