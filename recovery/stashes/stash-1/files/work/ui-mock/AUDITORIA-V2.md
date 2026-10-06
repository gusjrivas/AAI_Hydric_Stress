# Revisión del mock Cultiva v2

Alcance: propuesta visual e interactiva aislada. No se modificó el frontend ni el
backend de la aplicación. Los datos y los tres horizontes son ilustrativos.

## Hallazgos corregidos

- El último valor de temperatura variaba al elegir 7 o 30 días: ahora depende de
  la fecha, no del índice dentro del período.
- El gráfico de 30 días y la tabla deben usar la misma ventana y los mismos datos.
- Los borradores se conservan por sector para impedir guardar inadvertidamente
  una observación del sector anterior.
- En pronóstico parcial, el mensaje principal se adapta al sector; no anuncia una
  alerta en un sector cuyos resultados disponibles no la tienen.
- Elegir una tarjeta reconstruía los controles y perdía el foco: se restablece el
  foco en la tarjeta elegida, conservando su estado accesible.
- A 320 px, selector y fecha se superponían: se reorganizó el encabezado y se
  verificó nuevamente que no se solapen.
- Error, ausencia de mediciones, datos antiguos y horizonte faltante se distinguen
  de “sin alerta”. El error tiene una acción de reintento simulada.

## Comprobaciones realizadas

- Pruebas del mock con JSDOM: navegación, tres horizontes, ventanas, valores
  consistentes, huecos sin interpolar, observaciones aisladas, borradores,
  texto vacío, representación segura de texto y cinco estados informativos.
- Chrome: recorrido de mediciones con tabla de 30 días y registro de observación.
- Anchos de viewport 1024, 390 y 320 px; sin desbordes detectados en las vistas
  comprobadas. Inspección de capturas en apariencia clara y oscura.
- Activación de tarjeta con Enter y conservación del foco; controles de inicio
  medidos con al menos 44 px de alto en la vista móvil comprobada.
- Error de consulta seguido de reintento: recuperación al estado de ejemplo.
- Sin errores de consola capturados en la revisión final.

## Límites de la aprobación interna

Pasa las comprobaciones realizadas para revisión de diseño; no equivale a una
validación con productores ni a una certificación de accesibilidad. La vista
aislada usada en Chrome no incorpora los iconos Lucide que aporta el host de la
visualización. Se verificó la legibilidad de los controles sin depender de iconos.

La implementación real requiere definir/evaluar horizontes +1 y +2, la presentación
de probabilidades, los nombres de sectores y el contrato de observaciones. La
observación libre del mock no equivale a una etiqueta agronómica ni cambia modelos.
No representa resultados de HU7/HU8. No hubo cambios metodológicos ni de arquitectura.

El nombre Cultiva es una propuesta de identidad, no una decisión de producto.

## Ampliación: revisión de alertas por día

Se agregaron Confirmar/Rechazar, comentario opcional, guardar/cancelar y edición
de la revisión. La tarjeta conserva su pronóstico original y añade el estado de
revisión. La revisión se aísla por sector y fecha objetivo y se guarda solo en
memoria del mock durante la sesión; recargar reinicia estas revisiones.

El selector de recorrido del prototipo permite pasar del 18 al 21 de septiembre.
El día 18 los controles de revisión de la alerta del 21 están deshabilitados; el
día 21 la alerta de ese mismo día puede revisarse, según la corrección del usuario.
Los resultados conservan su fecha de emisión del 18 de septiembre. Este ajuste
afecta únicamente al mock; aplicar esta regla al backend requiere revisar el
contrato temporal de feedback vigente antes de implementarla.

`audit-review.cjs` verifica bloqueo temporal, confirmación, rechazo, cancelación,
edición, aislamiento y preservación del pronóstico. Flujo de rechazo y guardado
comprobado también en Chrome. No se modificó el contrato real de feedback.

### Revisión tardía sin vencimiento

Según la indicación del usuario, la elegibilidad comienza en la fecha objetivo y
no tiene límite superior. El recorrido del 28 de septiembre permite revisar la
alerta pendiente del 21. Se distingue la fecha de la alerta de la fecha efectiva
de revisión y nunca se presenta una alerta histórica como situación actual.
Pruebas: pendiente y habilitada siete días después; revisión tardía conserva el
objetivo del 21 y registra la respuesta con fecha 28. La persistencia definitiva
de pendientes corresponde a la implementación real; este mock mantiene las
revisiones durante la sesión y no escribe datos del sistema.

## Sensores y registros

En Mediciones se añadió origen simulado, punto de medición por sector, última
fecha, cantidad de registros de la ventana, valores y registros diarios con
unidades y faltantes. El alta local propuesta incorpora un punto sin lecturas;
no lo usa en el pronóstico ni combina series de sensores. Los nombres y las altas
son datos de diseño, no capacidades CRUD existentes del backend.

Verificación de código del backend: `FEATURE_COLUMNS` contiene humedad del suelo,
radiación solar y humedad relativa. Temperatura y lluvia son contexto registrado.
Las unidades se contrastaron con `predictive_modeling/contract.py`. El endpoint
histórico actual aún no devuelve radiación/humedad relativa: su presentación real
requiere ampliar el contrato de lectura. El catálogo de puntos requiere desarrollo.

Otras capacidades útiles existentes: completitud/valores inusuales (`quality`),
objetivo y estado de revisión (`feedback`), cantidad/fechas de correcciones
incorporadas (`models/active`, con linaje para verificar referencias). No convertir
diagnósticos de calidad en porcentajes de confianza ni afirmar mejora por feedback.
