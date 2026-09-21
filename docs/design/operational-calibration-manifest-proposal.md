# Propuesta de manifiesto operacional de calibración +1/+2/+3

Estado: **borrador para revisión**. Este documento no es un manifiesto aprobado,
congelado ni habilitado para ajuste. No autoriza entrenamiento, calibración ni
evaluación, y no debe transformarse a `ready_for_fit` hasta resolver todas las
decisiones marcadas como pendientes.

## Propósito y fuentes

La propuesta completa el paso documental previo exigido por el
[diseño multihorizonte](../../openspec/changes/add-daily-multihorizon-predictors/design.md)
y por el validador
[`calibration_manifest.py`](../../src/predictive_modeling/calibration_manifest.py).
Se apoya en la evidencia descriptiva ya registrada en la
[auditoría de preparación](backend-producer-ui-readiness.md), sin repetirla, abrir
holdouts ni calcular resultados de evaluación. También conserva las restricciones
del [ADR-0013](../adr/0013-backend-ui-productor.md) y del
[protocolo experimental vigente](../research/protocolo-experimental-v3.md).

Trazabilidad: HU4/HU6; capacidades `predictive-modeling` y
`architecture-integration`; CRISP-DM modelado, evaluación de desarrollo e
integración. Es una ampliación operacional separada: no modifica
`controlled_daily_v3`, configuraciones HU7, resultados HU8, hipótesis, alcance o
capas de arquitectura. El sistema continúa siendo apoyo a la decisión, no
automatización del riego.

## Campos ya determinados

Estos campos provienen de las specs y del contrato implementado. No son decisiones
que deban reabrirse para obtener un resultado favorable.

| Campo | Valor o regla determinada | Fundamento |
|---|---|---|
| `status` | `draft` | La propuesta contiene decisiones pendientes y no puede habilitar ajuste. |
| `schema_version` | `producer_calibration_plan_v1` | Versión aceptada por el validador. |
| `contract_version` | `producer_daily_h123_v1` | Contrato operacional +1/+2/+3. |
| `calendar_timezone` | `UTC` | Calendario diario explícito del contrato. |
| `horizons` | `[1, 2, 3]` | Tres predictores directos e independientes; no interpolar +3. |
| `dataset.dataset_id` | `melchor_romero_2024_consolidado` | Único dataset local permitido para esta evaluación de desarrollo. |
| `dataset.site` | Melchor Romero | Un solo sitio; no representa validación espacial. |
| `dataset.sha256` | `121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e` | Hash ya documentado por la auditoría; debe volver a verificarse desde la misma instantánea antes de cualquier congelamiento. |
| `dataset.source_kind` | `real` | NASA POWER y ESA CCI, según la procedencia documentada. |
| `dataset.allowed_dates` | 2024-01-01 a 2024-12-31 | Rango completo descrito; no habilita otras fuentes o años. |
| `dataset.population` | Observaciones diarias del sitio durante 2024 con target de humedad observado | No equivale a la población agronómica general. |
| `dataset.provenance` | Variables climáticas de NASA POWER y humedad de suelo de ESA CCI | Deben conservarse sitio, unidades y procedencia. |
| `dataset.prior_exposure` | Dataset ya explorado en v3 y en auditorías; solo desarrollo | Su último tramo no es un holdout independiente. |
| `intended_use` | Evaluar si un bundle exacto permite mostrar probabilidades agrupadas de desarrollo para +1/+2/+3 en una UI de apoyo | No acredita diagnóstico fisiológico, validación externa ni recomendación automática de riego. |
| `event.variable` / `unit` | `soil_moisture` / `m3/m3` | Variable física y unidad del contrato vigente. |
| `event.comparison` | `lt` | Evento: humedad observada menor que el umbral congelado. |
| `event.percentile` | 20 | Conserva el proxy relativo vigente; no es un umbral agronómico. |
| `event.threshold_source` | `training_observations_only` | Prohíbe informar el umbral con calibración o evaluación. |
| `event.threshold_reference` | Igual a `partitions.train` | Misma referencia observada para los tres horizontes; la purga posterior depende de `target_date`. |
| Partición | Train 2024-01-01..2024-08-06; calibración 2024-08-07..2024-10-18; evaluación 2024-10-19..2024-12-31 | Aplicación cronológica 60/20/20 sobre 366 días, con redondeo hacia abajo de los dos primeros tramos. La elegibilidad final será menor por purga, features y targets faltantes. |
| `model_plan.family` | `random_forest` | Familia propuesta por el diseño; no implica que sus probabilidades califiquen. |
| `training_seeds` | `[0, 1, 2, 3, 4]` | Sensibilidad del procedimiento; no son cinco poblaciones independientes. |
| `calibration.method` | `sigmoid` | Se ajusta por horizonte solo sobre calibración, sin reajustar el estimador. |
| `probability_bins` | `equal_width`, 10 bins, incluir 1 en el último | Agrupamiento normativo; los bins vacíos o sin soporte siguen visibles. |
| `uncertainty.nominal_level` | 0.95 | Nivel nominal exigido; no garantiza estimabilidad con esta muestra. |
| `multiplicity.family_dimensions` | horizonte, semilla, ventana de estabilidad y bin respaldado | Familia simultánea mínima exigida por el diseño y el validador. |
| `log_loss.clipping_epsilon` | Propuesta técnica: `1e-15` | Protección numérica uniforme para todos los comparadores; no es una tolerancia de aprobación. Debe confirmarse contra la implementación concreta. |

