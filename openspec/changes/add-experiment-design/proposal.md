# Change: Add experiment design capability

## Trazabilidad

- **Épica:** 4. Evaluación experimental.
- **Historia de usuario:** HU7 — Diseño y ejecución del plan experimental (primer de tres sub-proyectos: diseño experimental).
- **Fase de CRISP-DM:** Evaluación.
- **Insumo de diseño:** [`openspec/specs/architecture-integration/spec.md`](../../specs/architecture-integration/spec.md) (orquestador de punta a punta), [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md) (anomalías, datos sintéticos), [`openspec/specs/predictive-modeling/spec.md`](../../specs/predictive-modeling/spec.md) (métricas de comparación de modelos).

## Why

HU2-HU6 dejan cada capacidad probada por separado y un orquestador de punta a punta (HU6), pero todavía no hay un diseño experimental formal: qué preguntas se responden, qué configuraciones se comparan, con qué métricas, cuántas repeticiones, y — el bloqueo concreto que impedía correr las 4 configuraciones de la Épica 4 — cómo generar datos sintéticos que compongan con las variables de retardo/ventana móvil de HU4 (limitación documentada en `add-architecture-integration-pipeline`).

## What Changes

- **Preguntas experimentales y factores de evaluación**: ¿la detección de anomalías mejora el desempeño del modelo? ¿los datos sintéticos aportan valor predictivo cuando se combinan con las variables ya diseñadas en HU4? Factores: detección de anomalías (on/off), aumento con datos sintéticos (on/off) — su combinación da las 4 configuraciones de la Épica 4 (base, +sintéticos, +anomalías, completa).
- **Escenarios de escasez y variabilidad**: escasez de datos, aproximada reduciendo el tamaño del conjunto de entrenamiento real (ej. 50% de las filas más recientes antes del corte); variabilidad, aproximada ejecutando cada configuración con múltiples semillas aleatorias y reportando el desvío entre corridas — no se dispone de una fuente de datos con ruido de sensor real distinta a la ya ingerida, así que no se inyecta ruido sintético adicional en esta primera versión.
- **Configuraciones comparativas (ablación)**: las 4 configuraciones de la Épica 4, resultado de cruzar los dos factores de detección de anomalías y aumento sintético.
- **Resolución del bloqueo de datos sintéticos + variables de retardo**: se agrega una función que genera filas sintéticas muestreando conjuntamente las variables predictoras *ya construidas* (retardos, ventanas móviles) y la etiqueta, en vez de las columnas físicas crudas — evita necesitar una fecha ficticia o continuidad temporal real, y reutiliza el mismo enfoque estadístico de HU3 (normal multivariada) sobre el espacio de variables de HU4.
- **Métricas y criterios de evaluación**: se reutilizan sin cambios las de HU4 (`predictive_modeling.evaluation`): precisión, recall, F1 y ROC-AUC de la clase de estrés, más estabilidad (desvío entre repeticiones) y complejidad del modelo.
- **Particiones, semillas y repeticiones**: partición temporal (ya existente, HU3), 5 semillas aleatorias por configuración experimental para poder reportar media y desvío estándar de cada métrica.

## Impact

- **Specs afectadas:** nueva capacidad `experiment-runner`.
- **Specs futuras que dependen de esta:** el segundo *change* de HU7 (procedimiento automatizado y registro con MLflow) ejecuta este diseño; el tercero (ejecución real) corre las 4 configuraciones sobre el dataset real.
- **Código afectado:** nuevo paquete `src/experiment_runner/` con `synthetic_augmentation.py`.
- **Fuera de alcance de este change:** implementación del procedimiento automatizado en sí y su registro en MLflow (segundo *change*); ejecución real de experimentos (tercer *change*); inyección de ruido sintético adicional (no hay todavía una fuente real de ruido de sensor distinta a la ya ingerida — ver "Alternativas consideradas").

## Alternativas consideradas

- **Muestrear datos sintéticos sobre las columnas físicas crudas y asignarles una fecha ficticia consecutiva**: se descarta porque una fecha ficticia insertada en medio de la serie temporal real complicaría la partición entrenamiento/evaluación (¿antes o después del corte?) sin ningún beneficio real, dado que las filas sintéticas no representan continuidad temporal genuina.
- **Diferir la resolución del bloqueo de datos sintéticos a HU8 o dejar solo 2 configuraciones (base, +anomalías)**: se descarta porque el plan de tesis exige explícitamente comparar las 4 configuraciones de la Épica 4; la solución de muestrear sobre el espacio de variables ya construidas es simple y no requiere infraestructura adicional.
- **Inyectar ruido sintético artificial para el escenario de "ruido"**: se descarta por ahora porque no hay una caracterización real del ruido de sensor esperado (más allá de los gaps ya observados en ESA CCI); se prioriza el escenario de escasez, que sí tiene una implementación directa (subconjunto del conjunto de entrenamiento real).

## Estado: implementado

Ver [`openspec/specs/experiment-runner/spec.md`](../../specs/experiment-runner/spec.md) para los requisitos vigentes y la verificación con datos reales.
