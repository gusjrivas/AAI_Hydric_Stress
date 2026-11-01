# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Diagrama de despliegue y recorrido ilustrativo

La vista de arquitectura DEBE incluir un diagrama de despliegue con los componentes técnicos de la aplicación y sus conexiones, una ficha por componente con responsabilidad, conexiones, evidencia y límites, y una alternativa textual en tabla. DEBE ofrecer un recorrido ilustrativo que resalte, paso a paso, los componentes y conexiones involucrados en el flujo de un dato desde la fuente hasta el registro de una recalibración. El recorrido es un guion fijo y DEBE rotularse como ilustrativo. NO DEBE consultar servicios, ni mostrar datos, métricas, estados de salud o tiempos, ni presentar ningún componente como activo en la infraestructura real. Este requisito extiende, sin reemplazar, el requisito «Mapa de arquitectura veraz y accesible».

#### Scenario: Consultar un componente del despliegue

- **GIVEN** la vista Arquitectura
- **WHEN** se selecciona un componente del diagrama
- **THEN** se muestra su ficha con rutas de evidencia existentes en el repositorio y sus límites
- **AND** los puertos declarados coinciden con `docker-compose.yml`.

#### Scenario: Reproducir el recorrido ilustrativo

- **GIVEN** la vista Arquitectura
- **WHEN** se inicia el recorrido
- **THEN** cada paso resalta los componentes y conexiones involucrados y muestra un subtítulo, con controles de pausa, anterior, siguiente y salida
- **AND** el rótulo «Recorrido ilustrativo · sin datos ni métricas reales» permanece visible
- **AND** MLflow solo se resalta en los pasos de recalibración posteriores a la retroalimentación humana.

#### Scenario: Preferencia de movimiento reducido

- **GIVEN** un sistema con `prefers-reduced-motion: reduce`
- **WHEN** se inicia el recorrido
- **THEN** no hay avance automático ni animación, y los pasos se recorren con los controles siguiente y anterior.
