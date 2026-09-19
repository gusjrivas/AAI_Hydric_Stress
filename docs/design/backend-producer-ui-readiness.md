# Auditoría de preparación del backend para la UI del productor

Fecha: 2026-09-18. Rama auditada: `feat/hu6-backend-soporte-ui`, commit base
`8047fe3a101166956df6351a2fc9f99b36faf893`. Alcance: revisión previa; no se
implementaron funcionalidades, no se modificaron datos, modelos, experimentos,
specs canónicas ni protocolos.

> Actualización de gobernanza (2026-09-19): el autor aceptó ADR-0013 y los cuatro
> changes. Se levanta el gate de aprobación para implementar, pero permanecen los
> bloqueos técnicos y metodológicos identificados por esta auditoría, incluido el
> manifiesto obligatorio previo al primer ajuste multihorizonte.

## Conclusión por change

| Change | Conclusión | Fundamento y siguiente condición |
|---|---|---|
| [`add-producer-sensor-catalog`](../../openspec/changes/add-producer-sensor-catalog/proposal.md) | **Listo con condiciones** | Se pueden reutilizar el validador y aislamiento por `sensor_id`, el contrato Parquet y la captura con SHA-256. Faltan el repositorio de catálogo, consultas por ventana y, antes de prometer consistencia, escritura atómica y exclusión entre procesos. Es la primera entrega recomendada. |
| [`add-daily-multihorizon-predictors`](../../openspec/changes/add-daily-multihorizon-predictors/proposal.md) | **Bloqueado para el primer ajuste y para publicar porcentajes** | Es implementable el contrato y el etiquetado +1/+2/+3, pero el manifiesto previo obligatorio aún no fija soporte, tolerancias, cobertura, bloques, ventanas, multiplicidad ni semilla de despliegue. La evidencia disponible no garantiza que el gate sea evaluable o aprobado. |
| [`extend-dated-alert-feedback`](../../openspec/changes/extend-dated-alert-feedback/proposal.md) | **Listo con condiciones** | El almacén append-only, revisión e idempotencia pueden construirse contra fixtures. La integración real depende de una identidad v2 persistida y de resolver la autoridad del bloqueo de demo. No depende de que las probabilidades califiquen. |
| [`add-producer-forecast-api`](../../openspec/changes/add-producer-forecast-api/proposal.md) | **Bloqueado para cierre integral; listo en su porción catálogo/histórico** | La fachada aditiva es compatible con FastAPI y legacy, pero emisión, feedback y assessments dependen de los otros changes. Catálogo y `GET readings` pueden entregarse sin esperar al modelado. |

El [ADR-0013](../adr/0013-backend-ui-productor.md) y los cuatro changes fueron
aceptados por el autor el 2026-09-19. Esta aceptación posterior levanta el gate de
gobernanza, sin alterar los hallazgos ni autorizar por sí sola ajustes experimentales.

## Trazabilidad e impacto

| HU / capacidad | CRISP-DM | Impacto metodológico |
|---|---|---|
| HU2 / `data-ingestion` | Comprensión y preparación de datos | Metadatos y consulta operacional; no cambia el conjunto experimental. |
| HU4 / `predictive-modeling` | Modelado y evaluación de desarrollo | Nuevo contrato operacional +1/+2/+3. No cambia `controlled_daily_v3`, v4, configuraciones formales ni resultados HU7/HU8. |
| HU5 / `human-feedback` | Evaluación e integración | Separa opinión registrada de elegibilidad temporal; no reinterpreta feedback legacy. |
| HU6 / `architecture-integration` y `alerting-ui` | Despliegue e integración | API v2 aditiva dentro de la arquitectura existente. Sin cambio de hipótesis, propósito o alcance. |

## Hallazgos priorizados

### Bloqueos reales

1. **El ajuste multihorizonte no puede comenzar todavía.** El
   [diseño del change](../../openspec/changes/add-daily-multihorizon-predictors/design.md)
   exige congelar antes de mirar resultados `minimum_bin_count`,
   `minimum_class_count`, `epsilon_ece`, `epsilon_bin`, cobertura mínima, bloques,
   ventanas de estabilidad, remuestreo, multiplicidad, clipping y semilla de
   despliegue. Fijarlos después sería ajuste sobre evaluación. Hasta entonces el
   estado correcto es `incomplete_assessment_plan`; no hay porcentaje publicable.

2. **La persistencia actual no satisface concurrencia ni idempotencia v2.**
   [`storage.py`](../../src/data_ingestion/storage.py) guarda Parquet directamente;
   `append_reading` hace read-modify-write sin reemplazo atómico ni lock entre
   procesos. [`registry.py`](../../src/human_feedback/registry.py) hereda lo mismo.
   El lock de caché en [`backend/app/pipeline.py`](../../backend/app/pipeline.py)
   solo protege memoria dentro de un proceso. Hace falta un primitivo compartido
   de lock, revisión y escritura atómica antes del catálogo mutable, reviews o
   claves idempotentes duraderas.

