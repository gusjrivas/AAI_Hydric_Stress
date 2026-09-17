# Change: Mejorar la interfaz de apoyo a la decisión

## Estado

Propuesto, pendiente de implementación. Este change documenta el desarrollo futuro;
no declara implementados sus requisitos ni reemplaza la spec vigente.

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **HU principal:** HU6, tarea de integración de la interfaz; HU5 relacionada por la exposición del feedback humano.
- **Capacidad:** `alerting-ui`, capa 4 de la arquitectura.
- **CRISP-DM:** despliegue e integración experimental.
- **Configuraciones experimentales:** ninguna alteración de base, +sintéticos, +anomalías o completa.
- **HU7/HU8:** sin ejecución de experimentos ni modificación de métricas, resultados, protocolos o corridas históricas.
- **Hipótesis, propósito, alcance y arquitectura:** sin cambios. Se conserva React/TypeScript y el backend como fachada delgada.
- **Memoria técnica:** aporta al capítulo 3 (interacción, integración y trazabilidad); mantiene las garantías metodológicas del capítulo 2, sin afirmar mejoras predictivas por mejorar la interfaz.

## Why

La pantalla actual organiza el contenido como un recorrido de defensa: arquitectura,
calidad, predicción, linaje y evidencia. Consultar un pronóstico existente requiere
ejecutar primero uno nuevo; el control de sensor aparece dentro de una sección aunque
afecta al conjunto. El feedback carece de estado de guardado por fila y el contador
de correcciones pendientes cuenta todas las rechazadas, incluso si ya fueron aplicadas.

Se necesita una entrada centrada en el último pronóstico y su revisión, conservando
el recorrido científico y el detalle técnico como destinos accesibles.

## What Changes

1. Consultar historial mediante GET al seleccionar un sensor, con aislamiento de respuestas y estados vacíos/error explícitos.
2. Centralizar el sensor y las operaciones en una cabecera y estado compartidos; evitar escrituras superpuestas desde esta instancia de la UI.
3. Ofrecer Resumen, Alertas y revisión, Calidad de datos, Modelo y trazabilidad, Evidencia y arquitectura.
4. Presentar la señal predictiva con fecha de referencia, fecha objetivo y límites de interpretación.
5. Agregar corrección humana explícita, feedback de guardado y presentación honesta de las correcciones registradas/aplicadas.
6. Unificar estilos, responsive y accesibilidad, con pruebas funcionales y revisión visual.

## Impact

- Archivos previstos: `frontend/src/App.tsx`, estilos globales, features existentes, componentes/hooks compartidos acotados y tests relacionados.
- Documentación prevista: actualizar la referencia visual y consolidar los requisitos en la spec canónica cuando estén implementados; registrar la entrega en seguimiento.
- API: se consumen los endpoints actuales; este change no requiere cambios de backend ni de `src/`.
- No se incorpora un catálogo de sensores inexistente, series de mediciones nuevas, explicaciones causales del modelo, streaming, automatización del riego ni reentrenamiento automático.
- No se incorpora una librería de UI, router o gestor de estado por defecto. La implementación debe justificar cualquier dependencia adicional.
- Elegibilidad temporal y de procedencia: autoridad exclusiva del backend. La UI no promete un número de correcciones elegibles que la API actual no expone.
- La protección de concurrencia cubre esta instancia de la UI; no pretende resolver escrituras desde varias pestañas o clientes.

## Entregas y criterio de éxito

| Entrega | Resultado verificable |
|---|---|
| 1. Flujos confiables | Consultar y revisar historial sin ejecutar un pronóstico; cambios de sensor y errores no mezclan datos. |
| 2. Navegación y resumen | Último pronóstico y fechas como entrada; contexto del sensor visible en todos los destinos operativos. |
| 3. Revisión y trazabilidad | Corrección explícita, guardado verificable y estados de recalibración fieles a la API. |
| 4. Diseño y validación | Flujos utilizables con teclado y en móvil; evidencia de tests, build y revisión visual. |

La mejora de usabilidad se comprobará con las tareas de consulta, revisión y lectura
de linaje; no se asigna una reducción porcentual de tiempos sin medición previa.

## Fuentes y documentos de implementación

- [Spec vigente](../../specs/alerting-ui/spec.md).
- [ADR-0003](../../../docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md), [ADR-0006 y sus actualizaciones](../../../docs/adr/0006-recalibracion-disparada-desde-la-ui.md), [ADR-0008](../../../docs/adr/0008-ruteo-y-aislamiento-multi-sensor.md).
- [Diseño visual existente](../../../docs/design/alerting-ui-visual-design.md): su nota histórica sobre recalibración fuera de alcance está desactualizada; prevalecen la spec vigente y las actualizaciones del ADR-0006.
- [Diseño de esta propuesta](design.md), [requisitos y escenarios](specs/alerting-ui/spec.md), [tareas](tasks.md).

No se necesita un nuevo ADR: las decisiones son de presentación e interacción dentro
de la arquitectura vigente. Una ampliación de API o cambio metodológico requiere un
change separado y la lectura de sus fuentes normativas antes de implementarlo.