El `sensor_id` operativo, la lista exacta de variables/unidades, las versiones de
dependencias y los hiperparámetros efectivos deben copiarse de una identidad de
dataset y un contrato de modelo explícitamente seleccionados. No se completan desde
fixtures ni desde cifras históricas: la spec canónica advierte que
`n_estimators=100` y `max_depth=5` son evidencia histórica, no una configuración
universal vigente.

## Decisiones pendientes y propuesta para revisión

Los valores siguientes son candidatos **pre-resultados**. Aun aceptados, no
prometen que el gate sea evaluable o que un horizonte pase.

### Soporte

Propuesta candidata:

- `minimum_bin_count: 10`;
- `minimum_class_count: 10` por clase en cada alcance exigido;
- `minimum_temporal_blocks: 4`.

Fundamento técnico: diez casos evita tratar bins casi unitarios como rangos
respaldados; diez casos por clase es un piso de detectabilidad, no una garantía de
precisión; cuatro bloques exige repetición temporal mínima y evita que un único
episodio sostenga la afirmación. Estos pisos se aplican al período completo y a
cada ventana, sin combinar semillas ni horizontes para inflar el conteo.

Elección de producto que requiere revisión: aceptar estos pisos implica que la UI
puede ocultar porcentajes con frecuencia. Con ventanas de hasta 37 días, exigir más
soporte puede volver el gate estructuralmente no evaluable; exigir menos produciría
porcentajes demasiado frágiles. No existe evidencia suficiente para declarar que
`10/10/4` es el equilibrio correcto. Si no se ratifica, los tres campos permanecen
pendientes y el manifiesto sigue incompleto.

### Tolerancias

`epsilon_ece` y `epsilon_bin` quedan **sin valor propuesto para congelamiento**.
Técnicamente deben estar en (0, 1), expresarse en puntos de probabilidad y aplicarse
a límites superiores simultáneos, no a estimaciones puntuales. Sin embargo, ni las
specs ni la auditoría definen qué error probabilístico es útil para una decisión del
productor o qué costo tienen sobreconfianza y subconfianza.

Propuesta para la revisión de producto: acordar primero el máximo error global y
por rango que todavía haría honesto mostrar un porcentaje. Como referencia de
discusión, `0.10` para ECE y `0.15` por bin significarían tolerar límites
superiores de 10 y 15 puntos porcentuales, respectivamente; **no se recomiendan ni
se incorporan al manifiesto porque no existe evidencia estadística a su favor**. Si esa
precisión no sirve al uso real, no corresponde relajarla para aprobar: debe
mantenerse `display_probability=null`.

