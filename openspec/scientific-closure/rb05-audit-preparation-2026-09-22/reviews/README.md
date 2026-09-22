# Informes de auditoría independiente del dossier RB-05

Este directorio conserva, **sin alterar**, los informes de auditoría
independiente recibidos sobre `rb05-dossier.md`. Sigue el precedente de
`openspec/changes/sc-06-scientific-synthesis/reviews/` y de
`openspec/changes/sc-08-aux-hitl/reviews/`: los informes se preservan
verbatim y las correcciones viven aparte, en el propio dossier (marcadas en
línea, sin borrar lo que la versión anterior decía) y en `decisions.md`.

| Archivo | Rol | Objeto | Veredicto |
| --- | --- | --- | --- |
| `review-audit-codex-round1-FAIL.md` | `scientific_auditor` (Codex, sesión externa independiente de la preparación) | Snapshot `88ced62` | `FAIL` — cuatro hallazgos materiales (M-01..M-04). M-01 (contradicción cronológica en la secuencia de gates A→B→C, verificada independientemente contra dos fuentes primarias) declarado incumplimiento histórico **no reparable documentalmente** (`decisions.md` GD-38, `risks.md` RK-20). M-02, M-03 y M-04 corregidos el 2026-09-22 |

**Verificación de integridad del archivo preservado.** sha256
`04a4f49b575a84bc128a298a98b8f9635104df6e754a8ac90ec73762fb13d29a`, copiado
byte a byte del archivo recibido (`sha256sum` verificado en el momento de la
copia, coincide).

**Qué NO acredita este informe.** No es un veredicto sobre los resultados
científicos de A, B, C o H, que no están en disputa. Es un veredicto sobre si
el **proceso de gobernanza** documentado (autorización de cada etapa
condicionada a la auditoría PASS de la etapa anterior) se cumplió como el
protocolo lo exige. `SC-GOV-025` y `GF` permanecen `PENDIENTE` a la espera de
una decisión del responsable sobre M-01, no de una reejecución de A, B o C.
