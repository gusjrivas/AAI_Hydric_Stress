# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Laboratorio con escena, sequía y alerta

El laboratorio de sensores DEBE presentar sus controles al inicio de la vista y ofrecer una demostración automática que ejecute los pasos pendientes con una pausa entre cada uno. DEBE mostrar una escena con la serie de humedad del suelo y los pronósticos emitidos, la serie de temperatura con el rango físico esperado, un subtítulo por paso e indicadores de calidad y de último pronóstico, derivados únicamente de lo que el backend devolvió. DEBE incluir un paso de sequía que genere días secos y calurosos sin lluvia y solicite un pronóstico real. La escena NO DEBE presentar una alerta que el backend no haya emitido, NO DEBE dibujar umbrales que el backend no informe y DEBE mantener visible el rótulo de datos sintéticos y de que no es evidencia científica.

#### Scenario: Ver la demostración completa con un clic

- **GIVEN** un laboratorio sin iniciar
- **WHEN** se elige «Ver la demostración»
- **THEN** se ejecutan los pasos A a E en orden, con una pausa entre cada uno, y la persona puede detenerla
- **AND** ante un error la demostración se detiene.

#### Scenario: Contraste entre ausencia y presencia de alerta

- **GIVEN** la semilla fija del laboratorio
- **WHEN** se completan los pasos A a E contra el backend real
- **THEN** los pronósticos de los pasos A, B y D no alertan y el del paso E alerta
- **AND** la escena muestra la probabilidad y el veredicto de cada pronóstico tal como los devolvió el backend.

#### Scenario: Sin alerta del backend

- **GIVEN** un pronóstico del paso E que el backend emitió sin alerta
- **WHEN** se muestra la escena
- **THEN** no se presenta ninguna alerta y el subtítulo indica que el pronóstico no emitió alerta.

#### Scenario: Pantallas angostas

- **GIVEN** un ancho de 360 px
- **WHEN** se abre el laboratorio
- **THEN** la página no desborda en horizontal, los gráficos se desplazan dentro de su caja y los controles tienen al menos 44 px.