3. **El bloqueo de demo carece de autoridad backend reutilizable.** La demo y su
   UI bloquean mutaciones en su propio flujo, pero los routers actuales no consultan
   un estado común que permita a v2 responder `demo_write_locked`. Antes de emitir o
   revisar por v2 debe definirse una interfaz de solo lectura hacia el manifiesto de
   demo, o corregir el contrato si esa garantía no será responsabilidad del backend.
   Catálogo descriptivo e histórico pueden avanzar porque no escriben lecturas ni
   pronósticos.

4. **La API completa depende de una emisión que hoy no existe.**
   [`forecast.py`](../../backend/app/routers/forecast.py) produce solo t+3 y persiste
   una fila por `fecha`; [`feedback.py`](../../backend/app/routers/feedback.py) también
   busca por fecha. No hay `forecast_id`, batch, slot por horizonte, revisión
   versionada ni assessment. Debe usarse almacenamiento v2 separado: ampliar el log
   legacy rompería su unicidad y la demo #202–#205.

### Reutilización y brechas implementables

- Son reutilizables `validate_sensor_id`/`dataset_name_for` de
  [`sensor_naming.py`](../../src/data_ingestion/sensor_naming.py), los schemas de
  ingesta, `load_dataset`, y especialmente `load_dataset_snapshot`, que deriva
  DataFrame y SHA-256 de los mismos bytes. El `snapshot_id` v2 debe ser el hash de
  contenido, no `(mtime, size)` de `get_dataset_fingerprint`.
- El etiquetador vigente en
  [`labeling.py`](../../src/predictive_modeling/labeling.py) usa `shift(-h)` por
  posición. No cumple por sí solo el calendario exacto v2 cuando hay días omitidos;
  se necesita una variante que una por `timestamp + h días` y purgue por
  `target_date`. Es una incompatibilidad demostrada con el nuevo requisito, no una
  preferencia de implementación.
- La procedencia legacy admite `real | sintetico`, mientras el contrato v2 publica
  `real | synthetic | unknown`. Hace falta traducción explícita en el adaptador; no
  se debe reescribir Parquet ni inferir `real` por ausencia de una marca.
- FastAPI, dependencias de directorios y routers por sensor son reutilizables. La
  envoltura `{error:{...}}`, cursores estables y códigos v2 requieren handlers y
  schemas propios; la respuesta legacy `detail` puede mantenerse sin conflicto.
- `calendar_timezone=UTC`, `server_today`, `as_of_date` y `target_date` son
  implementables sin fecha simulada. La demo debe seguir usando sus endpoints
  legacy; v2 no debe ampliar su controlador ni cambiar su reloj.

### Decisiones que pueden esperar

- La identidad normativa dice que `forecast_id` se deriva de sensor, fecha de datos,
  horizonte y contrato. La frase “dos emisiones para el mismo día siguen siendo
  distintas” es ambigua si se refiere al mismo `as_of_date`; antes de implementar
  emisión debe aclararse si batch/snapshot/modelo forman parte de la identidad. No
  bloquea catálogo ni histórico.
- Exigir una segunda revisión madura para una opinión emitida durante el día objetivo
  es una política conservadora ya especificada, pero con costo de UX. Debe ratificarse
  antes de HU5; no es una contradicción técnica.
- El backend inspeccionado no implementa identidad/autenticación de usuario. “Aplicar
  acceso existente” hoy significa conservar ese estado del prototipo; autenticación
  productiva queda fuera del change y no debe atribuirse autoría humana inexistente.

## Evidencia descriptiva de datos y límites

Las fuentes permitidas están identificadas en
[`hu2-fuentes-datos-acceso.md`](../research/hu2-fuentes-datos-acceso.md): NASA POWER
y ESA CCI Soil Moisture forman el conjunto de desarrollo; SMN continúa bloqueado y
Copernicus requiere registro. El protocolo permite reutilizar el dataset local v3
solo como **desarrollo ya explorado**, nunca como holdout independiente. No se abrió
ningún holdout protegido ni artefacto v4.

Se inspeccionó en modo solo lectura
`data/melchor_romero_2024_consolidado.parquet` (SHA-256
`121697dd5af202633f24adf4244a793477d34bf5e4cf4a1f10d7b2ca1b33ba8e`):

- 366 filas diarias UTC, 2024-01-01 a 2024-12-31, sin fechas omitidas ni duplicadas;
  procedencia `real` en las 366 filas.
- NASA POWER aporta temperatura (`degC`), humedad relativa (`%`), precipitación
  (`mm/day`), radiación (`MJ/m2/day`) y viento (`m/s`); ESA CCI aporta humedad de
  suelo (`m3/m3`). Las cinco variables climáticas están completas.
