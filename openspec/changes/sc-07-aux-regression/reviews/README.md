# Informes de revisión independiente de la decisión de suficiencia GD-12

Este directorio conserva, **sin alterar**, los informes de los revisores
independientes que intervinieron sobre la decisión de suficiencia GD-12, que
clasifica los complementos R, N y S como `NOT_REQUIRED`.

**Por qué existe.** Es el bloqueo **RB-03** que levantó la auditoría final
independiente del complemento H el 2026-09-21: GD-12 nunca había sido criticada
ni auditada por nadie independiente. La conducta correcta la fija el precedente
de `openspec/changes/sc-08-aux-hitl/reviews/`, creado tras el hallazgo
`AUD-H-01`, que a su vez recoge el de
`openspec/scientific-closure/closure-verification-2026-09-20/`.

**Regla que rige estos archivos.** Se transcriben literalmente. No se corrigen,
no se resumen, no se reordenan y no se suavizan, incluidos los pasajes que
señalan defectos del orquestador y los veredictos negativos. Las correcciones y
las respuestas viven aparte, en
`openspec/scientific-closure/sufficiency-review-2026-09-22/findings-resolution.json`.

**Un solo informe por rol, preservado en tres lugares.** La decisión GD-12 es
una y cubre los tres complementos a la vez, de modo que cada revisor emitió un
único informe sobre los tres. Ese informe se conserva **byte a byte idéntico**
en los directorios `reviews/` de `sc-07-aux-regression`, `sc-09-aux-anomalies` y
`sc-10-aux-robustness`, para que ningún change quede sin su expediente de
revisión. La identidad de las copias es verificable con `sha256sum`.

| Archivo | Rol | Objeto | Veredicto |
| --- | --- | --- | --- |
| `review-critic-gd12.md` | `scientific_critic` | Snapshot `2185ed4` del dossier de suficiencia | Confirma `NOT_REQUIRED` en R, N y S; **7 hallazgos materiales** abiertos sobre el snapshot (C-01..C-06, C-08) |
| `review-audit-gd12.md` | `scientific_auditor` | Snapshot remediado `6878184` | **`PASS`** sobre RB-03, con 4 hallazgos propios (A-01..A-04) y 5 condiciones documentales, todas aplicadas. No es cierre científico |

**Limitaciones declaradas.** Cada revisor corrió en una sesión de contexto
separado, con instrucción de solo lectura. El enforcement es **instruido, no
forzado por el harness**: lo que estos archivos acreditan es el contenido de los
informes tal como fueron recibidos, no una firma verificable externamente. Los
perfiles nominales de `.codex/agents` no son cargables en este runtime y la
sustitución está declarada en
`openspec/scientific-closure/sufficiency-review-2026-09-22/session-identity.json`.

**Única transformación aplicada al texto recibido:** el transporte entre
sesiones indenta cada línea dos espacios; esa indentación de transporte se
retiró para restituir el Markdown original. No se cambió ningún carácter del
contenido.
