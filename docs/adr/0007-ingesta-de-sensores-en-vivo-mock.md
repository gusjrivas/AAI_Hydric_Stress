# ADR-0007: Ingesta de sensores en vivo (push) con generador mock

## Estado

Aceptado (2026-08-23)

## Contexto

`openspec/specs/alerting-ui/spec.md` y `docs/seguimiento-tareas.md` documentan explícitamente, desde `add-alerting-ui`, que no hay ingesta de datos de sensores en vivo — el dataset es el mismo consolidado histórico de HU2, configurable por nombre pero no por fuente en tiempo real. Con el motor de selección automática (`add-model-selection-engine`) y su caché (`add-selection-caching`) ya resueltos, el backend puede sostener pronósticos frecuentes sin pagar el costo de reentrenar/re-seleccionar en cada corrida — eso destraba conectar una fuente que actualice el dataset seguido, que antes hubiera sido impracticable.

No existe todavía ningún sensor real disponible para este proyecto. Se necesita un generador mock que produzca lecturas plausibles, y una forma de que esas lecturas entren al sistema, sin comprometer la reproducibilidad de los resultados de HU7/HU8 ya verificados sobre el dataset histórico `melchor_romero_2024_consolidado`.

## Decisión

### Ingesta por *push*: un endpoint HTTP genérico, el mock es un cliente sintético

Se agrega `POST /sensors/readings` en el backend (`backend/app/routers/sensors.py`), que recibe una lectura (timestamp + valores, parcial está permitido) y la agrega al dataset configurado por `ALERTING_UI_DATASET`/`DATASET_NAME` — el mismo que ya lee el pipeline de pronóstico. El endpoint no sabe ni le importa si quien llama es un sensor real o un script mock: es la interfaz de producción real, deliberadamente agnóstica del origen de la lectura.

El generador mock (`src/data_ingestion/mock_sensor.py::generate_next_reading`) y un script cliente aparte (`scripts/simulate_sensor_readings.py`) simulan tráfico de sensor llamando a ese mismo endpoint por HTTP, exactamente como lo haría una integración real el día que exista.

### Dataset en vivo separado del histórico de investigación

Las lecturas en vivo (reales o simuladas) se acumulan en el dataset que apunte `ALERTING_UI_DATASET` en cada despliegue — nunca en `melchor_romero_2024_consolidado`, que queda intacto para siempre como evidencia de HU7/HU8. Un despliegue con sensores en vivo simplemente configura esa variable a un nombre distinto (ej. `sensores_en_vivo`); no hace falta ninguna lógica de "no tocar el dataset de investigación", el mecanismo separa ambos casos por construcción.

### Backfill inicial vía script, no vía la API

`scripts/seed_mock_sensor_dataset.py` genera de una sola vez un backfill de varios días de historia sintética (necesaria para que `run_end_to_end_pipeline` tenga suficiente profundidad para calcular retardos/ventanas móviles desde el primer pronóstico), usando el mismo generador que las lecturas incrementales. No se expone como endpoint HTTP: es una operación de setup deliberada, de una sola vez, que no debería poder dispararse por accidente ni automatizarse por un cliente externo.

### Generador: random walk acotado, sin estado propio

`generate_next_reading` no mantiene estado en memoria: cada lectura nueva se genera a partir de la última fila ya persistida en el dataset (leída desde el propio archivo), con un paso aleatorio chico recortado a los rangos físicos ya definidos en `data_quality.rules.AGRONOMIC_RANGES` (reuso directo, sin inventar nuevos límites). Esto hace que el generador sea sin estado entre invocaciones — el propio dataset es la única fuente de verdad de "dónde va la serie", así que backfill y lecturas incrementales pueden ejecutarse en procesos separados sin coordinación adicional.

## Alternativas consideradas

- **Pull/cron: un script standalone que escribe directo al archivo, sin endpoint**: se descarta — no modela cómo entrarían datos de un sensor real (que empujaría lecturas a un gateway, no esperaría a que algo lo consulte), y quedaría como deuda a rehacer el día que haya un sensor de verdad. El costo de construir el endpoint ahora es bajo y deja la arquitectura correcta desde el principio.
- **Append directo al dataset histórico `melchor_romero_2024_consolidado`**: se descarta de forma explícita — modificaría el archivo que sustenta hallazgos de HU7/HU8 ya documentados con números concretos citados en las specs, comprometiendo la reproducibilidad de esa evidencia.
- **Ruido independiente por lectura (sin memoria) en vez de random walk**: se descarta por realismo — un sensor real no da valores completamente independientes día a día; un random walk acotado es la aproximación más simple que evita saltos bruscos visiblemente artificiales al graficar la serie.
- **Consolidar el dataset en vivo con el histórico antes de cada pronóstico**: se descarta por ahora — agrega una pieza de diseño propia (¿cómo se concilian ambas fuentes en el tiempo?) sin un beneficio claro para esta iteración; el dataset en vivo funciona de punta a punta por sí solo. Queda anotado como mejora futura si hiciera falta enriquecer el histórico de entrenamiento con contexto de años previos.

## Consecuencias

- `ALERTING_UI_DATASET` pasa a tener dos usos legítimos por deployment: el histórico de investigación (default actual, sin cambios) o un dataset en vivo alimentado por sensores — la elección es de configuración, no de código.
- El endpoint de ingesta no tiene autenticación en esta iteración (fuera de alcance) — aceptable para un prototipo de tesis sin exposición pública, a revisar antes de cualquier despliegue real expuesto a internet.
- `et0` sigue sin generarse por el mock (se deriva en preprocesamiento, igual que con las fuentes reales) — consistente con el contrato ya existente, no una limitación nueva.
- El dataset en vivo, al no consolidarse con el histórico, empieza su propia serie desde cero (más el backfill del script de seed) — sus primeros pronósticos no se benefician de los ~357 días de contexto del dataset histórico.

## Referencias

- [ADR-0006: Disparo de recalibración desde la UI y reacoplamiento a MLflow](0006-recalibracion-disparada-desde-la-ui.md)
- `openspec/changes/add-selection-caching/` — prerequisito de performance que este ADR asume resuelto.
- `openspec/changes/add-mock-sensor-ingestion/` — spec delta y plan de implementación.
- `src/data_quality/rules.py` (`AGRONOMIC_RANGES`) — rangos físicos reutilizados por el generador.
