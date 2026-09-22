# Plan de implementación, validación y gates

changes.json es el DAG estructurado; cada directorio sc-* contiene proposal,
tasks y delta. Todos comienzan PLANNED y sin autorización científica.
Aprobación de preparación en esta sesión no activa esos cambios experimentales.

Orden: sc-01 → sc-02 → sc-03(A) → sc-04(B) → sc-05(C).
sc-07..10 requieren sc-01+sc-02 y condición REQUIRED.
sc-06 requiere sc-01+sc-02, terminal A/B/C auditado y todos los REQUIRED con PASS.
UNRESOLVED bloquea cierre. NOT_REQUIRED exige decisión motivada compatible con
alcance y revisión; no se marca el experimento como ejecutado.
Antes de despachar, evaluar dependencias estáticas Y gate adicional; no basta
una ordenación topológica. Cambios dependientes no se ejecutan si gate negativo.

## Gates verificables

| Gate | Entrada | Salida y condición de avance | Evidencia y bloqueo |
| --- | --- | --- | --- |
| G0 Preparación | Identidad correcta y árbol limpio | Specs/roles/matriz validados y auditoría de preparación PASS | Informe con SHA; no concede autorización científica |
| G1 Campaña | sc-01 PASS, afirmaciones resueltas, sc-02 PASS | Autoridad, procedencia, imagen/SHA/constraints, backup y permisos acreditados | Preflight metadata-only; resolver RK-05..11; nunca inicializar ledger por preflight |
| GA A | G1 y autorización A | Candidato primary_selection transferible y soporte; ganador estable o simplicidad predeclarada | frozen_config.json, selection_decision.json, métricas/OOF/config; NO_VALID_SELECTION bloquea B |
| GB B | GA, auditor A PASS, autorización B y registro único | CANDIDATE_VALIDATED si MCC>0 y CI inferior delta>=-0.05, soporte válido | decision.json, predictions_2023.csv, custodia; negativo/monoclase no abre C |
| GC C | GB, auditor B PASS, autorización C e inicialización separada autorizada | Evaluación única registrada y preservada, sin exigencia de resultado favorable | Ledger original, artefactos C y revisión; estado incierto/incompleto bloquea |
| GF Cierre | Terminal científico auditado y obligaciones aplicables cumplidas | Auditor final PASS sobre suficiencia del alcance completo | Afirmaciones trazadas, límites/pendientes y memoria; no solo software verde |

Los nombres exactos de artefactos de A/B/C se contrastan en
src/experiment_runner/controlled_daily_v4/artifacts.py antes de una campaña. Los gate-review
de gobernanza son nuevos informes; no modificar manifests/hash lists del runner.

## Protocolo A → B → C

Usar los comandos de scientific-closure-runbook.md solo después de G1 y de la
autorización específica de etapa. No ejecutar una cadena automática de comandos.
A: desarrollo 2015–2022, nested CV 3×3, gap 3, MCC OOF, delta 0.05, bootstrap
no circular segmentado 30 días/5000/seed 20250109; mínimo 2 folds y 80% válidas.
Congelamiento separado por segunda pasada. Modelo seed 42. Umbral alerta 0.5.
P20/transformaciones se aprenden en train y target observado t+3 no se imputa.
El detalle normativo de grillas/ventanas es el protocolo, no una nueva versión aquí.

B: train target <=2022-12-31, emisiones 2023-01-01..12-28. Reserva persistente
antes de analizar valores; comparación única contra persistencia; no reemplazar
candidato ni modificar configuraciones tras abrir B.
C: train target <=2023-12-31, emisiones 2024-01-01..2025-12-28; identidad
ejecutable e imagen iguales a A/B, ledger y permiso adicional; no reabrir por resultado.
Balcarce y sensibilidades no alimentan la comparación principal.

Durante A→B→C no editar checkout ejecutable ni resolver de nuevo un tag mutable.
La imagen histórica contiene SHA 214735e..., mientras esta preparación añade
documentación en otro SHA. sc-02 debe demostrar exactamente qué código e imagen
se usarán; no atribuir la imagen anterior al HEAD nuevo. Resolver la precondición
de main de ADR-0011 sin inferir excepción ni hacer merge en esta tarea.

