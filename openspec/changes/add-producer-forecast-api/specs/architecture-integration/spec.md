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
