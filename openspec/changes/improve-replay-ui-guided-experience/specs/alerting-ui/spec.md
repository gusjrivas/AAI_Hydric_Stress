# Spec delta: alerting-ui (navegación)

## MODIFIED Requirements

### Requirement: Navegación centrada en la decisión y resumen fiel

La interfaz DEBE ofrecer Resumen, Alertas y revisión, Calidad de datos,
Modelo y trazabilidad, Explorar una predicción (reproducción histórica) y
Evidencia y arquitectura. El Resumen DEBE priorizar el último pronóstico
registrado, sus fechas y el acceso a revisión humana.

#### Scenario: Leer el resumen

- **GIVEN** un historial disponible
- **WHEN** se abre Resumen
- **THEN** se presenta la fila con mayor fecha de referencia, su alerta,
  probabilidad disponible y fecha objetivo
- **AND** se distingue esa fecha de la cobertura de datos y se conserva la
  aclaración de señal predictiva relativa, no diagnóstico ni probabilidad
  agronómicamente calibrada.

#### Scenario: Navegar sin perder contexto

- **GIVEN** un sensor activo y un resultado consultado o generado
- **WHEN** se cambia de destino o se usa Atrás/Adelante
- **THEN** se conserva el contexto compartido, se identifica el destino
  activo y se enfoca su encabezado, sin iniciar POST
- **AND** los enlaces previos a calidad, predicción, linaje, reproducción
  histórica y evidencia siguen resolviendo al destino correspondiente.

#### Scenario: Explorar una predicción es un destino de primera clase

- **GIVEN** la navegación principal
- **WHEN** se activa "Explorar una predicción"
- **THEN** se marca como destino activo (`aria-current="page"`), se enfoca
  su encabezado y no queda un enlace duplicado fuera de la navegación
  principal

Ampliado en `improve-replay-ui-guided-experience`: "Explorar una
predicción" (reproducción histórica, antes un enlace aparte sin estado
activo) se integra como sexto destino de `useHashRoute`/`DestinationNav`,
sin alterar los cinco destinos ni los anchors previos. Ver
`frontend/src/App.tsx`, `frontend/src/features/navigation/useHashRoute.ts`
y `frontend/src/App.test.tsx`.
