# Interfaz comprensible para productores y agrónomos

## Motivo y autorización

El usuario solicita una UI sencilla para productores sin formación agronómica y
agrónomos sin formación tecnológica. La navegación de defensa y el lenguaje de
arquitectura de la entrega anterior no son adecuados como presentación principal.

## Trazabilidad

- HU6 principal, HU5 relacionada; capacidad `alerting-ui`, capa de presentación.
- CRISP-DM: despliegue e integración experimental.
- Sin cambios en hipótesis, alcance científico, arquitectura ni contratos API.
- Sin impacto en configuraciones base/+sintéticos/+anomalías/completa, HU7/HU8,
  protocolos, resultados históricos o mecanismo temporal de validación.
- Capítulo 3: adecuación de la interfaz al usuario destinatario. No constituye
  evidencia de mejora predictiva ni validación de usabilidad con productores.

## Cambio implementado

Navegación en lenguaje cotidiano, resultado principal explicado en palabras,
fechas diferenciadas, guía para revisar observaciones y explicación del efecto de
aplicarlas a futuros pronósticos. Valores numéricos y detalles técnicos se consultan
mediante desplegables. La evidencia del estudio permanece accesible y sin cambios.
Los filtros muestran la cantidad de coincidencias sobre el historial guardado.

Se conservan los hashes anteriores y las operaciones existentes. No se agregan
resultados de días no registrados ni indicaciones de riego. Los datos y el override
Docker no versionados del usuario permanecen intactos.

## Referencias

- [Spec vigente](../../specs/alerting-ui/spec.md).
- [Diseño anterior](../improve-alerting-ui-decision-workflow/design.md).
- [ADR-0003](../../../docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md).
- [ADR-0006](../../../docs/adr/0006-recalibracion-disparada-desde-la-ui.md).

## Validación

Pruebas frontend, lint y build; evidencia final en `tasks.md`. La inspección visual
en navegador y la evaluación con usuarios reales se informan por separado. Este
change sustituye las etiquetas de navegación de la entrega anterior, sin eliminar
sus capacidades ni su trazabilidad técnica.
