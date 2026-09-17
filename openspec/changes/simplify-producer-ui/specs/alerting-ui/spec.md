## ADDED Requirements

### Requirement: Lenguaje cotidiano y detalle técnico secundario

La UI DEBE permitir consultar pronósticos y registrar observaciones sin requerir
comprensión de modelos, backend, features, linaje o recalibración. DEBE explicar
las acciones por sus efectos y mantener disponible el detalle técnico secundario.

#### Scenario: Consultar el resultado

- **GIVEN** un pronóstico registrado
- **WHEN** se abre Resumen
- **THEN** el resultado se explica en palabras, con datos usados hasta y día pronosticado diferenciados
- **AND** el valor numérico se consulta por un desplegable y no se presenta como certeza agronómica.

#### Scenario: Consultar filtros y ajustes

- **GIVEN** un historial cargado
- **WHEN** se aplican filtros o se consulta el ajuste de próximos pronósticos
- **THEN** los filtros muestran coincidencias sobre el total guardado; no generan días nuevos
- **AND** aplicar observaciones explica su efecto en la próxima ejecución, conserva resultados previos y mantiene identificadores técnicos fuera del mensaje principal.

#### Scenario: Acceder al estudio y a la trazabilidad

- **GIVEN** un usuario que necesita información adicional
- **WHEN** abre los desplegables del estudio o de los ajustes
- **THEN** puede acceder a las fuentes, metadata y linaje existentes sin alterar sus valores ni crear escrituras por navegar.
