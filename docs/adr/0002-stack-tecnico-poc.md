# ADR-0002: Stack técnico del prototipo experimental

## Estado

Aceptado (2026-08-06)

## Contexto

El ADR-0001 fija una arquitectura modular en 5 capas para poder aislar el aporte de cada componente durante la evaluación experimental (Épica 4). Antes de abrir el primer *change* de código (HU2, ingesta de datos) es necesario fijar el stack técnico mínimo: lenguaje de modelado, mecanismo de registro de experimentos y estrategia de persistencia de datos.

El proyecto es un prototipo experimental de tesis, ejecutable en entorno local (sección 8.6 del plan de proyecto), con 600 horas de esfuerzo estimado y sin alcance de despliegue productivo. Al mismo tiempo, el trabajo contempla explícitamente una posible extensión futura (prueba de concepto física con sensores, y "recomendaciones para futuras implementaciones de mayor escala" en el alcance). El stack elegido debe ser simple de operar durante la tesis, pero no debe imponer decisiones que obliguen a reescribir las capas de IA si el proyecto escala más adelante.

## Decisión

### Lenguaje y librerías de modelado

Python, con scikit-learn para los modelos de referencia y modelos candidatos supervisados, y PyTorch disponible para arquitecturas de mayor complejidad (p. ej. modelos generativos para datos sintéticos o detección de anomalías basada en aprendizaje profundo), en caso de que el estado del arte (HU1) o los resultados experimentales (HU4) justifiquen su uso. Python se elige por ser el ecosistema estándar de investigación en ML/DL, con soporte maduro para series temporales, detección de anomalías y generación de datos sintéticos, y por facilitar la reproducibilidad exigida en la gobernanza de datos (sección 12.1).

### Registro y versionado de experimentos

> **Reemplazado por [ADR-0004](0004-orquestacion-experimentos-mlflow-minio.md) (2026-08-16).** La decisión original de esta sección (MLflow local sin servidor) queda documentada por su valor histórico, pero ya no rige: ADR-0004 adopta un servidor de tracking de MLflow con backend Postgres y almacenamiento de artefactos MinIO (S3-compatible) como patrón vigente, adelantando la recomendación de escalado futuro mencionada en el contexto de este ADR.

MLflow, ejecutado localmente (sin servidor remoto), para registrar parámetros, métricas, artefactos y versiones de modelo de cada corrida. Cada configuración experimental de la Épica 4 (base, base+sintéticos, base+anomalías, completa) se registra como un *run* independiente, lo que permite comparar configuraciones y sostener la trazabilidad de hiperparámetros, métricas y decisiones exigida en las secciones 12.1 y 13.3 del plan de proyecto.

### Persistencia de datos

La persistencia arranca simple: archivos Parquet/CSV en almacenamiento local, versionados junto con su diccionario de datos (HU2). Sin embargo, ningún módulo de la capa 3 (módulos de IA) accede directamente a estos archivos. Todo acceso a datos pasa por un **contrato de acceso a datos versionado** (una interfaz estable, p. ej. funciones `load_dataset(...)` / `save_dataset(...)` que devuelven y reciben estructuras tabulares estándar como `DataFrame`), definido como parte de la capa 2 (almacenamiento y preprocesamiento) del ADR-0001.

Este contrato es el que se congela como estable; el backend concreto (Parquet local hoy, SQLite o una base de series temporales como TimescaleDB/InfluxDB más adelante si se incorpora la prueba de concepto física con sensores en tiempo real) es un detalle de implementación intercambiable detrás de esa interfaz. Ninguna capa de IA, de generación de alertas o de retroalimentación humana debe depender del formato de almacenamiento subyacente.

## Alternativas consideradas

- **Fijar desde ahora una base de datos de series temporales (TimescaleDB/InfluxDB)**: se descarta para el arranque porque agrega infraestructura y complejidad operativa que el alcance actual (prototipo local, HU2) no requiere, y el plan de proyecto trata la instrumentación física con sensores como una validación opcional y complementaria, no como la fuente principal de datos.
- **Persistencia ad-hoc sin contrato de acceso** (cada módulo lee archivos directamente): se descarta porque acoplaría los módulos de IA al formato de archivo elegido hoy, contradiciendo el principio de intercambiabilidad de capas del ADR-0001 y obligando a reescribir código de modelado si el backend cambia al escalar.
- **DVC para versionado de datos y experimentos**: se descarta por ahora frente a MLflow porque el volumen de datos esperado en el prototipo no justifica versionar datasets completos con DVC; puede reevaluarse si los datasets crecen significativamente en una fase posterior.

## Consecuencias

- Antes de implementar HU2 (ingesta de datos) debe definirse y documentarse la interfaz del contrato de acceso a datos, no solo el formato de archivo.
- Cualquier cambio futuro de backend de almacenamiento (por ejemplo, al incorporar la prueba de concepto física con sensores en tiempo real) se resuelve implementando una nueva versión del contrato de acceso a datos, sin modificar los módulos de calidad/robustez, modelado predictivo o retroalimentación humana.
- ~~MLflow local no requiere infraestructura adicional durante la tesis, pero si el proyecto escala a un entorno colaborativo o productivo, deberá reevaluarse un servidor de tracking centralizado.~~ Superseded por ADR-0004: el servidor de tracking centralizado se adopta ya, no se difiere.
- El uso de PyTorch queda habilitado pero no obligatorio: su adopción concreta se decidirá en HU4 según el desempeño observado, evitando complejidad innecesaria si los modelos supervisados clásicos resultan suficientes.

## Referencias

- [ADR-0001: Arquitectura modular para la detección temprana de estrés hídrico](0001-arquitectura-modular-deteccion-estres-hidrico.md)
- Plan de proyecto del Trabajo Final — Maestría en Inteligencia Artificial, Esp. Lic. Gustavo Julián Rivas, FIUBA (v4.1, 2026-08-01), secciones 4, 8.3, 12.1 y 13.3.
