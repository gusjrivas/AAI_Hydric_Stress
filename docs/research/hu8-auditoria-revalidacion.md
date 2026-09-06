# HU8 — Auditoría científica de revalidación del cierre

HU8 (issue #17) ya había sido cerrada formalmente, con sus 15 issues hijos (#97 a #111) cerrados como `completed`. Esta auditoría revisó si esa interpretación sigue siendo sostenible contra la evidencia experimental **formal** vigente (`controlled_daily_v3`, PR #168), en vez de contra la evidencia histórica (`purged_cv_v2` y anteriores) sobre la que están redactados actualmente `docs/research/hu8-analisis-resultados.md` y `docs/research/hu8-resultados-discusion-conclusiones.md`.

**Principio de esta auditoría:** no busca una conclusión favorable a la hipótesis. Busca determinar qué conclusiones están realmente justificadas por la evidencia formal. No se optimizaron resultados, no se ocultaron resultados negativos o mixtos, y no se trasladaron conclusiones de protocolos anteriores a `controlled_daily_v3`.

Conclusión adelantada: **HU8 no se reabre.** Sus cuatro criterios de aceptación continúan satisfechos con limitación de sincronización documental — la evidencia formal es válida, íntegra y suficiente; lo que falta es trasladarla al análisis redactado.

## 1. Fuentes formales utilizadas

- **Evidencia cuantitativa primaria:** `docs/research/reference-v3-formal-results.json` (leído directamente, 48 runs: 8 configuraciones × 5 semillas + 8 parents de agregación).
- **Evidencia derivada:** `docs/research/reference-v3-formal-table.md`.
- **Contrato metodológico:** `docs/research/protocolo-experimental-v3.md`, `docs/adr/0009-contratos-temporales-y-experimentos-controlados.md`, `openspec/specs/experiment-runner/spec.md`.

No se utilizó ningún artefacto `reference-v3-*` sin sufijo `-formal` (evidencia histórica/provisional, archivada fuera del repositorio en una auditoría previa).

## 2. Criterios de aceptación

### CA1 — "Se comparan las distintas configuraciones evaluadas"

**Estado: CUMPLE CON LIMITACIÓN**

La evidencia formal compara correctamente las 8 configuraciones de `controlled_daily_v3` (F1/MCC/AP, dispersión entre semillas). La limitación es que los documentos de análisis (`hu8-analisis-resultados.md`, `hu8-resultados-discusion-conclusiones.md`) todavía presentan solo las 4 configuraciones de `purged_cv_v2`, sin incorporar las 8 formales.

### CA2 — "Se analiza el aporte de los componentes incorporados a la arquitectura"

**Estado: CUMPLE CON LIMITACIÓN**

Modelado predictivo, anomalías y sintéticos tienen evidencia cuantitativa formal (ver sección 4). Retroalimentación humana (HITL) carece de evaluación cuantitativa formal — diseñada pero no ejecutada (`protocolo-experimental-v3.md`, ADR-0009) — limitación ya reconocida explícitamente, no oculta.

### CA3 — "Se elaboran conclusiones fundamentadas a partir de la evidencia experimental"

**Estado: CUMPLE CON LIMITACIÓN**

Las conclusiones actuales están fundamentadas en evidencia real, pero pre-formal (`purged_cv_v2`), no en `controlled_daily_v3`.

### CA4 — "Se determina si los resultados permiten contrastar la hipótesis de investigación"

**Estado: CUMPLE CON LIMITACIÓN**

Contrastar no exige confirmar: los documentos ya declaran "no confirma" con matices por componente. La limitación es la misma que en CA1-CA3: la contrastación vigente usa evidencia pre-formal.

## 3. Hipótesis canónica

Debe reproducirse exactamente el texto de ADR-0001 (`docs/adr/0001-arquitectura-modular-deteccion-estres-hidrico.md`):

> "La hipótesis de investigación sostiene que la incorporación de técnicas de inteligencia artificial, particularmente generación de datos sintéticos, modelado predictivo, detección de anomalías y retroalimentación humana, puede mejorar la capacidad de detección temprana de condiciones de estrés hídrico en contextos caracterizados por disponibilidad limitada, ruido y alta variabilidad de datos, respecto de enfoques tradicionales basados principalmente en observación empírica o reglas de riego estáticas."

`docs/research/hu8-resultados-discusion-conclusiones.md` (sección 2, antes de esta iteración) citaba una reformulación categórica distinta ("la combinación de ... **mejora** ... frente a enfoques tradicionales"), que cambia "puede mejorar" por una afirmación de mejora garantizada. Esa reformulación fue corregida en esta iteración (ver sección 9).

## 4. Matriz de las 8 configuraciones formales (verificada contra el JSON)

| Configuración | F1 media ± desvío | MCC media | AP media |
|---|---:|---:|---:|
| base | 0.5592 ± 0.0287 | -0.0135 | 0.5816 |
| recent_fraction_0.5 | 0.6891 ± 0.0407 | 0.1417 | 0.6546 |
| sinteticos | 0.5450 ± 0.0986 | 0.0582 | 0.6029 |
| noise_test_only_0.3 | 0.5605 ± 0.0346 | 0.0100 | 0.5755 |
| completa | 0.5052 ± 0.0374 | -0.0706 | 0.5493 |
| noise_both_0.3 | 0.5041 ± 0.0719 | -0.0058 | 0.5804 |
| anomalias | 0.5689 ± 0.0395 | 0.0110 | 0.5672 |
| coverage_fraction_0.5 | 0.5238 ± 0.0631 | -0.0376 | 0.5913 |

Estos 8 valores fueron reverificados contra `reference-v3-formal-table.md` y, para varias configuraciones, recalculados manualmente desde los 40 registros individuales (child runs) del JSON — sin discrepancias.

**Baselines formales embebidos en cada child run** (persistencia, clase mayoritaria de entrenamiento, siempre-estrés): existen y comparten el mismo `test_rows`/target que la configuración correspondiente. Pertenecen íntegramente a `controlled_daily_v3` (mismo `commit_sha`, mismo `pipeline_version`); no se importaron cifras de `purged_cv_v2` para esta comparación.

## 5. Comparaciones pareadas (delta = configuración − base, por semilla)

Estadísticos descriptivos sobre 5 observaciones pareadas por semilla — no es inferencia estadística nueva; 5 semillas miden sensibilidad del procedimiento a la aleatoriedad algorítmica, no son 5 réplicas independientes.

| Contraste | ΔF1 media | ΔMCC media | ΔAP media | Consistencia entre 5 semillas | Conclusión descriptiva |
|---|---:|---:|---:|---|---|
| base → anomalias | +0.0097 | +0.0245 | **-0.0143** | F1/MCC: 3 pos/1 neg/1 nulo; AP: 5/5 negativo | EVIDENCIA MIXTA |
| base → sinteticos | -0.0141 | +0.0717 | +0.0213 | F1: 3 pos/2 neg (un outlier extremo); MCC/AP: 4/5 pos | EVIDENCIA MIXTA |
| base → completa | -0.0538 | -0.0570 | **-0.0325** | F1/MCC: 4 neg/1 nulo; AP: 5/5 negativo | NO SUPERA CONSISTENTEMENTE (peor en las 3 métricas) |
| base → coverage_fraction_0.5 | -0.0353 | -0.0242 | +0.0097 | Sin dirección clara, alta dispersión | EVIDENCIA MIXTA, sin conclusión sostenible |
| base → recent_fraction_0.5 | **+0.1300** | **+0.1552** | **+0.0730** | **5/5 seeds positivo en las 3 métricas** | MEJORA DESCRIPTIVA CONSISTENTE |
| base → noise_both_0.3 | -0.0551 | +0.0077 | -0.0012 | F1: 4 neg/1 pos; MCC/AP: mixto, ~nulo | EVIDENCIA MIXTA/CASI NULA |
| base → noise_test_only_0.3 | +0.0013 | +0.0234 | -0.0061 | Mixto, prácticamente nulo | EVIDENCIA MIXTA/CASI NULA |
| sinteticos → completa | -0.0398 | -0.1288 | -0.0535 | MCC/AP: 5/5 negativo; F1: 4/5 negativo | completa consistentemente peor que sinteticos |
| anomalias → completa | -0.0637 | -0.0815 | -0.0179 | F1: 5/5 negativo; MCC/AP: 4/5 negativo | completa consistentemente peor que anomalias |

## 6. Interpretación por componente

### Detección de anomalías (base → anomalias)

**EVIDENCIA MIXTA, no mejora consistente.** F1/MCC mejoran en 3 de 5 semillas (con un outlier fuertemente negativo), pero **AP empeora en las 5/5 semillas sin excepción** — un compromiso claro entre métricas. La narrativa histórica ("efecto positivo pero modesto") no se sostiene bajo `controlled_daily_v3`: el ranking de probabilidades (AP) se degrada de forma consistente aunque el punto de corte fijo a 0.5 (F1) mejore en algunos casos.

### Datos sintéticos (base → sinteticos)

**EVIDENCIA MIXTA**, con un matiz relevante frente a la narrativa histórica ("los sintéticos empeoran consistentemente"): bajo `controlled_daily_v3`, MCC y AP son **predominantemente positivos** (4 de 5 semillas cada uno), mientras que F1 es inconsistente por un outlier extremo en una semilla. No hay una dirección única sostenible; el rechazo tajante de la hipótesis para este componente **no se replica** con la misma fuerza bajo el protocolo formal. La conclusión se restringe exclusivamente a este generador (normal multivariada), esta parametrización y este dataset — no se generaliza a otros métodos de generación sintética.

### Configuración completa (anomalías + sintéticos)

**NO SUPERA CONSISTENTEMENTE A `base` — es consistentemente peor.** AP empeora en 5/5 semillas, F1 y MCC empeoran en 4/5 (1 sin cambio). `completa` es la configuración más consistentemente desfavorable de las 4 configuraciones de factores. No incluye retroalimentación humana cuantitativa; no debe describirse como "arquitectura completa de los cuatro componentes de la hipótesis".

### Escasez por cobertura (coverage_fraction_0.5)

**EVIDENCIA MIXTA, sin dirección clara.** F1 mayormente negativo, MCC y AP mixtos, con alta dispersión entre semillas. No permite ninguna conclusión sostenible sobre el efecto de la escasez por cobertura estratificada.

### Escasez por recencia (recent_fraction_0.5)

**El único contraste con mejora descriptiva consistente**: 5/5 semillas positivas en F1, MCC y AP simultáneamente. Es el efecto más robusto de todo el estudio formal. **Esto no permite afirmar "menos datos mejora el desempeño"**: la configuración representa entrenamiento restringido al 50% más reciente, no una reducción arbitraria de volumen. Una explicación por corrimiento de distribución estacional (el entrenamiento reciente se parece más al período evaluado) es **una interpretación plausible, no demostrada causalmente** por este diseño experimental.

### Ruido en train+test (noise_both_0.3) y ruido solo en test (noise_test_only_0.3)

Ambos con patrón **casi nulo/mixto** en las 3 métricas (medias cercanas a cero, signos mixtos entre semillas). No hay evidencia de degradación uniforme ni de robustez general al ruido. El ruido es gaussiano artificial, ratio 0.3, no calibrado contra ninguna caracterización empírica de ruido de sensor real.

## 7. Robustez y dispersión

**Robustez** se define aquí como "capacidad de conservar desempeño bajo una perturbación controlada" — no equivale a mejora. Ningún escenario de perturbación (coverage, noise_both, noise_test_only) muestra conservación clara de desempeño combinada con degradación mínima esperada que permita hablar de "robustez general"; los tres son mixtos o casi nulos. `recent_fraction_0.5` no es un caso de robustez: es una mejora real, pero corresponde a una manipulación del conjunto de entrenamiento, no a una perturbación adversa.

**Dispersión entre semillas** (columna "desvío" de la tabla) mide sensibilidad del procedimiento a la semilla aleatoria (inicialización del modelo, muestreo de estratos, ruido gaussiano) — no incertidumbre poblacional externa, ni variación entre sitios o campañas. `sinteticos` (0.0986) y `coverage_fraction_0.5` (0.0631) tienen la mayor dispersión de F1; `noise_test_only_0.3` (0.0346) y `base`/`recent_fraction_0.5` (~0.029-0.041) la menor.

## 8. Modelado predictivo, baseline y "enfoque tradicional"

Random Forest es un **modelo fijo** en las 8 configuraciones formales (comparación pareada controlada), no seleccionado por desempeño de test ni presentado como "el mejor modelo universal".

`base` **no es** un enfoque tradicional: es una configuración de la arquitectura propuesta sin anomalías ni sintéticos, con Random Forest entrenado sobre variables de retardo/ventana móvil. El único baseline formal disponible que podría representar "observación empírica o reglas de riego estáticas" es **persistencia** (predecir estrés futuro si la humedad actual ya está bajo el umbral) — una heurística simple sin modelo, pero **no una regla de riego estática en sentido agronómico** (no hay calendario de riego fijo ni criterio de un agrónomo en el protocolo formal). La comparación contra "enfoques tradicionales" que exige la hipótesis está **solo parcialmente cubierta** por este baseline.

## 9. Falsos positivos y falsos negativos bajo controlled_daily_v3

El JSON formal **sí contiene predicciones por fecha** (`predictions.rows`, con `y_true`/`y_pred` por día) para cada child run — no fue necesario ejecutar ningún modelo. Se consolidó la matriz de confusión de la configuración `base` (la de referencia para comparación) leyendo directamente esas filas, sin ejecutar código:

| Semilla | TP | TN | FP | FN |
|---|---:|---:|---:|---:|
| 0 | 22 | 13 | 15 | 17 |
| 1 | 19 | 12 | 16 | 20 |
| 2 | 22 | 14 | 14 | 17 |
| 3 | 22 | 11 | 17 | 17 |
| 4 | 21 | 12 | 16 | 18 |
| **Total (5 semillas)** | **106** | **62** | **78** | **89** |

Los totales agrupan las cinco ejecuciones sobre el mismo conjunto temporal de evaluación. Por lo tanto, no representan observaciones independientes adicionales: cada fecha aparece una vez por semilla. La tabla se utiliza como resumen descriptivo de los errores acumulados entre ejecuciones y no como una única matriz de confusión correspondiente a un conjunto de 335 casos independientes. Para interpretar la variabilidad entre ejecuciones deben conservarse también los valores por semilla.

Como control descriptivo, los conteos agrupados producen una precisión (106/(106+78)=0.576) y un recall (106/(106+89)=0.544) muy próximos a los promedios registrados entre semillas (`precision_mean`/`recall_mean` del JSON formal para `base`: 0.5760/0.5436). Esta proximidad no implica equivalencia matemática general entre el promedio de métricas por ejecución y la métrica calculada después de agrupar matrices de confusión. Esta evidencia reemplaza, para efectos de HU8 vigente, a los conteos de FP/FN de la partición única de HU4 (7 FP/24 FN sobre 72 filas) citados en `hu8-analisis-resultados.md` sección 7, que corresponden a un pipeline anterior a todas las correcciones de fuga temporal.

## 10. Retroalimentación humana (HITL)

- **Evidencia funcional: SI** — el mecanismo de recalibración madura (`recalibrate_predictor`, HU5) está implementado y verificado; puede modificar el modelo ante correcciones humanas.
- **Evidencia cuantitativa formal de mejora: NO** — no existe, dentro de `controlled_daily_v3`, ninguna configuración que compare un modelo congelado contra uno reentrenado con/sin correcciones humanas. Diseñada pero no ejecutada (`protocolo-experimental-v3.md`, sección "Próxima fase científica"; ADR-0009).
- **Evidencia de generalización: NO.**

Esta ausencia **no obliga a reabrir HU7/HU8**: ni los criterios de aceptación reales de HU7 ni los de HU8 exigen esa evaluación cuantitativa, y la limitación ya está documentada explícitamente, sin ocultarse.

## 11. Auditoría de issues hijos (#97 a #111)

| Issue | Clasificación |
|---|---|
| #97 — Consolidar los resultados de todas las ejecuciones experimentales | RATIFICADO CON LIMITACIÓN |
| #98 — Identificar ejecuciones incompletas o inconsistentes | RATIFICADO |
| #99 — Calcular métricas agregadas y medidas de dispersión | RATIFICADO CON LIMITACIÓN |
| #100 — Comparar el enfoque de referencia con la arquitectura propuesta | RATIFICADO CON LIMITACIÓN |
| #101 — Analizar el aporte de la detección de anomalías y los datos sintéticos | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |
| #102 — Evaluar el efecto de la retroalimentación y la recalibración | RATIFICADO CON LIMITACIÓN |
| #103 — Analizar falsos positivos, falsos negativos y errores relevantes | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |
| #104 — Analizar el desempeño bajo escenarios de escasez de datos | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |
| #105 — Analizar el desempeño bajo escenarios de ruido y variabilidad | RATIFICADO CON LIMITACIÓN |
| #106 — Evaluar robustez, estabilidad y compromisos entre métricas | RATIFICADO CON LIMITACIÓN |
| #107 — Contrastar los resultados con la hipótesis de investigación | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |
| #108 — Identificar limitaciones y amenazas a la validez | RATIFICADO |
| #109 — Redactar la sección de resultados experimentales | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |
| #110 — Redactar la discusión y las conclusiones | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |
| #111 — Consolidar tablas, figuras, referencias y evidencias | CIERRE HISTÓRICO REQUIERE CORRECCIÓN DOCUMENTAL |

Los 15 issues permanecen **CLOSED / completed**. "Cierre histórico requiere corrección documental" significa exactamente eso — una reescritura sobre evidencia ya existente y ya verificada, sin nueva evidencia experimental y sin reapertura.

## 12. Amenazas a la validez (actualizadas contra v3)

- **Interna:** diseño pareado correcto (seeds compartidas), correcciones de fuga temporal ya incorporadas en `controlled_daily_v3`, umbral congelado sobre train limpio, generador sintético simple (normal multivariada), ruido simulado no calibrado, HITL no cuantitativo dentro del diseño experimental.
- **Externa:** un único sitio (Melchor Romero) y un único año (2024) como **referencia de desarrollo, no validación externa** (`protocolo-experimental-v3.md`: "el test de 2024 ya fue inspeccionado... es una referencia de desarrollo, no una confirmación externa independiente"); sin validación multisitio ni multianual.
- **De constructo:** definición operacional de estrés (percentil 20, proxy relativo no agronómico validado), horizonte de 3 días (razonado, no comparado contra alternativas), coverage/recent como proxies de escasez no equivalentes entre sí, ruido gaussiano no calibrado, F1/MCC/AP como trío metodológicamente correcto sin una métrica "ganadora" preespecificada.
- **De conclusión:** 5 semillas miden sensibilidad algorítmica, no son réplicas agronómicas independientes; no se eligió retrospectivamente la métrica más favorable; ausencia deliberada de inferencia estadística confirmatoria no preespecificada; resultados mixtos preservados sin armonización forzada.

## 13. Contrastación de la hipótesis

**Conclusión científica canónica:** la evidencia formal obtenida es parcial y mixta. Dentro del alcance experimental evaluado, no permite sostener una mejora general de la arquitectura para la detección temprana de estrés hídrico. Algunos escenarios y componentes presentan efectos favorables en determinadas métricas, otros muestran compromisos o resultados desfavorables, y el aporte cuantitativo de la retroalimentación humana permanece sin evaluar.

El único efecto consistente y fuerte (`recent_fraction_0.5`) no corresponde a un componente arquitectónico de la hipótesis, sino a una manipulación del conjunto de entrenamiento con explicación causal no demostrada. Los componentes propiamente dichos (anomalías, sintéticos) muestran evidencia mixta. La comparación con "enfoques tradicionales" está solo parcialmente cubierta por el baseline de persistencia disponible.

No se afirma "hipótesis comprobada", "hipótesis confirmada" ni "hipótesis rechazada". Tampoco se afirma que la arquitectura mejore de manera general.

## 14. Material para la memoria técnica

- **Capítulo 4 (ensayos y resultados):** tabla formal de 8 configuraciones (sección 4 de este documento), comparaciones pareadas (sección 5), resultados por componente (sección 6), FP/FN consolidados (sección 9). Para la presentación de errores (FP/FN), se recomienda mostrar las métricas medias y su dispersión entre semillas como evidencia principal, junto con las matrices de confusión por semilla (o un resumen descriptivo de ellas) — no usar el total agrupado de las cinco semillas como si correspondiera a un conjunto de observaciones independientes.
- **Capítulo 5 (conclusiones):** contrastación de la hipótesis (sección 13), limitaciones y amenazas a la validez (sección 12), HITL pendiente (sección 10), 2024 como referencia de desarrollo (no validación externa), trabajo futuro (más fracciones de escasez, evaluación HITL cuantitativa ya diseñada en el protocolo, validación externa multisitio/multianual).

## 15. Conclusión de la auditoría

Los cuatro criterios de aceptación de HU8 (CA1-CA4) permanecen CUMPLE CON LIMITACIÓN: la evidencia formal `controlled_daily_v3` es válida, íntegra y suficiente (heredado de la revalidación de HU7 — sin fuga, sin contaminación, sin selección post hoc), pero los documentos de análisis y discusión de HU8 no la incorporan todavía. Ninguno de los gaps identificados es un defecto técnico ni exige nueva evidencia experimental: son de redacción/consolidación sobre evidencia ya existente y ya verificada. No se requiere segunda auditoría técnica/científica independiente. El issue #17 y sus 15 issues hijos (#97-#111) permanecen cerrados; esta auditoría no reabre ni modifica ninguno de ellos.

**Clasificación final: B — CIERRE DE HU8 REVALIDADO CON ITERACIÓN DOCUMENTAL/ANALÍTICA.**
