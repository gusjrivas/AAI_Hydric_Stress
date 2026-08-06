# Contexto del proyecto

## Qué es

Prototipo experimental que implementa y evalúa la arquitectura de inteligencia artificial descrita en el trabajo final de la Maestría en Inteligencia Artificial (FIUBA): *"Arquitectura de inteligencia artificial para detección temprana de estrés hídrico en cultivos hortícolas bajo escenarios de escasez y variabilidad de datos"* (autor: Gustavo Julián Rivas; director: Camilo Enrique Argoty Pulido).

Ver [ADR-0001](../docs/adr/0001-arquitectura-modular-deteccion-estres-hidrico.md) para la decisión de arquitectura base.

## Propósito

Investigar y evaluar cómo la generación de datos sintéticos, la detección de anomalías, el modelado predictivo y la retroalimentación humana contribuyen a la detección temprana de estrés hídrico en escenarios de disponibilidad limitada, ruido y alta variabilidad de datos, frente a enfoques basados en observación empírica o reglas de riego estáticas.

## Alcance

**Incluye:** revisión del estado del arte, preparación de un conjunto experimental de datos públicos (humedad de suelo, variables climáticas y de riego), un componente de calidad/robustez de datos (limpieza, detección de anomalías, generación de datos sintéticos), un componente de modelado predictivo y generación de alertas tempranas, un mecanismo de retroalimentación humana con recalibración supervisada, integración de todos los componentes en un prototipo ejecutable local, y un plan experimental que compare configuraciones (base, base+sintéticos, base+anomalías, completa).

**No incluye:** implementación productiva o comercial, hardware IoT propio, despliegue en explotaciones agrícolas reales de gran escala, automatización física del riego, validación agronómica longitudinal multi-campaña, ni generalización estadística a toda la producción hortícola.

Una prueba de concepto física de escala reducida (sensores de humedad de suelo) es **opcional y complementaria**: solo valida el flujo de extremo a extremo, no reemplaza la evaluación experimental basada en datasets públicos.

## Trazabilidad con el plan de tesis

Cada *change* de OpenSpec debe indicar en su propuesta a qué Épica e Historia de Usuario (HU1-HU8) del product backlog corresponde, y qué fase de CRISP-DM cubre (comprensión del problema/datos, preparación de datos, modelado, evaluación, despliegue e integración experimental). Esto mantiene la trazabilidad entre la hipótesis de investigación, la arquitectura conceptual y la evidencia experimental exigida por el plan de proyecto.

Mapa orientativo HU → carpeta de capacidad esperada en `openspec/specs/`:

| HU | Capacidad | Épica |
|----|-----------|-------|
| HU1 | (documentación, sin capacidad de código) | 1. Fundamentación científica |
| HU2 | `data-ingestion` | 1. Fundamentación científica |
| HU3 | `data-quality` (detección de anomalías + datos sintéticos) | 2. Núcleo de IA |
| HU4 | `predictive-modeling` (ingeniería de variables + alertas) | 2. Núcleo de IA |
| HU5 | `human-feedback` | 3. Integración y mejora |
| HU6 | `architecture-integration` | 3. Integración y mejora |
| HU7 | `experiment-runner` | 4. Evaluación experimental |
| HU8 | (análisis de resultados, sin capacidad de código) | 4. Evaluación experimental |

## Convenciones para changes

- Un *change* por historia de usuario (o por tarea técnica significativa dentro de una HU), nunca mezclando componentes de capas distintas de la arquitectura de ADR-0001.
- `proposal.md` debe declarar explícitamente qué configuración experimental afecta (base / +sintéticos / +anomalías / completa), dado que la Épica 4 depende de poder aislar el aporte de cada componente.
- Los datos sintéticos se documentan y almacenan siempre separados e identificables respecto de los datos reales (criterio ético del plan de tesis, sección 12.2).
- Toda decisión sobre datasets externos, licencias o modelos preentrenados debe registrarse para sostener la trazabilidad y reproducibilidad exigidas en la gobernanza de datos (sección 12.1).

## Stack técnico

Aún no definido — se registrará en un ADR posterior (lenguaje/framework de modelado, formato de almacenamiento de series temporales, mecanismo de versionado de experimentos) antes de abrir el primer *change* de implementación.
