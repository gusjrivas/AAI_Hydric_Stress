# ADR-0011: Protocolo formal de controlled_daily_v4_external_pergamino

Estado: Aceptado
Fecha: 2026-09-08

## Contexto

ADR-0010 registró la estrategia multimodelo para `controlled_daily_v4` (Regresión Logística, Random Forest, HistGradientBoostingClassifier y Soft Voting) y dejó como condición previa a su implementación: verificar si existe un período temporal todavía no observado que pueda reservarse como holdout, definir el protocolo completo antes de observar nuevos resultados, e impedir que el conjunto de test de `controlled_daily_v3` intervenga en la selección de los nuevos candidatos.

Un relevamiento técnico-científico read-only sobre cuatro datasets externos (`pergamino_era5land_soil_hourly_2015_2025.csv`, `pergamino_nasa_power_daily_2015_2025.csv`, `balcarce_era5land_soil_hourly_2015_2025.csv`, `balcarce_nasa_power_daily_2015_2025.csv`, ubicados fuera del repositorio en `AAI_Hydric_Stress_external_data/raw`) identificó que Pergamino y Balcarce, productos de reanálisis (ERA5-Land vía Open-Meteo y NASA POWER, no mediciones de sensores de campo), ofrecen una secuencia diaria continua sin faltantes estructurales entre 2015 y 2025, con un período 2024–2025 todavía no observado que puede reservarse como holdout independiente del de `controlled_daily_v3`. Una microvalidación metodológica posterior confirmó, para Pergamino y la profundidad de suelo 0–7 cm, ausencia de folds monoclase y cumplimiento de las condiciones de no-leakage bajo `TimeSeriesSplit(n_splits=3, gap=3)` (outer e inner), y corrigió la definición del target al operador estrictamente `<` (nunca `<=`) frente al umbral `P20_train`.

Este ADR formaliza el protocolo experimental resultante de ese relevamiento y esa microvalidación, como condición previa exigida por ADR-0010 antes de cualquier implementación de `controlled_daily_v4`.

## Problema metodológico

`controlled_daily_v3` es evidencia científica formal congelada (`scientific-baseline-v3`), obtenida sobre un único sitio (`melchor_romero_2024_consolidado`) y un único año. ADR-0010 exige que la nueva evidencia experimental de `controlled_daily_v4` no reutilice el conjunto de test de `controlled_daily_v3` para seleccionar modelos, ajustar hiperparámetros o definir pesos de ensamble. Falta, sin embargo, un protocolo formal que: (a) explote un dominio de datos externo (reanálisis agroclimático de Pergamino) sin confundirlo con evidencia de campo directa; (b) separe estrictamente selección de modelos (con datos ya observados) de validación temporal y holdout final (con datos todavía cerrados); y (c) module estadísticamente la comparación entre los cuatro candidatos de ADR-0010 sin afirmar superioridad no sostenida por la evidencia.

## Decisión

Se adopta el protocolo `controlled_daily_v4_external_pergamino`, documentado en detalle en `docs/research/controlled-daily-v4-external-pergamino-protocol.md`, con los siguientes puntos normativos:

