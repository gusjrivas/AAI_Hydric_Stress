# Change: Demostración dinámica con un sensor simulado

## Estado

Propuesto, pendiente de aprobación e implementación. No activa simuladores, no crea
datasets ni modifica las capacidades vigentes. Las tareas permanecen pendientes.

## Trazabilidad

- **HU principal:** HU6, tarea de demostración de la integración; HU2/HU5 relacionadas como capacidades consumidas.
- **Épica:** 3. Integración y mejora.
- **Capacidades:** nueva `demo-simulation` (herramienta local de demostración) y extensión de presentación `alerting-ui`.
- **Capa:** cliente de demostración y presentación; no se modifican las capas internas de datos o IA.
- **CRISP-DM:** despliegue e integración experimental.
- **Configuraciones base/+sintéticos/+anomalías/completa:** sin cambios.
- **HU7/HU8:** ninguna ejecución experimental ni modificación de métricas, protocolos, baselines o resultados históricos.
- **Hipótesis, propósito y alcance científico:** sin cambios. No se incorpora un simulador agronómico validado ni automatización del riego.
- **Memoria:** capítulo 3, demostración de integración; capítulo 2, preservación del orden temporal. La demo no mide capacidad predictiva ni latencia de sensores reales.

## Why

Los scripts actuales envían lecturas con la fecha actual. El endpoint las normaliza
a día UTC y reemplaza la fila del mismo día; repetir solicitudes no agrega días.
Además, la ingesta no dispara pronósticos y la UI no actualiza automáticamente el
historial. Por eso aumentar los envíos no produce un recorrido visible de varios días.

Se propone reproducir un período pasado sintético, un día por paso, usando los
endpoints reales y mostrando cómo crecen los datos y los pronósticos registrados.

## What Changes

1. Preparación por CLI de una sesión nueva, con historia sintética inicial, sensor exclusivo y manifiesto persistido.
2. Controlador local opcional: enviar día → verificar ingesta → ejecutar pronóstico → verificar registro → avanzar.
3. Inicio, pausa al completar el paso, continuación y recuperación conservadora tras fallos.
4. UI con estado, día simulado, progreso y consultas periódicas; lenguaje cotidiano y señalización permanente de simulación.
5. Tests de causalidad, aislamiento, recuperación, no duplicación de registros y operaciones concurrentes.

**Decisión de arquitectura a revisar:** se propone un proceso local auxiliar de
control, separado del backend, para que la UI pueda iniciar/pausar una ejecución que
continúe aunque se cierre la pestaña. Es una extensión del entorno de demostración,
no una división de las capas de IA en microservicios. Se explicita en el
[ADR propuesto](../../../docs/adr/0012-controlador-local-demo-acelerada.md); no debe
tratarse como una decisión ya aceptada.

## Alcance y límites

- Un sensor por sesión; varias sesiones solo de forma secuencial en esta entrega.
- Días consecutivos del pasado, nunca timestamps subdiarios disfrazados de días.
- Semilla y parámetros congelados; generador mock existente reutilizado, incluida ET0 en el payload.
- Historia inicial suficiente verificada contra el pipeline real con fixtures. El número de días por sí solo no garantiza entrenabilidad ni ambas clases.
- Inicialización explícita por CLI; no se agrega un endpoint genérico para sembrar/sobrescribir datasets (ADR-0007).
- El controlador no importa funciones de entrenamiento ni escribe feedback: consume la API real.
- No se modifica el módulo de aumento sintético HU3 ni se lo confunde con el mock de lecturas.
- No se fuerza alternancia alerta/sin alerta, no se buscan semillas por resultados favorables y no se cambian umbrales para la demo.
- Generación de secuencias meteorológicas más realistas queda para otro change; se documentan las limitaciones del random walk actual.
- No incluye reinicio destructivo, catálogo de sensores, streaming subdiario, autenticación productiva ni comandos de riego.
- La revisión humana se habilita en la UI al completar la sesión y solo para objetivos observables, manteniendo la validación del backend. No se simulan decisiones humanas automáticamente.

## Entregas

| Entrega | Resultado |
|---|---|
| 1. Preparación y ejecución CLI | Sesión aislada, secuencia causal y manifiesto persistido; pruebas con API real en entorno temporal. |
| 2. Control local y recuperación | Servicio opcional con inicio/pausa/continuación y recuperación conservadora. |
| 3. UI de demostración | Controles y refresco de lecturas/pronósticos, separados del uso normal. |
| 4. Verificación integrada | Recorrido de al menos cinco días y revisión humana explícita de un resultado observable. |

Cada entrega requiere las anteriores verificadas. La implementación se divide en PRs
pequeños; no se declara completo el change por finalizar solo el simulador CLI.

## Fuente de verdad

- [Proyecto](../../project.md), [data-ingestion](../../specs/data-ingestion/spec.md), [alerting-ui](../../specs/alerting-ui/spec.md).
- [ADR-0003](../../../docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md), [ADR-0007](../../../docs/adr/0007-ingesta-de-sensores-en-vivo-mock.md), [ADR-0008](../../../docs/adr/0008-ruteo-y-aislamiento-multi-sensor.md).
- [ADR-0006, actualizaciones temporales](../../../docs/adr/0006-recalibracion-disparada-desde-la-ui.md) y [protocolo v3](../../../docs/research/protocolo-experimental-v3.md).
- [Diseño](design.md), [tareas](tasks.md), [simulador](specs/demo-simulation/spec.md), [UI](specs/alerting-ui/spec.md).
