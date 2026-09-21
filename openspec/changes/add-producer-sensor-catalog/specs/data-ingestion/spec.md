## ADDED Requirements

### Requirement: Catálogo descriptivo aislado de las mediciones
El sistema MUST registrar sectores y puntos con identidad estable y metadatos
versionados sin crear lecturas ni activar entrenamiento. La serie de pronóstico
de un sector MUST seleccionarse explícitamente; no se fusionan puntos.

#### Scenario: Alta de un punto nuevo
- **GIVEN** un sector existente y un identificador válido sin lecturas
- **WHEN** se registra el punto
- **THEN** queda sin lecturas y sin predicción, conservando datasets previos.

#### Scenario: Dos altas concurrentes con la misma identidad
- **WHEN** dos procesos registran el mismo identificador
- **THEN** solo uno crea el recurso y el otro obtiene conflicto, sin corrupción.

#### Scenario: Adopción de una serie existente
- **GIVEN** una serie sensor__ no catalogada
- **WHEN** se registran sus metadatos
- **THEN** se conserva el archivo y origen de sus filas sin reclasificarlas.

### Requirement: Lecturas completas y consistentes por snapshot
El sistema MUST exponer valores, unidades, fechas, origen y faltantes desde un
único snapshot de la serie. MUST NOT imputar ni usar otra serie como reemplazo.

#### Scenario: Cambiar ventana sin cambiar el extremo
- **WHEN** se consultan 7 y 30 días del mismo snapshot y fecha final
- **THEN** los registros compartidos y la última medición son idénticos.

#### Scenario: Falta una lectura
- **GIVEN** un día omitido o un valor nulo
- **WHEN** se consulta el historial
- **THEN** el faltante queda explícito y no se convierte en cero.

#### Scenario: Falla el almacenamiento
- **WHEN** falla la lectura de un recurso conocido
- **THEN** se informa error y no un historial vacío.
