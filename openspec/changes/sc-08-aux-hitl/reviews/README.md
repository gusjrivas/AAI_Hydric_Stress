# Informes de revisión independiente del complemento H

Este directorio conserva, **sin alterar**, los informes de los revisores
independientes que intervinieron sobre el complemento H (`auxiliary_hitl_v1`).

**Por qué existe.** La auditoría final independiente de H levantó el hallazgo
material **AUD-H-01**: ninguna de las cuatro rondas de crítica conservaba el
informe de su autor, y sólo existían resúmenes escritos por el implementador.
El auditor señaló que ésa es exactamente la forma que el hallazgo `AUD-F-02` de
la sesión del 2026-09-20 condenó en este mismo proyecto, y que sin los informes
no hay artefacto que acredite la identidad separada implementador/crítico que
exige SC-GOV-008. El precedente que fija la conducta correcta está en
`openspec/scientific-closure/closure-verification-2026-09-20/`, que conserva
`review-critic.md`, `review-audit.md`, `review-audit-2.md`, `review-audit-3.md`
y `review-evidence-checker.md` completos y en las palabras de sus autores.

**Regla que rige estos archivos.** Se transcriben literalmente. No se corrigen,
no se resumen, no se reordenan y no se suavizan, incluidos los pasajes que
señalan defectos del propio orquestador y los veredictos negativos. Las
correcciones y las respuestas viven aparte, en
`evidence/governance/hitl-complement-2026-09-21/sc-08-aux-hitl/findings-resolution.json`
y en el contrato congelado.

| Archivo | Rol | Objeto | Veredicto |
| --- | --- | --- | --- |
| `review-critic-package-1.md` | `scientific_critic` | Paquete de intervención v1 | `NO_APTO` — 5 hallazgos materiales (C-01..C-05) |
| `review-critic-package-2.md` | `scientific_critic` | Paquete v2, tras corregir la ronda 1 | `NO_APTO` — 4 hallazgos materiales (D-01..D-04) |
| `review-critic-package-3.md` | `scientific_critic` | Paquete v3, tras corregir la ronda 2 | `APTO_PARA_MOSTRAR` — 9 menores (E-01..E-09) |
| `review-critic-execution.md` | `scientific_critic` | Ejecución de H y su evidencia | No confirma `PASS_WITH_LIMITATIONS`; 1 material (F-01) |
| `review-audit-final.md` | `scientific_auditor` | Snapshot final de H, GF y SC-GOV-025 | `PASS` de requisito con condiciones; GF bloqueado |

**Limitación declarada.** Cada revisor corrió en una sesión separada, de solo
lectura, sin capacidad de escritura sobre el repositorio ni sobre la evidencia.
Lo que estos archivos acreditan es el contenido de sus informes tal como fueron
recibidos. No constituyen una firma verificable externamente: son la
transcripción que conserva el orquestador, igual que en la campaña A/B/C.
