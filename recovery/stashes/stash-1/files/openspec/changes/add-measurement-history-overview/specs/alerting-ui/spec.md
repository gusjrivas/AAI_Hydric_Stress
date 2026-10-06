## ADDED Requirements

### Requirement: Historial de mediciones comprensible en el inicio

La interfaz MUST separar mediciones guardadas de estimaciones, mostrar fechas,
unidades y procedencia, y permitir consultar 7, 30 o 90 días calendario terminados
en la última medición disponible. El gráfico MUST tener una tabla accesible de
valores y MUST NOT unir huecos ni representar faltantes como cero.

#### Scenario: Datos de demostración con huecos
- GIVEN un punto con datos sintéticos y días sin humedad registrada
- WHEN se consulta el resumen
- THEN se identifica la simulación, se muestran fechas y unidades y se conservan
  los huecos sin imputar valores.

#### Scenario: Cambio de punto mientras hay una consulta pendiente
- WHEN el usuario cambia de punto
- THEN una respuesta del punto anterior MUST NOT reemplazar el historial actual.

### Requirement: Horizonte y antigüedad explícitos

El resumen MUST mostrar la fecha objetivo y su distancia respecto de la fecha de
datos del resultado registrado. MUST identificar objetivos pasados y explicar que
el contrato operativo estima t+3, sin presentar días intermedios o t+7 inventados.

#### Scenario: Resultado sobre un período pasado
- GIVEN un resultado con fecha objetivo anterior al día UTC actual
- WHEN se muestra el resumen
- THEN se aclara que no es un pronóstico para hoy.

### Requirement: Consulta histórica sin efectos sobre datos o modelos

La fachada MUST ofrecer GET `/sensors/{sensor_id}/history`, con `days` entero de
1 a 366 (predeterminado 30), devolver valores almacenados ordenados por fecha y
conservar nulos. MUST preservar aislamiento y no escribir, imputar o entrenar.

#### Scenario: Dataset inexistente o período inválido
- WHEN no existe el dataset solicitado o el período es inválido
- THEN la API responde 404 o 422 respectivamente, sin usar otro sensor como reemplazo.
