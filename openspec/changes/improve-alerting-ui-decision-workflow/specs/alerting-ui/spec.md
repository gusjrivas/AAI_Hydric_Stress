# Spec delta: alerting-ui

Requisitos propuestos de presentación e interacción. Complementan la capacidad
vigente; no modifican contratos del núcleo ni garantías temporales del backend.

## ADDED Requirements

### Requirement: Contexto global de sensor y aislamiento de solicitudes

La interfaz DEBE separar el sensor en edición del sensor activo, aplicar el cambio
solo mediante confirmación explícita y validar `^[a-zA-Z0-9_-]{1,64}$`. DEBE evitar
que datos o respuestas de un sensor se presenten como pertenecientes a otro.

#### Scenario: Editar y aplicar un sensor

- **GIVEN** un sensor activo con datos visibles
- **WHEN** se edita el identificador sin aplicar
- **THEN** el contexto y las consultas permanecen en el sensor activo
- **AND** al aplicar un identificador válido se limpia el contexto anterior y se consultan recursos del nuevo sensor; un valor inválido muestra un error asociado y no dispara consultas.

#### Scenario: Respuesta tardía del sensor anterior

- **GIVEN** una consulta pendiente del sensor A y un cambio aplicado al sensor B
- **WHEN** llega la respuesta de A después del cambio
- **THEN** no modifica datos, errores, contadores ni estados de carga de B.

### Requirement: Consulta de historial independiente de la ejecución

La interfaz DEBE consultar el historial persistido al activar un sensor sin ejecutar
pronóstico ni recalibración. DEBE preservar filas aunque falten probabilidad u objetivo.

#### Scenario: Consultar registros existentes

- **GIVEN** registros persistidos de un sensor
- **WHEN** se abre la aplicación o se aplica ese sensor
- **THEN** se muestran mediante GET, ordenados por fecha de referencia descendente, sin POST
- **AND** los valores ausentes se identifican como no disponibles, sin convertirse en cero o «Sin alerta».

#### Scenario: Registro ausente o consulta fallida

- **GIVEN** una consulta de historial
- **WHEN** retorna 404 por ausencia de registro
- **THEN** se muestra «Todavía no hay pronósticos registrados» y la acción explícita de generar uno
- **AND** cualquier otro error se muestra con reintento de lectura, sin presentarse como historial vacío ni contador cero.

#### Scenario: Filtrar el historial

- **GIVEN** un historial cargado
- **WHEN** se filtra por alerta, estado de validación o rango inclusivo de fecha de referencia
- **THEN** se muestran las coincidencias sin nuevas escrituras y se permite limpiar los filtros
- **AND** un resultado sin coincidencias se distingue de un historial vacío; los contadores generales conservan el total sin filtrar.

### Requirement: Navegación centrada en la decisión y resumen fiel

La interfaz DEBE ofrecer Resumen, Alertas y revisión, Calidad de datos, Modelo y
trazabilidad, y Evidencia y arquitectura. El Resumen DEBE priorizar el último
pronóstico registrado, sus fechas y el acceso a revisión humana.

#### Scenario: Leer el resumen

- **GIVEN** un historial disponible
- **WHEN** se abre Resumen
- **THEN** se presenta la fila con mayor fecha de referencia, su alerta, probabilidad disponible y fecha objetivo
- **AND** se distingue esa fecha de la cobertura de datos y se conserva la aclaración de señal predictiva relativa, no diagnóstico ni probabilidad agronómicamente calibrada.

#### Scenario: Navegar sin perder contexto

- **GIVEN** un sensor activo y un resultado consultado o generado
- **WHEN** se cambia de destino o se usa Atrás/Adelante
- **THEN** se conserva el contexto compartido, se identifica el destino activo y se enfoca su encabezado, sin iniciar POST
- **AND** los enlaces previos a calidad, predicción, linaje y evidencia siguen resolviendo al destino correspondiente.

### Requirement: Operaciones explícitas y protección de mutaciones

La interfaz DEBE serializar sus mutaciones por instancia y mostrar su progreso.
Durante una mutación DEBE impedir otra mutación y aplicar un cambio de sensor;
DEBE permitir navegar. No DEBE reintentar escrituras automáticamente.

#### Scenario: Evitar operaciones superpuestas

- **GIVEN** un pronóstico, validación o recalibración pendiente
- **WHEN** se intenta repetir la acción, modificar otra fila o iniciar otra mutación
- **THEN** se mantiene una sola escritura en curso y su control muestra progreso
- **AND** al completarse o fallar se liberan los controles sin perder el sensor de origen.

#### Scenario: Escritura exitosa con actualización fallida

- **GIVEN** un POST exitoso seguido de un GET fallido
- **WHEN** se presenta el resultado
- **THEN** se conserva la respuesta exitosa y se comunica por separado el fallo de actualización, con reintento GET
- **AND** no se invita a repetir el POST como si la operación no hubiera ocurrido.