- **Identificador:** `controlled_daily_v4_external_pergamino` (no `controlled_daily_v4` a secas, para no colisionar con una eventual iteración futura de v4 sobre el sitio original de `melchor_romero_2024_consolidado`, que ADR-0010 deja abierta como posibilidad).
- **Dataset y sitio:** Pergamino (ERA5-Land + NASA POWER), como sitio externo principal. Balcarce queda fuera de esta ejecución, registrado como `FUTURE_GEOGRAPHIC_VALIDATION`.
- **Profundidad:** 0–7 cm como análisis principal; 7–28 cm como sensibilidad separada, sin capacidad de intervenir en la selección del análisis principal. Se excluyen 28–100 cm y 100–255 cm (esta última mostró folds monoclase sistemáticos y un umbral P20 coincidente con un valor repetido en 109 filas, revelando baja variabilidad estructural del reanálisis a esa profundidad).
- **Target:** `stress(t) = 1` si `soil_moisture(t+3) < P20_train`, operador estrictamente `<`, umbral aprendido exclusivamente con el `train` autorizado de cada etapa/fold.
- **Etapas:** A (desarrollo y selección, 2015–2022, nested `TimeSeriesSplit(n_splits=3, gap=3)` outer e inner) → B (validación temporal candidata, 2023, compuerta real con criterio de aceptación predeclarado) → C (holdout final, 2024–2025, solo si B produce `CANDIDATE_VALIDATED`).
- **Modelos:** Regresión Logística, Random Forest, HistGradientBoostingClassifier y Soft Voting (pesos fijos 1/3, 1/3, 1/3), tal como registra ADR-0010, con balanceo de clases exclusivamente vía `sample_weight` calculado fold-local (sin `class_weight`, para no depender de la versión exacta de scikit-learn instalada).
- **Selección:** MCC global sobre OOF concatenado como criterio principal, con margen práctico predeclarado `δ = 0.05` (fijado antes de observar resultados, no derivado de A/B/C) para definir ganador estable, conjunto de equivalencia práctica y `SIN_GANADOR_ESTABLE`.
- **Bootstrap:** moving block bootstrap **no circular**, con reglas exactas y justificación registradas en el protocolo canónico (sección 8, "Implementación del moving block bootstrap: variante no circular") — no duplicadas aquí.
- **Umbral de decisión probabilístico:** fijo en `0.5` para los cuatro candidatos, no optimizado con A, B ni C.
- **Entorno:** la versión exacta de Python/NumPy/pandas/SciPy/PyArrow/scikit-learn se fija y valida en un manifiesto o lock experimental antes del primer experimento (`PRECONDITION_FOR_EXECUTION`); no existe hoy en el repositorio (`pyproject.toml` solo fija pisos mínimos, sin lockfile).

## Alternativas consideradas

- **Usar `controlled_daily_v4` sin sufijo de sitio.** Descartada: colisionaría con la posibilidad, dejada abierta por ADR-0010, de una iteración v4 sobre el sitio original con un nuevo holdout local.
- **Incorporar Balcarce en esta misma iteración.** Descartada por ahora: multiplicaría el alcance sin necesidad — se prioriza validar el protocolo completo sobre un único sitio externo antes de replicarlo, y Balcarce queda registrado como validación geográfica futura, no descartada.
- **Incluir temperatura y precipitación en el conjunto de features principal.** Descartada para el protocolo principal: el contrato de `controlled_daily_v3` no las incluye, y agregarlas confundiría cualquier diferencia observada entre "efecto del sitio/dominio" y "efecto de variables adicionales". Quedan como sensibilidad separada, predeclarada, no obligatoria.
- **Fijar un margen práctico numérico derivado del desvío estándar bootstrap de la Etapa A.** Descartada por decisión explícita de dirección de proyecto: se prefiere un margen fijo (`δ=0.05`) declarado antes de observar cualquier resultado, más simple de auditar y defender que un margen cuyo valor concreto solo existiría después de ejecutar la Etapa A.
- **Usar `class_weight` del constructor de cada modelo para el balanceo de clases.** Descartada por decisión explícita de dirección de proyecto: introduce una dependencia no confirmada de la versión exacta de scikit-learn (no hay lockfile en el repositorio); se reemplaza por `sample_weight` calculado explícitamente, soportado de forma universal.

## Consecuencias

Positivas:
- Existe, por primera vez, un protocolo formal para evaluar los cuatro candidatos de ADR-0010 sobre un dominio de datos independiente del de `controlled_daily_v3`, sin comprometer la evidencia congelada de esta última.
- La separación estricta de etapas A/B/C, con compuerta real en B, evita selección post hoc usando el holdout.
- El manifiesto de provenance (sección siguiente) deja trazabilidad completa de fuente, licencias, hashes, folds, semillas y resultados, incluso antes de ejecutar nada.

Negativas / riesgos:
- Mayor costo experimental (hasta ~789 ajustes de modelo en la Etapa A, ver el protocolo detallado) frente a una comparación de un único modelo.
- Pergamino es reanálisis, no observación de campo: cualquier resultado de este protocolo es replicación funcional/validación temporal sobre datos modelados, nunca validación agronómica in situ.
- La versión exacta del entorno de ejecución no está fijada hoy en el repositorio; ejecutar sin fijarla primero comprometería la reproducibilidad.