- Humedad de suelo: 278 observaciones y 88 nulos (75,96 % de cobertura), repartidos
  en 50 episodios; hueco máximo de 6 días. ET0 y las cuatro variables opcionales
  están totalmente nulas.
- Pares conservadores con humedad observada tanto en `t` como en `t+h`: 227 para
  +1, 232 para +2 y 220 para +3. Son ejemplos potenciales descriptivos, no conteos
  finales de entrenamiento: todavía faltan purga por corte, features causales y
  particiones predeclaradas.

No se calculó soporte por clase para h=1/h=2/h=3: el umbral del nuevo esquema
60/20/20 y su manifiesto aún no están congelados. El umbral y prevalencias históricas
de `controlled_daily_v3` pertenecen a otra partición y no se reutilizan para declarar
viabilidad. Con un único sitio/año, 88 targets faltantes y diez bins, la evaluación
de soporte, cobertura, estabilidad y bootstrap temporal es ejecutable una vez
predeclarada, pero puede terminar legítimamente en `insufficient_evidence`.

## Plan de calibración: estado de decisiones

Ya está especificado: predictores directos, snapshot común, umbral aprendido solo
en entrenamiento y compartido como referencia inicial, split cronológico 60/20/20,
RF operacional congelado, calibración sigmoid separada, cinco semillas como análisis
de sensibilidad, diez bins, targets observados, intervalos temporales del 95 %,
baselines sobre las mismas fechas y publicación por bundle/horizonte/rango compatible.

Antes del primer ajuste deben justificarse y versionarse los parámetros enumerados
en el bloqueo 1, además de dataset/SHA, exposición previa, fechas, hiperparámetros
efectivos y semilla de despliegue. Los fixtures sintéticos solo pueden probar el
cálculo y los fallos del gate. Brier/log-loss y semillas son controles auxiliares.
Hasta que un bundle exacto pase todos los criterios, `display_probability` debe ser
`null`; la alerta binaria puede seguir disponible con score y estado explícitos.
No hay probabilidades validadas ni evidencia externa en esta auditoría.

## Primera entrega recomendada

**Alcance:** `add-producer-sensor-catalog` tareas 1–6 y la porción de
`add-producer-forecast-api` 1.1–1.2: repositorio de metadatos, servicios de ventana
y endpoints v2 de sectores, sensores y lecturas. No marcar tareas hasta implementar
y validar.

**Componentes previsibles:** nuevos módulos de catálogo/consulta bajo
`src/data_ingestion/`; primitivas atómicas en `src/data_ingestion/storage.py`;
schemas y router v2 bajo `backend/app/`; registro del router en `main.py`; pruebas
unitarias en `tests/` y de contrato en `backend/tests/`. No hace falta tocar
modelado ni feedback.

**Dependencias previas:** aceptar ADR/changes; fijar formato/versionado del archivo
`data/ui_metadata`, lock entre procesos y traducción de procedencia. El catálogo
debe tratar adopción/renombre/selección como metadatos, sin alterar la serie.

**Pruebas de aceptación y finalización:**

1. Alta/adopción, unicidad, revisión optimista, reinicio y dos escritores: uno crea
   y el otro recibe conflicto, sin archivo parcial.
2. Ventanas 7/30 del mismo hash y extremo comparten exactamente filas; nulos,
   `missing_dates`, unidades, procedencia y cobertura permanecen explícitos.
3. Sensor registrado sin datos devuelve `no_readings`; desconocido, error de
   almacenamiento y calendario inválido no se convierten en lista vacía.
4. GET no escribe, no entrena y no llama MLflow. Adoptar una serie conserva SHA-256
   y bytes; datasets históricos conservan sus hashes.
5. Pasan pruebas dirigidas de storage, catálogo, endpoints legacy de sensores y la
   demo que consume ingesta/pronóstico legacy. OpenAPI y fixtures concuerdan.
6. Diff limitado al change, enlaces válidos, `git diff --check` limpio y evidencia
   de tests registrada; solo entonces se marcan tareas alcanzadas.

**Exclusiones:** predictores +1/+2/+3, fitting/calibración, porcentajes,
emisiones/reviews/recalibración v2, migración legacy, UI, autenticación, escritura
de nuevas lecturas, cambios de datos y cualquier experimento HU7/HU8.

## Verificaciones realizadas y pendientes

Realizadas: lectura de fuentes de verdad, cuatro changes y código directamente
relacionado; contraste con endpoints legacy y demo; inspección descriptiva en
contenedor local sin red y repositorio montado solo lectura; verificación de rama,
upstream y árbol inicialmente limpio. No se ejecutó suite completa porque el cambio
de esta sesión es exclusivamente documental.

Pendientes para la implementación: aceptar ADR/changes; congelar el manifiesto antes
del primer ajuste; definir autoridad de lock de demo e identidad de reemisión;
ejecutar las pruebas dirigidas de la primera entrega. Esta auditoría no declara CI
verde ni tareas de implementación completadas.