### Cobertura

Propuesta candidata: `coverage.minimum: 0.80`.

Fundamento técnico: obliga a que al menos cuatro de cada cinco observaciones estén
en bins que alcancen `minimum_bin_count`, y evita aprobar a partir de una fracción
conveniente del rango predicho. Se informará además el rango de probabilidades
respaldado.

Elección de producto que requiere revisión: 80 % define cuánto comportamiento no
respaldado tolera la UI; no es una constante estadística. Debe confirmarse que el
producto acepta ocultar el porcentaje en el 20 % restante y que no presentará ese
silencio como riesgo bajo.

### Bloques temporales

Propuesta candidata: bloques contiguos de 7 días sobre el calendario de
`target_date`.

Fundamento técnico: la unidad semanal conserva dependencia de corto plazo en una
serie diaria y es mayor que el hueco máximo de humedad observado de 6 días. Usar
`target_date` alinea el bloque con el resultado evaluado y con la purga temporal.
No se usarán filas iid, semillas ni horizontes como réplicas.

Pendiente metodológico: siete días no fue estimado con evaluación ni constituye
una longitud universal. Requiere revisión antes de congelar. Si cuatro bloques
distintos no pueden sostenerse después de faltantes y purgas, el resultado será
`insufficient_evidence`; no se reducirá la longitud después de mirar resultados.

### Ventanas de estabilidad

Propuesta candidata, sobre `target_date`, no solapada y con
`criteria_reference: global`:

1. 2024-10-19..2024-11-24;
2. 2024-11-25..2024-12-31.

Fundamento técnico: divide los 74 días calendario de evaluación en dos mitades de
37 días sin seleccionar cortes por métricas ni eventos observados. Mantiene los
mismos criterios globales de soporte, cobertura y tolerancia.

Riesgo explícito: cada ventana tendrá menos de 37 pares elegibles después de targets
faltantes y requisitos causales. Es plausible que alguna clase, bin o bloque no
alcance soporte. Eso debe producir `insufficient_evidence`, no una nueva ventana
post hoc. La interpretación estacional de solo dos ventanas de un único año es
limitada y no acredita estabilidad interanual.

### Incertidumbre

Propuesta técnica:

- método: bootstrap de bloques móviles de 7 días, sincronizado por fechas entre
  horizontes y semillas;
- `replicates: 5000`;
- `resampling_seed: 20260919`;
- tratamiento de huecos: conservar la grilla diaria; nunca imputar el target;
  recalcular cada estadístico solo con pares observados y declarar inválida una
  réplica o alcance que no conserve el soporte predeclarado.

Fundamento técnico: el remuestreo conjunto preserva la dependencia entre resultados
que comparten días y permite construir una familia simultánea. Cinco mil réplicas
son una propuesta de estabilidad computacional del cuantil, no cinco mil
observaciones ni precisión inferencial adicional. La semilla fija aporta
reproducibilidad y no se elige por resultados.

Pendiente metodológico: debe verificarse con fixtures conocidos que el algoritmo
respeta límites, huecos y sincronización. Si la cantidad de bloques distintos es
insuficiente o los límites no son estables, no se publican bandas ni porcentajes.

### Multiplicidad

Propuesta técnica: límite superior simultáneo mediante el máximo estadístico
obtenido en cada réplica de bloques sobre toda la familia predeclarada:

- ECE por horizonte, semilla, período completo y ventana;
- error absoluto de cada bin respaldado en esos mismos alcances.

El cuantil 0.95 del máximo se usa para construir límites superiores family-wise.
No se filtran combinaciones desfavorables ni bins de poco soporte del ECE; los bins
no respaldados se muestran y quedan fuera de cualquier afirmación publicable.

Revisión requerida: confirmar que se desea una única familia conservadora para los
tres horizontes. Separar familias por horizonte produciría límites menos exigentes,
pero permitiría tres afirmaciones sin control conjunto y cambiaría el significado
del gate. No debe decidirse después de observar resultados.

