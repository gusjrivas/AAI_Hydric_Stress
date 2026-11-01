# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Menú de presentación de tres entradas

La navegación principal DEBE ofrecer tres entradas en este orden: Arquitectura, Caso de demostración y Resultados, y un menú «Más» que conserve el acceso a «Mi cultivo» y a «Herramientas técnicas». La aplicación DEBE abrir en Arquitectura cuando no se indica una ruta. «Caso de demostración» DEBE reunir Pergamino, Melchor Romero y el Laboratorio de sensores mediante un selector de caso que indique el caso vigente y muestre una línea que distinga los datos reales de los sintéticos. NO DEBE eliminarse ni renombrarse ninguna ruta ni ancla existente. El selector DEBE mostrarse solo en las vistas de esos tres casos.

#### Scenario: Abrir la aplicación sin ruta

- **GIVEN** una dirección sin ancla
- **WHEN** se abre la aplicación
- **THEN** se muestra Arquitectura con su entrada marcada como actual.

#### Scenario: Elegir un caso de demostración

- **GIVEN** la entrada «Caso de demostración»
- **WHEN** se elige Pergamino, Melchor Romero o Laboratorio de sensores
- **THEN** la entrada permanece marcada como actual, el selector indica el caso vigente y una línea describe si el caso usa datos reales o sintéticos
- **AND** el Laboratorio se rotula como sintético y no como evidencia científica.

#### Scenario: Acceder a los destinos conservados

- **GIVEN** cualquier vista
- **WHEN** se abre «Más»
- **THEN** se ofrecen «Mi cultivo» y «Herramientas técnicas», y los enlaces previos a `#productor`, `#resumen`, `#calidad`, `#linaje` y `#evidencia` mantienen su destino.

#### Scenario: Usar la navegación en pantallas angostas

- **GIVEN** un ancho de 360 px
- **WHEN** se abre la aplicación y se despliega «Más»
- **THEN** la barra inferior muestra cuatro entradas con objetivos táctiles de al menos 44 px, el panel de «Más» se abre sobre la barra y la página no desborda en horizontal.