#### Scenario: Resultado de escritura no verificable

- **GIVEN** una pérdida de conexión durante un POST
- **WHEN** no puede confirmarse su resultado
- **THEN** la interfaz explica la incertidumbre y ofrece consultar el estado antes de repetir la operación, sin reintento automático.

### Requirement: Corrección humana explícita y recuperable

La interfaz DEBE permitir confirmar el resultado o corregirlo mediante una etiqueta
observada explícita y una observación editable. DEBE mostrar errores junto a la fila
y conservar la autoridad del backend sobre maduración y procedencia.

#### Scenario: Guardar una corrección

- **GIVEN** una fila y su resultado original
- **WHEN** se abre «Corregir resultado»
- **THEN** se muestran resultado original y fecha objetivo, y no se envía ninguna escritura hasta guardar una etiqueta opuesta seleccionada explícitamente
- **AND** se envía la observación introducida, o cadena vacía si se omite, sin texto inventado; elegir la misma etiqueta orienta a confirmar.

#### Scenario: Confirmación o corrección guardada

- **GIVEN** una validación aceptada por el servidor
- **WHEN** se recibe la fila actualizada
- **THEN** la interfaz refleja ese registro y anuncia que la validación se guardó sin actualizar el modelo
- **AND** conserva separado el estado de alerta del estado de revisión.

#### Scenario: Cancelación o rechazo temporal

- **GIVEN** un formulario de corrección abierto
- **WHEN** se cancela
- **THEN** no se escribe y el foco retorna al activador
- **AND** si se guarda y el backend responde 409, se muestra su motivo junto a la fila y se conserva el contenido para revisión, sin eludir la regla temporal.

### Requirement: Estado honesto de correcciones y recalibración

La interfaz DEBE diferenciar correcciones registradas de fechas incorporadas al
predictor activo. No DEBE inferir elegibilidad temporal ni incorporación de una
edición posterior a partir del estado «rechazada» o de la sola fecha.

#### Scenario: Correcciones registradas y fechas incorporadas

- **GIVEN** feedback rechazado y metadata del predictor con `applied_feedback_dates`
- **WHEN** se presenta el resumen de recalibración
- **THEN** se muestran por separado las correcciones registradas y las fechas incorporadas
- **AND** no se rotula su diferencia como correcciones elegibles; si falta metadata, la incorporación se informa como desconocida.

#### Scenario: Recalibrar explícitamente

- **GIVEN** correcciones registradas y ninguna mutación pendiente
- **WHEN** el usuario ejecuta recalibración manual
- **THEN** el backend determina si son aplicables; sus rechazos se muestran sin inventar una versión nueva
- **AND** tras éxito se actualizan predictor y linaje, se conservan los pronósticos anteriores y se indica que la próxima ejecución usará el nuevo predictor, sin afirmar mejora de desempeño.

### Requirement: Presentación accesible y adaptable

La interfaz DEBE mantener jerarquía visual, tema claro consistente, controles
etiquetados, foco visible y estados comprensibles sin depender del color. DEBE
permitir completar consulta y revisión mediante teclado y en pantallas angostas.

#### Scenario: Uso mediante teclado

- **GIVEN** navegación con teclado sin ratón
- **WHEN** se selecciona sensor, consulta historial, corrige una fila y abre detalles
- **THEN** todos los controles son alcanzables y operables, el foco no queda oculto y los mensajes de guardado/error son anunciados
- **AND** los identificadores completos no dependen exclusivamente de hover o `title`.

#### Scenario: Pantalla angosta, zoom y contraste

- **GIVEN** anchos de 360, 768 y 1440 px, verificación de reflow a 320 CSS px y zoom 200%
- **WHEN** se recorren las vistas
- **THEN** no hay contenido o acciones recortados ni scroll horizontal global; las tablas bidimensionales usan contenedores accesibles
- **AND** se verifican contrastes WCAG 2.2 AA y etiquetas textuales para alerta y revisión; el modo oscuro del sistema no mezcla controles oscuros con superficies claras sin diseño.

### Requirement: Conservación de evidencia y explicación científica

La interfaz DEBE conservar el acceso al recorrido de arquitectura, evidencia
congelada, procedencia y limitaciones, diferenciados del estado operativo por sensor.

#### Scenario: Consultar evidencia y trazabilidad

- **GIVEN** cualquier sensor seleccionado
- **WHEN** se abre Evidencia y arquitectura
- **THEN** los valores y fuentes científicas existentes permanecen idénticos y la navegación no ejecuta experimentos
- **AND** Modelo y trazabilidad presenta el predictor para el próximo pronóstico sin atribuirlo a registros históricos; un error de integridad del linaje permanece explícito.
