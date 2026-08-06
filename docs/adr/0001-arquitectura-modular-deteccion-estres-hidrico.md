# ADR-0001: Arquitectura modular para la detección temprana de estrés hídrico

## Estado

Aceptado (2026-08-06)

## Contexto

Este proyecto corresponde al trabajo final de la Maestría en Inteligencia Artificial (FIUBA) *"Arquitectura de inteligencia artificial para detección temprana de estrés hídrico en cultivos hortícolas bajo escenarios de escasez y variabilidad de datos"*. La hipótesis de investigación sostiene que la combinación de generación de datos sintéticos, detección de anomalías, modelado predictivo y retroalimentación humana mejora la detección temprana de estrés hídrico frente a enfoques tradicionales, en contextos de disponibilidad limitada, ruido y alta variabilidad de datos.

El plan de proyecto (product backlog, HU1-HU8) exige que el sistema pueda evaluarse en configuraciones incrementales y comparables: arquitectura base, base + datos sintéticos, base + detección de anomalías, y arquitectura completa. Esto requiere que cada componente pueda activarse, desactivarse y evaluarse de forma independiente sin reescribir el resto del sistema.

No existe aún un despliegue productivo ni hardware IoT propio: el alcance es un prototipo experimental ejecutable en entorno local, reproducible, y opcionalmente validado con una prueba de concepto física de escala reducida.

## Decisión

Se adopta una arquitectura modular en capas desacopladas, alineada al diagrama conceptual del plan de tesis:

1. **Fuentes de datos** — sensores de campo, información satelital, datos climáticos (SMN, NASA POWER, Copernicus) y datasets públicos de humedad de suelo.
2. **Almacenamiento y preprocesamiento** — data store de series temporales y datos crudos; limpieza, normalización y control de calidad.
3. **Módulos de inteligencia artificial** — tres componentes independientes que consumen los datos preprocesados:
   - Generación de datos sintéticos (mitigación de cold start).
   - Detección de anomalías (ruido y fallas de medición).
   - Predicción temprana de estrés hídrico (modelado predictivo y generación de alertas).
4. **Salidas** — alertas de estrés en tiempo real, paneles de monitoreo, recomendaciones de riego.
5. **Retroalimentación humana** — validación/corrección de alertas por parte del usuario, que alimenta la recalibración supervisada de los modelos de la capa 3.

Estas capas se apoyan en una capa transversal de **gobernanza, seguridad y operación** (autenticación y accesos, calidad de datos, versionado y trazabilidad, monitoreo de desempeño y deriva, privacidad y cumplimiento normativo — Ley 25.326).

Cada módulo de la capa 3 se implementa como un componente con contrato de entrada/salida explícito (según HU6, "Definir contratos, entradas y salidas entre componentes"), de forma que las configuraciones experimentales de la Épica 4 (base, base+sintéticos, base+anomalías, completa) se logren activando o desactivando módulos sin modificar su interfaz.

## Alternativas consideradas

- **Monolito de modelado end-to-end**: un único pipeline que integre preprocesamiento, síntesis de datos y predicción sin separación de módulos. Se descarta porque impediría aislar el aporte individual de cada componente durante la evaluación experimental (HU7, HU8), requisito central para contrastar la hipótesis de investigación.
- **Arquitectura de microservicios desplegados**: separación de cada capa en servicios independientes con comunicación por red. Se descarta por sobredimensionar el alcance definido (no incluye despliegue productivo ni infraestructura de gran escala) y por introducir complejidad operativa innecesaria para un prototipo experimental local.

## Consecuencias

- La comparación de configuraciones experimentales (Épica 4) se resuelve activando/desactivando módulos de la capa 3, sin necesidad de variantes de código separadas.
- El mecanismo de retroalimentación humana (HU5) requiere un modelo de datos que vincule cada observación con la versión del modelo vigente al momento de la alerta, para mantener trazabilidad durante la recalibración.
- La separación modular facilita la documentación de decisiones, parámetros y limitaciones por componente (criterio de aceptación de HU3 y HU4), pero exige definir y mantener contratos de datos estables entre capas (HU6) a medida que evolucionan los experimentos.
- Los datos sintéticos permanecen identificados y separados de los datos reales en el almacenamiento (capa 2), conforme al criterio ético del plan de tesis de no asumir beneficio por definición de este componente.

## Referencias

- Plan de proyecto del Trabajo Final — Maestría en Inteligencia Artificial, Esp. Lic. Gustavo Julián Rivas, FIUBA (v4.1, 2026-08-01), secciones 1, 6, 8 y 12.
