## ADDED Requirements

### Requirement: Revisión operacional desde la fecha objetivo
Las emisiones v2 MUST admitir revisión desde las 00:00 UTC del día objetivo,
sin vencimiento posterior y con identidad por emisión. MUST preservar el bloqueo
de escritura v2 para sensores reservados demo- en cualquier estado y no aceptar relojes del cliente.

#### Scenario: Revisión tardía
- **GIVEN** una alerta pendiente de hace tres semanas y un nuevo modelo activo
- **WHEN** el usuario confirma la alerta
- **THEN** se registra su opinión contra la emisión original.

#### Scenario: Intento antes de la fecha
- **WHEN** se revisa antes de review_open_at
- **THEN** no se persiste revisión y se informa review_not_open.

### Requirement: Historial de opiniones consistente
La API MUST conservar revisiones anteriores, aplicar control de concurrencia
e idempotencia y distinguir confirmar de corregir la alerta original.

#### Scenario: Reintento tras pérdida de respuesta
- **WHEN** se reenvía request_id con el mismo cuerpo
- **THEN** se devuelve el resultado original sin duplicar la revisión.

#### Scenario: Dos ediciones concurrentes
- **WHEN** la segunda usa una revisión esperada ya superada
- **THEN** se rechaza con conflicto sin perder la primera.

### Requirement: Captura y elegibilidad independientes
Guardar feedback MUST NOT volverlo automáticamente apto para entrenamiento.
MUST preservarse la madurez posterior al día objetivo, compatibilidad del
bundle y linaje exacto, sin modificar reglas experimentales ni registros legacy.

#### Scenario: Confirmación el día anunciado
- **WHEN** se guarda feedback durante el día objetivo
- **THEN** queda registrado y no pendiente para usuario, pero no elegible para entrenamiento.

#### Scenario: Opinión temprana al finalizar el día
- **WHEN** comienza el día siguiente sin otra acción humana
- **THEN** la opinión mantiene su fecha y requiere revalidación madura para selección.

#### Scenario: Corrección ya aplicada y luego editada
- **WHEN** se consulta el linaje tras editar una opinión
- **THEN** se identifica la revisión aplicada, sin atribuir al modelo la nueva edición.
