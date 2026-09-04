# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Ingesta de lecturas de sensores desde la interfaz de datos, aislada por sensor

El sistema DEBE poder recibir una lectura individual (timestamp y valores, parcial permitido) para un `sensor_id` dado, y agregarla al dataset propio de ese sensor, sin distinguir si el origen es un sensor real o un generador sintético. El timestamp se normaliza a granularidad diaria (medianoche, sin timezone); una segunda lectura del mismo día reemplaza a la anterior en vez de duplicarla. `sensor_id` DEBE validarse contra `^[a-zA-Z0-9_-]{1,64}$`; un `sensor_id` inválido DEBE rechazarse sin persistir nada.

#### Scenario: Ingesta de una lectura válida para un sensor

- **GIVEN** el dataset propio de `sensor_id`, con o sin historia previa
- **WHEN** se envía una lectura con timestamp y al menos un valor de columna obligatoria a `POST /sensors/{sensor_id}/readings`
- **THEN** la lectura queda persistida como una fila nueva del dataset de ese sensor, con procedencia según lo indicado en la lectura

#### Scenario: Lecturas de sensores distintos no comparten dataset

- **GIVEN** dos sensores `A` y `B` sin historia previa
- **WHEN** se ingiere una lectura para `A` y otra distinta para `B`
- **THEN** el dataset de `A` contiene únicamente la lectura de `A`, y el de `B` únicamente la de `B`

#### Scenario: Un `sensor_id` inválido se rechaza

- **GIVEN** un `sensor_id` que no cumple `^[a-zA-Z0-9_-]{1,64}$` (por ejemplo, con `/` o `..`)
- **WHEN** se intenta ingerir una lectura para ese `sensor_id`
- **THEN** la solicitud se rechaza sin persistir ninguna lectura

#### Scenario: El dataset en vivo de un sensor es independiente del dataset histórico de investigación

- **GIVEN** el dataset histórico `melchor_romero_2024_consolidado` ya usado para verificar HU7/HU8
- **WHEN** se ingieren lecturas para cualquier `sensor_id` válido
- **THEN** el dataset histórico permanece sin modificaciones, porque el nombre de todo dataset de sensor lleva el prefijo `sensor__` y nunca puede coincidir con el nombre del histórico

### Requirement: Aislamiento de estado entre sensores

El sistema DEBE mantener el caché de selección de modelo, el modelo recalibrado registrado y el registro de retroalimentación como recursos independientes por `sensor_id` — ninguna operación sobre un sensor DEBE afectar el estado cacheado, registrado o persistido de otro.

#### Scenario: El caché de selección de modelo no se comparte entre sensores

- **GIVEN** un modelo ya auto-seleccionado y cacheado para el sensor `A`
- **WHEN** se ejecuta un pronóstico por primera vez para el sensor `B`
- **THEN** se selecciona un modelo para `B` de forma independiente, sin usar ni invalidar el modelo cacheado de `A`

#### Scenario: Recalibrar un sensor no afecta el modelo de otro

- **GIVEN** modelos recalibrados registrados de forma independiente para los sensores `A` y `B`
- **WHEN** se ejecuta un pronóstico para `A`
- **THEN** se usa el modelo recalibrado de `A`, nunca el de `B`

## MODIFIED Requirements

### Requirement: Ejecución de pronóstico desde la interfaz, por sensor

El sistema DEBE poder ejecutar el pipeline completo (calidad, modelado, alertas) sobre el dataset de un `sensor_id` dado, y devolver un veredicto por fecha (alerta sí/no, probabilidad) sin exponer qué modelo lo generó.

#### Scenario: Correr un pronóstico para un sensor produce alertas y persiste su feedback inicial

- **GIVEN** un dataset disponible para `sensor_id`
- **WHEN** se invoca `POST /forecast/{sensor_id}/run`
- **THEN** se devuelve una lista de veredictos por fecha (fecha, alerta, probabilidad), y el registro de retroalimentación propio de ese sensor queda persistido con esas fechas en estado `pendiente` (o conservando su estado previo si ya existían)

### Requirement: Consulta y validación humana de alertas, por sensor

El sistema DEBE poder listar el registro de retroalimentación de un `sensor_id` dado, y permitir confirmar o rechazar una alerta puntual de ese sensor identificada por fecha.

#### Scenario: Confirmar una alerta de un sensor vía la API

- **GIVEN** un registro de retroalimentación de `sensor_id` con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca `POST /feedback/{sensor_id}/{fecha}/confirm`
- **THEN** el registro persistido de ese sensor queda con esa fecha en estado `confirmada`