## Restricciones

- No se modifica, reinterpreta ni recalcula retrospectivamente `controlled_daily_v3`.
- No se mueven `scientific-baseline-v3`, `technical-baseline-v1` ni `technical-baseline-v2`.
- El conjunto de test de `controlled_daily_v3` no interviene en ningún paso de este protocolo.
- Los CSV crudos de Pergamino (y, en el futuro, Balcarce) permanecen fuera de Git.
- Este ADR no autoriza por sí mismo la ejecución de experimentos ni la implementación del runner correspondiente.

## Relación con ADR-0010

Este ADR es la condición previa #3 de ADR-0010 ("definirse el protocolo completo antes de observar nuevos resultados") aplicada específicamente al dominio de datos externo de Pergamino. Los cuatro candidatos, la prohibición de ajustar pesos de Soft Voting con test/holdout, y la exigencia de mismas variables/target/horizonte/fechas/semillas comparables entre candidatos, provienen sin modificación de ADR-0010. Este ADR no reemplaza ni reabre ADR-0010; lo instancia sobre un dominio de datos concreto.

## Relación con controlled_daily_v3

`controlled_daily_v3` continúa siendo la evidencia científica formal congelada bajo `scientific-baseline-v3`. Este protocolo no la modifica, no la reinterpreta y no la usa como fuente de datos, umbral o test. Pergamino es una segunda fuente agroclimática externa, propuesta para evaluar transferibilidad metodológica y temporal — no para sustituir, ampliar retroactivamente ni recalibrar `controlled_daily_v3`. Cualquier resultado futuro de `controlled_daily_v4_external_pergamino`, sea cual sea, se reporta como evidencia independiente y adicional, nunca como corrección de la evidencia de v3.

## Condiciones previas a la ejecución

1. Existencia de un manifiesto o lock experimental con las versiones exactas y validadas de Python, NumPy, pandas, SciPy, PyArrow y scikit-learn (`PRECONDITION_FOR_EXECUTION`, ver `docs/research/controlled-daily-v4-external-pergamino-protocol.md`).
2. Confirmación (o descarte explícito) de las URLs exactas de adquisición de los CSV de Pergamino y de sus licencias/términos de uso (Open-Meteo/ERA5-Land vía Copernicus/ECMWF, NASA POWER), hoy marcadas `PENDING_CONFIRMATION` en el manifiesto de provenance.
3. Implementación del código del protocolo (fuera de alcance de este ADR y de la tarea que lo originó, exclusivamente documental) como un *change* de OpenSpec propio, con su propia propuesta, delta de especificación y tareas.
4. Ninguna ejecución puede comenzar sin que este ADR y el protocolo detallado ya estén mergeados en `main`.

## Criterios de apertura del holdout (2024–2025)

El holdout de 2024–2025 (Etapa C) solo puede abrirse si la Etapa B produce `CANDIDATE_VALIDATED`: `MCC_candidato_2023 > 0` **y** límite inferior del intervalo pareado de block bootstrap de `ΔMCC_B = MCC_candidato_2023 − MCC_persistencia_2023` mayor o igual que `−0.05` (bloques de 30 días, 5.000 réplicas, semilla `20250109`). Si cualquiera de las dos condiciones falla, se declara `CANDIDATE_NOT_VALIDATED`, el protocolo se detiene, y 2024–2025 permanece cerrado — no se prueba otro modelo con 2023 ni se reabre la selección de la Etapa A. La apertura efectiva del holdout, cuando corresponda, requiere además un registro explícito de fecha y autorización (nombre/rol de quien autoriza), según el manifiesto de provenance.

## Alcance futuro de Balcarce

Balcarce queda completamente fuera de `controlled_daily_v4_external_pergamino`: no participa en selección, ajuste de hiperparámetros, ni confirmación de ningún candidato en esta iteración. Se registra en el manifiesto de provenance como `FUTURE_GEOGRAPHIC_VALIDATION` — una eventual réplica geográfica futura, sujeta a su propio protocolo (probablemente derivado de este mismo documento), nunca concatenada directamente con Pergamino sin estudiar antes el cambio de dominio entre ambos sitios.
