# Reconciliación RB-03/04/05/06 — `65ca852` vs `f355272`

Dos líneas de trabajo divergieron desde el mismo commit `1c33aad` el 2026-09-22:

- **`feat/scientific-closure`** (esta rama), commits `2185ed4` → `6878184` →
  `65ca852`: resolvió **RB-03** (decisión de suficiencia GD-12 sobre R, N y S),
  con crítica y auditoría independientes, ambas registradas y `PASS`.
- **`feat/scientific-evidence-finalization`** (PR #211), commits `7e63d1c` →
  `0dbc976` → `f355272`: intentó resolver **RB-03 + RB-04 + RB-05 + RB-06** en
  una sola campaña, con dos rondas de auditoría final que terminaron en
  veredicto formal `FAIL`.

Instrucción del responsable: `65ca852` es la fuente autoritativa para RB-03; de
`f355272` sólo se recuperan selectivamente los entregables útiles de
RB-04/05/06; ningún `FAIL` se presenta como aprobación; la renuncia del auditor
a una tercera ronda no sustituye a un `PASS`.

## Archivos tocados, por rama (desde `1c33aad`)

| Archivo | `65ca852` | `f355272` |
| --- | --- | --- |
| `openspec/scientific-closure/changes.json` | sc-07/09/10 BLOCKED (applicability_decision) | sc-06 PASS; sc-07/09/10 BLOCKED |
| `openspec/scientific-closure/decisions.md` | GD-30..GD-32 | GD-33..GD-39 (numeración propia, no reutilizada aquí) |
| `openspec/scientific-closure/traceability.md` | Sección RB-03 (SC-GOV-021/023/024 → NOT_APPLICABLE) | «Matriz final» completa (25 filas), incluye SC-GOV-025/GF → PASS_WITH_LIMITATIONS |
| `openspec/scientific-closure/claims.md` | (no tocado) | «Clasificación final de afirmaciones» |
| `openspec/scientific-closure/plan.md` | (no tocado) | Sección «Estado de los gates», GF → PASS_WITH_LIMITATIONS |
| `openspec/scientific-closure/README.md` | (no tocado) | Enlaces a su propio directorio y síntesis |
| `docs/research/scientific-closure-synthesis-2026-09-22.md` | no existe | síntesis completa de A/B/C/H |
| `evidence-finalization-2026-09-22/thesis-traceability.md` | no existe | trazabilidad caps. 2/3 |
| `evidence-finalization-2026-09-22/auxiliary/{R,N,S}/review.json` | no existe (usa los de `sufficiency-review-2026-09-22/`) | versión propia, sin crítica adversarial documentada aparte de la auditoría única |
| `evidence-finalization-2026-09-22/reviews/*.md` | no existe | dos informes de auditoría, ambos `FAIL` |
| `openspec/changes/sc-0{7,9,10}-*/reviews/` | crítica + auditoría verbatim, `PASS` | no tocado |
| `sufficiency-review-2026-09-22/` | dossier GD-12, R/N/S review.json, findings-resolution | no existe |

## Tabla de reconciliación

| Entregable | Decisión | Motivo |
| --- | --- | --- |
| **RB-03** — decisión GD-12 sobre R/N/S | **Conservar `65ca852` íntegro** | Fuente autoritativa por instrucción explícita. `SC-GOV-021/023/024` = `NOT_APPLICABLE`; `sc-07/09/10` = `BLOCKED` con `applicability_decision`. No se reabre ni se reaudita |
| `docs/research/scientific-closure-synthesis-2026-09-22.md` | **Portar desde `f355272`, corregido** | RB-04. Contenido verificado por dos rondas (91/91 y 100/100 hashes, 72 métricas recomputadas). Se agrega nota de reconciliación y el ítem (e) sobre imputación causal en v3, ausente en el original |
| `evidence-finalization-2026-09-22/thesis-traceability.md` | **Portar desde `f355272`, corregido, reubicado** | RB-06. Se copia a `reconciliation-2026-09-22/thesis-traceability.md`; se agrega fila `2.12` sobre imputación causal |
| `claims.md` § «Clasificación final de afirmaciones» | **Portar desde `f355272`, corregido** | RB-04. Se corrigen las rutas de `auxiliary/{R,N,S}/review.json` para apuntar a los artefactos de RB-03 (no a los propios de `f355272`, que quedan como historia); se agrega la limitación de imputación en CL-04/CL-08; CL-10 se degrada de `DEMOSTRADA` a `RESPALDADA CON LIMITACIONES, pendiente de la auditoría única` |
| `evidence-finalization-2026-09-22/auxiliary/{R,N,S}/review.json` (propios de `f355272`) | **Descartar** | Redundantes y contradictorios: la fuente autoritativa de R/N/S es la de RB-03 (`sufficiency-review-2026-09-22/`), con su propia crítica adversarial documentada, que los de `f355272` no tienen por separado (`GD-35` de esa rama: «una sola revisión independiente por ronda») |
| `evidence-finalization-2026-09-22/reviews/review-audit-final.md` (ronda 1, FAIL) | **Preservar verbatim, como historia, no como aprobación** | Copiado a `sc-06-scientific-synthesis/reviews/review-audit-final-round1-FAIL.md`. Su verificación sustantiva (hashes, métricas) es reutilizable; su veredicto formal es `FAIL` y así se etiqueta |
| `evidence-finalization-2026-09-22/reviews/review-audit-final-correction.md` (ronda 2, FAIL) | **Preservar verbatim, como historia, no como aprobación** | Copiado a `.../review-audit-final-round2-FAIL.md`. Mismo tratamiento |
| `changes.json` → `sc-06-scientific-synthesis` = `PASS` (estado de `f355272`) | **Descartar la transición; reconstruir con eventos reales** | El `PASS` de `f355272` se apoya en la renuncia del auditor a una tercera ronda, no en un tercer informe favorable, y ningún lector independiente revisó el snapshot final (`GD-39` de esa rama). Se transiciona `sc-06` con su propia cadena de eventos en esta reconciliación, condicionada al resultado de la auditoría única que esta sesión solicita |
| `traceability.md` → `SC-GOV-025`/`GF` = `PASS_WITH_LIMITATIONS` (estado de `f355272`) | **Descartar; declarar `PENDIENTE`** | Misma razón. Se corrige sólo tras el veredicto de la auditoría única sobre el snapshot reconciliado |
| `traceability.md` → resto de la «Matriz final» (`SC-GOV-001..020`, salvo `016`) | **No se necesita portar**: ya están en la sección vigente de `65ca852` (posterior a H, 2026-09-21) con los mismos valores; se referencian, no se duplican | Evita una tercera copia divergente de 20 filas que no cambiaron |
| `SC-GOV-016` (interpretación científica) | **Actualizar en esta reconciliación** | Antes «no hay ninguna afirmación de resultado que revisar»; ahora existe la síntesis con resultados. Se actualiza junto con RB-04, sin depender de `f355272` |
| `plan.md` § «Estado de los gates — 2026-09-22» | **Descartar; redactar versión propia sin adelantar `GF`** | La versión de `f355272` declara `GF = PASS_WITH_LIMITATIONS` citando el informe `FAIL` corregido sin re-auditar. Se sustituye por una versión que deja `GF` `PENDIENTE` hasta la auditoría única |
| `README.md` (enlaces a `evidence-finalization-2026-09-22/`) | **Reescribir enlaces hacia esta reconciliación** | Apunta a rutas propias (`reconciliation-2026-09-22/`, `docs/research/scientific-closure-synthesis-2026-09-22.md`) |
| `openspec/changes/sc-06-scientific-synthesis/tasks.md` (todas `[x]`, de `f355272`) | **Descartar; dejar sin marcar hasta la auditoría única** | Marcaba `CLOSE` con «sin push» siendo falso (esa rama sí publicó y abrió PR) y marcaba `REVIEW-5` `[x]` con dos `FAIL` sin tercera ronda |
| `hu8-resultados-discusion-conclusiones.md` §8.4 | **Nuevo, no proviene de ninguna rama** | Se agrega la limitación de imputación causal directamente en la fuente donde vive la evidencia v3 afectada, por instrucción explícita del responsable (punto 9) |

## Qué NO se toca

`src/`, `tests/`, evidencia científica en `/home/gus/scientific-closure-runtime/`
y en `/mnt/scientific-backup/`, manifiestos, ledgers, el holdout, y los
artefactos ya auditados de A/B/C/H y de RB-03. No se ejecuta ninguna campaña.
No se repite ningún recómputo de hashes o métricas ya verificado en las
auditorías preservadas.
