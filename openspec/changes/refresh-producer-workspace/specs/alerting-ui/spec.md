## ADDED Requirements

### Requirement: Espacio del productor comprensible
La UI MUST priorizar sector, fechas de pronóstico, mediciones y opiniones usando
lenguaje cotidiano. MUST conservar procedencia, antigüedad y ausencia explícitas,
sin transformar score en porcentaje ni interpretar indisponibilidad como sin alerta.

#### Scenario: Consulta sin estimación
- **WHEN** un horizonte no dispone de estimación
- **THEN** se muestra la fecha o posición del día, un motivo y que no implica ausencia de riesgo.

#### Scenario: Pendientes futuros y antecedentes
- **WHEN** se muestran las opiniones pendientes
- **THEN** las revisables aparecen primero y las futuras se consultan en un desplegable;
  el historial permanece disponible sin ocupar el primer nivel visual.

### Requirement: Opiniones consistentes entre secciones
La UI MUST propagar una revisión confirmada por el servidor a todas las tarjetas
de la misma emisión, conservar revisiones nuevas frente a respuestas anteriores
y MUST NOT anunciar una actualización si la recuperación tras conflicto falla.

#### Scenario: Opinión guardada en pendientes
- **WHEN** se guarda una opinión
- **THEN** el pendiente se retira y la tarjeta del historial refleja la revisión guardada.

### Requirement: Recuperación de paginación operacional
La UI MUST reconocer invalid_cursor del backend y ofrecer reiniciar la lista.
Un fallo de carga MUST conservar los resultados visibles y ofrecer reintentar.

#### Scenario: Cursor anterior al despliegue
- **WHEN** backend devuelve 422 invalid_cursor
- **THEN** se ofrece volver a cargar desde la primera página, sin reutilizar ese cursor.

### Requirement: Presentación adaptable y accesible
La UI MUST mantener etiquetas y mensajes además de color, foco visible y controles
operables por teclado; MUST adaptar las tarjetas a una columna en pantallas pequeñas.

#### Scenario: Pantalla de 390 píxeles
- **WHEN** se abre Mi cultivo en un viewport de 390 píxeles
- **THEN** la página no requiere desplazamiento horizontal y los selectores siguen utilizables.