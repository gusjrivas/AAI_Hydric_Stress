# Procedencia de materiales de auditoría copiados

Origen: carpeta temporal de scratchpad de la sesión de auditoría (fuera del
repositorio), NO reproducible desde el árbol de trabajo. Copiados
byte-a-byte (hash SHA-256 verificado antes y después de la copia, con
`sha256sum`) al abrir la rama `fix/backend-technical-closure` desde
`origin/main` (`f17fe658bad4726202fe13784bb716c06468af9a`, 0 commits de
diferencia respecto del snapshot auditado).

| Archivo en esta rama | SHA-256 | Origen |
| --- | --- | --- |
| `docs/design/backend-audit-step2-informe-auditoria-paso2.md` | `616e27cee9640a37881bb543a4d1f111e45b49ab2cbf7a6bc1ad6434cba150b0` | scratchpad `backend-audit-step2/informe-auditoria-paso2.md` |
| `docs/design/backend-audit-step2-matriz-capitulo3-auditada.md` | `edf19d2b2872d824147ad5965dc6a87f9e88e7679fc95397b2f7702330b0866b` | scratchpad `backend-audit-step2/matriz-capitulo3-auditada-2026-09-24.md` |
| `docs/design/backend-audit-step2-encargo-correccion.md` | `a1001a6a4e52ec81e8e8f2d44a1318c54d8b2e045b4be41498c9c7c131782547` | scratchpad `backend-audit-step2/encargo-correccion-claude-code.md` |
| `docs/design/backend-audit-step2-fixtures/f08_replay_feedback_concurrency.py` | `24cc6048cf490fae28699e01b83fab22a61c39836ffa60e442c91be28498ba27` | scratchpad `fixtures/f08_replay_feedback_concurrency.py` |
| `docs/design/backend-audit-step2-fixtures/f08_replay_feedback_concurrency_v2.py` | `97ab0aee29a4f296ef5613bbfc5ad86c12a593fa34df554f3bf59d4e303470c5` | scratchpad `fixtures/f08_replay_feedback_concurrency_v2.py` |
| `docs/design/backend-audit-step2-fixtures/f08_mechanism_isolation.py` | `38bf9a9d22f8bb2fef0ba069f01eab33e3c7f0245369a7e0fdb30fc7e719119a` | scratchpad `fixtures/f08_mechanism_isolation.py` |
| `docs/design/backend-audit-step2-fixtures/f09_legacy_feedback_concurrency.py` | `36e407c28ab116c5af0c0d376a485bca3415f435992df52648fd8b6830222ab7` | scratchpad `fixtures/f09_legacy_feedback_concurrency.py` |

Estos documentos no reemplazan al informe de auditoría original; se
copian para que la revisión de este PR no dependa de una carpeta temporal
fuera del control de versiones.
