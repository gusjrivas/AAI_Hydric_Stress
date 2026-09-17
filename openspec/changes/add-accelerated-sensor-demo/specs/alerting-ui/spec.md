## ADDED Requirements

### Requirement: Control explícito de demostración opcional

La UI DEBE mostrar controles cotidianos de inicio, pausa y continuación cuando el
controlador local esté configurado, manteniendo el uso normal si no lo está.

#### Scenario: Abrir la demostración

- **GIVEN** una sesión preparada accesible
- **WHEN** se abre la vista de demostración
- **THEN** se muestra sensor, día simulado, progreso y estado bajo el rótulo permanente «Demostración con datos simulados»
- **AND** navegar solo consulta; iniciar requiere una acción explícita.

#### Scenario: Controlador ausente o inaccesible

- **GIVEN** controlador no configurado o consulta fallida
- **WHEN** se usa la aplicación
- **THEN** las vistas operativas siguen disponibles y no se crea una sesión automáticamente
- **AND** si hay pérdida de conexión se advierte que la demo podría seguir activa, sin afirmar que está pausada.

### Requirement: Refresco por progreso confirmado

La UI DEBE consultar el estado sin solicitudes superpuestas y actualizar historial
y calidad cuando avance una revisión confirmada, sin ejecutar POST por refrescar.

#### Scenario: Ver un nuevo día

- **GIVEN** una demostración en ejecución
- **WHEN** el controlador confirma una nueva ingesta y su pronóstico
- **THEN** la UI actualiza datos e historial del sensor correcto, conserva filtros y presenta la cantidad real de resultados guardados
- **AND** no agrega registros optimistas ni confunde el día simulado con hoy.

#### Scenario: Cambiar de sensor o volver a la pestaña

- **GIVEN** una sesión que continúa en el controlador
- **WHEN** el usuario consulta otro sensor o vuelve a la pestaña
- **THEN** las respuestas obsoletas no contaminan el contexto; volver a la demo consulta su estado real sin iniciar otro worker.

### Requirement: Revisión humana posterior a la reproducción

La UI DEBE impedir mutaciones manuales del sensor demo hasta completar la sesión.
Luego DEBE conservar la validación temporal del backend y distinguir objetivos sin datos.

#### Scenario: Intentar escribir durante la reproducción

- **GIVEN** sesión preparada, en ejecución, pausándose, pausada o bloqueada
- **WHEN** se consulta el sensor demo
- **THEN** generar pronóstico, confirmar/corregir y aplicar observaciones manualmente están deshabilitados con explicación; los controles de demo y las consultas siguen disponibles.

#### Scenario: Revisar un resultado al terminar

- **GIVEN** sesión completada y una fecha objetivo ya terminada en UTC y presente en los datos ingeridos
- **WHEN** la persona registra su observación
- **THEN** se usa el endpoint existente y se respetan sus rechazos de procedencia/maduración
- **AND** filas sin objetivo observable no se ofrecen como revisables; no se crean observaciones humanas automáticas ni se reanuda una sesión completada después de ajustar el predictor.