#### Scenario: Rechazar una alerta de un sensor con corrección vía la API

- **GIVEN** un registro de retroalimentación de `sensor_id` con una alerta en estado `pendiente` para una fecha dada
- **WHEN** se invoca `POST /feedback/{sensor_id}/{fecha}/reject`, con una etiqueta corregida y una observación
- **THEN** el registro persistido de ese sensor queda con esa fecha en estado `rechazada`, con la corrección y la observación guardadas

### Requirement: Disparo manual de recalibración desde la interfaz, por sensor

El sistema DEBE poder recalibrar el modelo de un `sensor_id` dado a partir de las alertas rechazadas con corrección presentes en su registro de retroalimentación, y registrar el resultado de forma versionada bajo un nombre de modelo propio de ese sensor.

#### Scenario: Recalibrar un sensor con correcciones pendientes

- **GIVEN** un registro de retroalimentación de `sensor_id` con al menos una alerta en estado `rechazada` con `etiqueta_corregida` no nula
- **WHEN** se invoca `POST /recalibrate/{sensor_id}`
- **THEN** se reentrena el modelo de ese sensor incorporando esas correcciones, el resultado queda registrado con una nueva versión bajo el nombre de modelo propio de `sensor_id`, y la respuesta indica la versión registrada y cuántas correcciones se aplicaron

#### Scenario: Recalibrar un sensor sin correcciones pendientes

- **GIVEN** un registro de retroalimentación de `sensor_id` sin ninguna alerta `rechazada` con `etiqueta_corregida` no nula
- **WHEN** se invoca `POST /recalibrate/{sensor_id}`
- **THEN** se devuelve un error explícito indicando que no hay correcciones pendientes de aplicar, sin registrar ninguna versión nueva

### Requirement: Uso del modelo recalibrado en el próximo pronóstico, por sensor

El sistema DEBE usar la versión más reciente del modelo recalibrado de un `sensor_id` dado (si existe alguna) al ejecutar un nuevo pronóstico para ese sensor, en vez de entrenar un modelo nuevo desde cero.

#### Scenario: Pronóstico de un sensor posterior a su recalibración

- **GIVEN** un modelo recalibrado ya registrado para `sensor_id`
- **WHEN** se ejecuta el pronóstico de ese sensor
- **THEN** las predicciones se generan con el modelo registrado de ese sensor, sin reentrenar uno nuevo

#### Scenario: Pronóstico de un sensor sin ninguna recalibración previa

- **GIVEN** que todavía no se registró ningún modelo recalibrado para `sensor_id`
- **WHEN** se ejecuta el pronóstico de ese sensor
- **THEN** se entrena un modelo nuevo para ese sensor, igual que el comportamiento previo a este *change*

### Requirement: Reutilización del modelo auto-seleccionado mientras el dataset de un sensor no cambie

El sistema DEBE reutilizar, sin volver a seleccionar, el último modelo auto-seleccionado para un `sensor_id` dado mientras el dataset de ese sensor no haya cambiado; DEBE volver a seleccionar cuando ese dataset cambie o cuando todavía no exista un modelo cacheado para ese sensor. Este comportamiento solo aplica cuando no hay un modelo recalibrado registrado para ese sensor — la prioridad de un modelo recalibrado sobre la selección automática no cambia, y es independiente por sensor.

#### Scenario: El dataset de un sensor no cambió entre dos corridas

- **GIVEN** un modelo ya auto-seleccionado para `sensor_id` en una corrida anterior, sin modelo recalibrado registrado para ese sensor, y su dataset sin cambios
- **WHEN** se ejecuta una nueva corrida para ese sensor
- **THEN** se reutiliza el mismo modelo cacheado de ese sensor sin volver a seleccionar

#### Scenario: El dataset de un sensor cambió entre dos corridas

- **GIVEN** un modelo ya auto-seleccionado para `sensor_id` en una corrida anterior, sin modelo recalibrado registrado para ese sensor, y su dataset modificado desde esa corrida
- **WHEN** se ejecuta una nueva corrida para ese sensor
- **THEN** se vuelve a seleccionar el mejor candidato para ese sensor, y el resultado reemplaza su modelo cacheado

#### Scenario: Un modelo recalibrado de un sensor sigue teniendo prioridad sobre su caché

- **GIVEN** un modelo recalibrado registrado en MLflow para `sensor_id` y, además, un modelo auto-seleccionado ya cacheado para ese mismo sensor
- **WHEN** se ejecuta una nueva corrida para ese sensor
- **THEN** se usa el modelo recalibrado de ese sensor, ignorando su caché de selección automática