## Validación

Preparación: CLI OpenSpec 1.13.1 estricta para scientific-closure y diez sc-*;
unittest documental (TOML, IDs, escenarios, DAG, tareas, referencias);
git diff --check y revisión completa de cambios/staged; verificar main/UI intactos.
Precisión 2026-09-21: tras integrar `origin/main`, «UI intacta» se verifica como
`git diff origin/main -- frontend/` vacío (el árbol reproduce la UI de `main`),
no como ausencia de archivos de `frontend/` en el diff contra el commit previo
de la rama; `main` no se modifica en ningún caso.
No ejecutar runner ni cargar módulos científicos para validar documentos.

Readiness futuro: tests de entorno, identidad, fronteras, soporte, custodia y
recuperación en contenedor sin red, raw no montado y fixtures en tmpfs.
Ensayo operativo de backup con fixtures; después verificar segunda copia real
sin abrir holdout. Capturar capacidades efectivas de los cinco roles.
Los tests de runtime pueden invocar runners sintéticos; nunca etiquetarlos
como ejecuciones científicas.

Después de cada etapa autorizada: checker de integridad, crítico metodológico,
auditor independiente. No reentrenar para verificar un holdout ni recalcular con
otro candidato. La revisión de métricas usa exclusivamente artefactos autorizados.
Los nuevos runners auxiliares, si REQUIRED, necesitan fixtures sustantivos
temporales y de perturbación antes de ejecutar su diseño congelado.

## Estado de los gates — 2026-09-22 (reconciliación)

Esta sección **no** modifica la tabla de gates ni el protocolo A→B→C: registra
el estado alcanzado. Ninguna compuerta se relaja. Reconcilia dos líneas de
trabajo divergentes; detalle en `reconciliation-2026-09-22/reconciliation-table.md`.

| Gate | Estado | Base |
| --- | --- | --- |
| G0 Preparación | PASS | Sin cambio desde 2026-09-19/20 |
| G1 Campaña | PASS | Sin cambio desde 2026-09-21 |
| GA A | SATISFECHO | Sin cambio |
| GB B | SATISFECHO | Sin cambio |
| GC C | SATISFECHO | Sin cambio |
| **GF Cierre** | **FAIL** | **Actualizado 2026-09-22.** RB-03 (GD-12 sobre R/N/S) tiene `PASS` de su auditor independiente y **no se reabre**. RB-04 (síntesis) y RB-06 (trazabilidad a memoria) están redactados y reconciliados. **RB-05 (auditoría final requisito por requisito) corrió sobre el snapshot `88ced62` y terminó en `FAIL`**: hallazgo material M-01, contradicción cronológica comprobada en la secuencia de gates A→B→C, declarada incumplimiento histórico no reparable documentalmente (`decisions.md` GD-38) y aceptada administrativamente por el responsable como desviación permanente (`decisions.md` GD-40). `GF` cierra en `FAIL`, no en `PASS_WITH_LIMITATIONS`: la aceptación administrativa de la desviación no equivale a su cumplimiento |

`GF` en `FAIL` corresponde, como máximo, al **alcance aprobado de HU7/HU8**;
no certifica ni descarta HU1 ni el Trabajo Final completo. `controlled_daily_v4`
queda cerrado administrativamente con no conformidad declarada, no con un
PASS estructural travestido de cierre científico. No hay tareas
experimentales pendientes dentro de esta campaña: una confirmación futura
requiere una campaña nueva sobre datos no utilizados previamente.

### Validación de esta fase

Documental y de gobernanza, sin ejecución científica: pruebas de gobernanza,
OpenSpec 1.13.1 estricto y `git diff --check`. **No** se recomputan hashes,
métricas ni la suite completa: se reutilizan las auditorías preservadas en
`sufficiency-review-2026-09-22/` (RB-03) y en
`openspec/changes/sc-06-scientific-synthesis/reviews/` (RB-05, histórico).
