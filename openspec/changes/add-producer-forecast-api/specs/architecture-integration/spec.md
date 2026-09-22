## ADDED Requirements

### Requirement: Fachada operacional v2 aditiva
La API v2 MUST exponer el contrato api-contract.md delegando dominio a src.
MUST preservar endpoints legacy y aislamiento por sensor. GET MUST ser de solo lectura.

#### Scenario: Consulta sin modelo
- **WHEN** se consulta resumen de un sensor registrado sin modelo
- **THEN** se devuelve estado explícito sin entrenar ni emitir alerta negativa.

### Requirement: Tanda consistente de tres horizontes
Una tanda MUST anclarse al mismo snapshot y representar h=1,2,3 con disponibilidad
individual, fechas objetivo y procedencia explícitas.

#### Scenario: Resultado parcial
- **WHEN** h=2 falla y h=1 y h=3 están disponibles
- **THEN** se conservan los dos resultados y h=2 contiene null y motivo de ausencia.

#### Scenario: Datos del mismo día modificados
- **WHEN** se solicita reemplazar una tanda con datos distintos para la misma clave
- **THEN** se informa conflicto y se conserva la emisión original.

### Requirement: Pendientes y trazabilidad duraderos
Las consultas MUST recuperar pendientes antiguos sin depender de la ventana del
resumen y MUST distinguir feedback registrado de revisiones aplicadas a modelos.

#### Scenario: Pendiente fuera del historial reciente
- **WHEN** se lista feedback pendiente sin filtro de fechas
- **THEN** también se incluye una emisión anterior a los últimos treinta días.

#### Scenario: Revisión del último registro entre páginas
- **GIVEN** una página de pendientes y su cursor de continuación
- **WHEN** el registro que ancla ese cursor deja de estar pendiente por una revisión
- **THEN** la siguiente página continúa después de su clave ordenada sin repetir
  resultados previos; los contadores reflejan el estado actual del sensor.

#### Scenario: Cursor de otro sensor
- **WHEN** se usa un cursor de pronósticos de otro sensor
- **THEN** se rechaza con 422 invalid_cursor sin modificar datos.

#### Scenario: Ventana de fechas invertida
- **WHEN** target_from es posterior a target_to
- **THEN** se rechaza con 422 invalid_date_range en vez de simular un listado vacío.
### Requirement: Identidad durable y reserva operacional de sensores demo
El sistema MUST aplicar la identidad, persistencia transaccional e idempotencia
especificadas en docs/design/backend-producer-ui-emission-dependencies.md.
MUST reservar sensores demo- al flujo legacy sin depender del estado del worker.

#### Scenario: Mismo objetivo con distinto origen
- **WHEN** dos emisiones tienen igual target_date pero distinto as_of_date u horizonte
- **THEN** sus forecast_id y sus reviews son independientes.

#### Scenario: Misma clave con otro modelo
- **WHEN** cambia el modelo activo para una clave ya emitida
- **THEN** no se reemplaza la emision exitosa ni se genera otra identidad.

#### Scenario: Retry tras otra revision
- **WHEN** se repite un request_id exitoso con el mismo payload tras otra review
- **THEN** se devuelve su respuesta original antes de comprobar expected_revision.

#### Scenario: Demo terminada o manifiesto inaccesible
- **WHEN** se intenta emitir por v2 en un sensor demo- conocido
- **THEN** se devuelve 409 demo_write_locked con legacy_demo_sensor_reserved,
  independientemente del estado o acceso al manifiesto; GET sigue permitido.

#### Scenario: Sensor sintetico fuera de demo
- **WHEN** un sensor synthetic no pertenece al espacio demo-
- **THEN** la procedencia no activa la reserva; siguen aplicando otras validaciones.
