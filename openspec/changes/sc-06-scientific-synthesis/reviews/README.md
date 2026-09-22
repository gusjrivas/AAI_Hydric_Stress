# Informes de revisión independiente de sc-06-scientific-synthesis

Este directorio conserva, **sin alterar**, los informes de los revisores
independientes que intervinieron sobre el cierre documental (síntesis,
claims, matriz final, trazabilidad a la memoria) en dos líneas de trabajo
distintas: la campaña original en `feat/scientific-evidence-finalization`
(PR #211) y la reconciliación de esta rama, `feat/scientific-closure`.

**Por qué existe.** Sigue el precedente de `openspec/changes/sc-08-aux-hitl/reviews/`
y de `openspec/changes/sc-0{7,9,10}-*/reviews/`: los informes de crítica y
auditoría se preservan verbatim, y las correcciones viven aparte.

## Historia preservada de `feat/scientific-evidence-finalization` (PR #211)

Dos rondas de auditoría final independiente revisaron el cierre documental
producido en esa rama. **Las dos terminaron en veredicto formal `FAIL`.**
Se preservan íntegras porque su contenido sustantivo —recomputación de 91/91 y
100/100 hashes, 72 métricas recalculadas en Python puro sin discrepancias,
verificación de los ledgers en modo sólo lectura, reconstrucción independiente
del recuento de la matriz— es real y no se repite en esta reconciliación.

| Archivo | Rol | Objeto | Veredicto |
| --- | --- | --- | --- |
| `review-audit-final-round1-FAIL.md` | `scientific_auditor` | Snapshot `7e63d1c` | `FAIL` — tres hallazgos materiales (`F-01`, `F-02`, `F-03`), documentales |
| `review-audit-final-round2-FAIL.md` | `scientific_auditor` | Snapshot `0dbc976`, tras corregir la ronda 1 | `FAIL` — un hallazgo material nuevo (`ND-01`), introducido por la propia corrección |

**Advertencia expresa, por instrucción del responsable.** Estos dos `FAIL` **no
se presentan aquí, ni en ningún artefacto de esta rama, como aprobación
independiente.** La rama de origen cerró `sc-06` como `PASS` de change
apoyándose en que el auditor, en el segundo informe, declaró por escrito un
veredicto de fondo `PASS_WITH_LIMITATIONS` para `SC-GOV-025`/`GF` y **renunció
expresamente a una tercera ronda** — pero ninguna tercera ronda verificó la
corrección de `ND-01`/`ND-02`/`ND-03` sobre el snapshot final `f355272`. Esta
reconciliación trata esa renuncia como lo que es —una limitación declarada por
el propio auditor (`GD-39` de esa rama)— y no como un tercer `PASS`. El estado
de `SC-GOV-025` y `GF` en esta rama se deriva **exclusivamente** de la
auditoría única solicitada sobre el snapshot reconciliado (ver más abajo), no
de estos dos informes.

## Auditoría de esta reconciliación

| Archivo | Rol | Objeto | Veredicto |
| --- | --- | --- | --- |
| `review-audit-reconciliation.md` | `scientific_auditor` | Snapshot `e822f6f` (reconciliación sobre `65ca852`) | **`PASS`** de alcance acotado a seis ítems; 1 hallazgo material (`F-01`, corregido) y 3 observaciones. **No** descarga RB-05/T25: no fue auditoría requisito por requisito |

**Alcance de esa auditoría, fijado por el responsable.** Verificar que RB-03
siga conforme al `PASS` de su propio auditor (sin reabrirlo ni reauditarlo);
que RB-04/RB-05/RB-06 estén realmente cubiertos por lo portado de `f355272` y
lo añadido en esta reconciliación; que no existan sobreafirmaciones; que el
estado propuesto para `GF`/`SC-GOV-025` se derive de evidencia vigente; que la
limitación de imputación causal (~24 % de días en la evidencia v3) esté
declarada; y que ningún `FAIL` histórico se presente como `PASS`. **No** repite
recómputo de hashes, métricas ni suites completas: los reutiliza de las dos
rondas preservadas arriba.

**Limitación declarada.** Cada revisor corrió en una sesión separada, de solo
lectura, con enforcement **instruido, no forzado por el harness**. Lo que estos
archivos acreditan es el contenido de sus informes tal como fueron recibidos.