### Semilla de despliegue

Propuesta candidata: `deployment_seed: 0`.

Fundamento: es el primer valor de la serie predeclarada, se elige por convención y
antes de entrenar; no presupone desempeño superior. Las otras semillas se conservan
como sensibilidad obligatoria.

Elección de producto que requiere revisión: confirmar si el artefacto servido debe
ser el de semilla 0 o un procedimiento determinista distinto predeclarado. Nunca se
elegirá la mejor semilla observada.

## Viabilidad esperable sin abrir evaluación

La auditoría describe 366 días, 278 observaciones de humedad, 88 nulos en 50
episodios y un hueco máximo de 6 días. Los pares potenciales conservadores antes de
partir son 227 (+1), 232 (+2) y 220 (+3). Esos números solo muestran que la
preparación es ejecutable; no anticipan soporte final.

La evaluación propuesta tiene como máximo 74 días calendario antes de purga,
faltantes y features; cada ventana, como máximo 37. La calibración tiene como máximo
73 días calendario antes de las mismas restricciones. Con diez bins, tres
horizontes, cinco semillas y criterios exigidos por ventana, es razonable esperar
que algunos bins estén vacíos o sin soporte y que alguna ventana carezca de casos
por clase suficientes. Las cinco semillas no aumentan el número de resultados
observados. Por lo tanto:

- es viable implementar y ejecutar en el futuro el procedimiento predeclarado;
- no puede afirmarse hoy que la calibración sigmoid sea ajustable en cada horizonte;
- no puede afirmarse que soporte, cobertura o límites simultáneos sean estimables;
- `insufficient_evidence` es un desenlace esperable y válido, no un fallo que
  habilite relajar el manifiesto.

No se consultó el tramo de evaluación, no se calcularon prevalencias por horizonte
y no se abrió ningún holdout v4 o externo para redactar esta propuesta.

## Implementación posible si la evidencia es insuficiente

Sin porcentajes calificados todavía se puede implementar, en una entrega posterior:

- preparación causal y bundles independientes +1/+2/+3 con identidad completa;
- alerta binaria basada en `score_kind=raw` y umbral 0.5, claramente separada de
  `display_probability`;
- `display_probability=null`, `probability_status=not_qualified` y motivos
  específicos como `insufficient_class_support`,
  `insufficient_temporal_blocks`, `insufficient_coverage` o
  `unsupported_probability_range`;
- informes y artefactos reproducibles que conserven bins vacíos, fallos de soporte,
  hashes y decisiones del manifiesto;
- el motor del assessment y sus fallos fail-closed validados solo con fixtures
  sintéticos, sin presentar esos fixtures como calibración real;
- acumulación futura de datos reales cronológicos bajo un protocolo nuevo y
  predeclarado, sin reusar como independiente el período ya examinado.

No corresponde reducir bins, mover ventanas, cambiar semilla, acortar bloques o
ensanchar tolerancias después de conocer resultados. Cualquier rediseño posterior
requiere nueva versión; los datos ya consultados quedan declarados exploratorios.

## Decisiones necesarias antes de completar el manifiesto

1. Ratificar o reemplazar los pisos de soporte `10/10/4`.
2. Definir tolerancias de producto para ECE y error por bin; hoy permanecen vacías.
3. Ratificar cobertura mínima de 0.80 y el comportamiento de UI fuera del rango
   respaldado.
4. Ratificar bloques móviles de 7 días y el tratamiento fail-closed de huecos.
5. Ratificar las dos ventanas de 37 días sobre `target_date`.
6. Ratificar 5000 réplicas, semilla de remuestreo 20260919 y máximo estadístico
   conjunto como control de multiplicidad.
7. Ratificar semilla de despliegue 0 o definir otro procedimiento determinista
   antes de observar resultados.
8. Identificar el `sensor_id`, variables/unidades, versiones y los hiperparámetros
   efectivos del Random Forest; no heredar valores históricos por omisión.

Hasta resolver los ocho puntos, el estado correcto continúa siendo
`incomplete_assessment_plan`.
