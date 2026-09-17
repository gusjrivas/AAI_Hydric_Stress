# Diseño: interfaz de apoyo a la decisión

## 1. Estructura y jerarquía

Cabecera global: nombre de la aplicación, indicación de prototipo experimental,
sensor activo y formulario «Cambiar sensor». Separar `draftSensorId` de `activeSensorId`:
solo Enter o «Aplicar» con identificador válido cambia el contexto. Conservar `sensor-a`
como valor inicial actual; no presentarlo como sensor descubierto o conectado.

Navegación con enlaces por hash, destino activo identificable y comportamiento
Atrás/Adelante. Evitar sumar un router solo para cinco vistas locales. Mantener los
enlaces existentes `#calidad`, `#prediccion`, `#linaje` y `#evidencia` como destinos
compatibles; `#prediccion` abre Alertas y revisión. `#resumen` es la entrada por defecto.
Al cambiar de vista, actualizar el título del documento y enfocar su encabezado.

| Destino | Contenido principal | Detalle secundario |
|---|---|---|
| Resumen | Último pronóstico registrado, fechas, pendientes de revisión, acción de generar pronóstico | Calidad resumida y acceso al predictor activo |
| Alertas y revisión | Historial, filtros, confirmar y corregir | Observación y detalles del registro |
| Calidad de datos | Período disponible, faltantes, duplicados y anomalías | Variables y método diagnóstico |
| Modelo y trazabilidad | Predictor para el próximo pronóstico, recalibración manual y cronología | Contrato, identificadores completos y hashes |
| Evidencia y arquitectura | Evidencia congelada, limitaciones y recorrido de defensa | Procedencia de los resultados |

Resumen en escritorio: tarjeta principal de pronóstico y contexto de datos a su lado;
revisiones pendientes debajo. En móvil: mismo orden en una columna. La ausencia de
datos tiene texto y siguiente paso válido; ausencia de pronóstico no significa «Sin alerta».

## 2. Estado, consultas y operaciones

Un controlador compartido por sensor mantiene historial, resultado de ejecución,
estado de operación e invalidaciones. Las vistas reutilizan ese estado: navegar no
debe borrar el resultado ni iniciar POST. Las consultas de calidad, predictor y linaje
conservan sus estados independientes; un fallo de MLflow no debe ocultar el historial.

Cada consulta captura sensor y generación de solicitud. Usar cancelación o descarte
de respuestas obsoletas; al cambiar de sensor no se muestran datos anteriores bajo
el identificador nuevo. No actualizar recursos durante la edición del borrador.

Serializar las mutaciones de esta instancia de la interfaz: pronosticar, confirmar,
corregir y recalibrar. Mientras una mutación está pendiente, bloquear otras mutaciones
y aplicar otro sensor; permitir navegación y lecturas. El bloqueo global se acompaña
de estado local en la fila/botón responsable. Evita también que dos filas escriban
simultáneamente el mismo archivo de feedback desde esta UI.

No reintentar POST automáticamente. Ante pérdida de respuesta, informar que el
resultado no pudo verificarse y ofrecer actualizar mediante GET antes de repetir.
Si un POST termina correctamente pero falla un GET posterior, distinguir éxito de
la operación y fallo de actualización; no sugerir que la escritura falló.

## 3. Datos y semántica

| Presentación | Fuente existente | Regla |
|---|---|---|
| Historial | `GET /feedback/{sensor_id}` | 404 del registro ausente es vacío; otros fallos son error, no cero registros. |
| Último pronóstico registrado | Fila de historial con mayor `fecha` | Mostrar también filas sin probabilidad; no descartar registros incompletos. |
| Resultado recién generado | `POST /forecast/{sensor_id}/run` | Conservar éxito aunque falle la recarga de historial; reconciliar por `fecha`. |
| Referencia y objetivo | `fecha`, `fecha_objetivo` | Fechas calendario sin conversión que reste un día por zona horaria; objetivo nulo es «No disponible». |
| Datos disponibles hasta | `GET /quality/{sensor_id}` → `period_end` | No confundir con fecha de generación ni fecha del último pronóstico. |
| Predictor para próxima ejecución | `GET /models/{sensor_id}/active` | No atribuirlo a todos los pronósticos históricos. |
| Correcciones registradas | Feedback rechazado con etiqueta corregida | No llamarlas automáticamente pendientes ni elegibles. |
| Incorporación por fecha | `applied_feedback_dates` del predictor activo | Indicar «Fecha incorporada al predictor activo»; no afirmar que una edición posterior de esa fila fue aplicada. |
| Linaje | `GET /lineage/{sensor_id}` | Preservar error de integridad; no mostrar cadena parcial como completa. |

La API actual no expone una versión de cada validación ni un preflight de elegibilidad.
Por ello se muestran correcciones registradas y fechas incorporadas como información
separada, sin calcular un total de «listas para recalibrar». Si falla la consulta de
predictor, la incorporación queda desconocida. La acción manual de recalibrar puede
estar disponible cuando hay correcciones registradas y no hay operación pendiente;
el backend decide si existen correcciones nuevas y temporalmente elegibles.

Los filtros operan sobre el historial cargado: alerta/sin alerta/todas, estado de
validación y rango inclusivo de `fecha` (etiquetado «Fecha de referencia»). Orden
descendente por `fecha`. Diferenciar historial vacío de filtros sin coincidencias.
Los contadores generales se calculan sobre el historial completo, no sobre el filtro.

## 4. Revisión humana

Confirmar conserva el significado del endpoint actual. «Corregir resultado» abre un
formulario inline asociado a la fila, con fecha objetivo, resultado original,
resultado observado y observación opcional (cadena vacía si se omite). Guardar exige
seleccionar explícitamente una etiqueta opuesta a la original; una etiqueta igual
se orienta a Confirmar. Cancelar no escribe y devuelve foco al activador.

No inventar una observación ni enviar la corrección al abrir el formulario. Tras
guardar, mostrar el registro devuelto por el servidor y «Validación guardada; el
modelo no se actualizó». Los rechazos temporales o de procedencia (409) se muestran
junto a la fila, conservando el formulario. No usar el reloj local como autorización
para validar: la comprobación temporal sigue en el backend.

Recalibrar es una acción explícita en Modelo y trazabilidad, con explicación breve de
su efecto. Tras éxito refrescar predictor y linaje; conservar los pronósticos previos
y aclarar que la nueva versión se utilizará en la próxima ejecución. No declarar una
mejora de desempeño a partir de la existencia de un sucesor.

## 5. Sistema visual y accesibilidad

Tokens globales para fondo, superficie, texto, texto secundario, bordes, acción,
alerta y estado de revisión. Partir de la paleta existente (fondo `#f4f6f2`, texto
`#1b2a1e`, acción `#1f5b6b`, alerta `#c1440e`) y verificar contrastes en sus usos reales.
Tema claro coherente en esta entrega: retirar la declaración global de modo oscuro
parcial. Tema oscuro completo queda fuera del alcance.

Tipografía del sistema, escala de espaciado 4/8/12/16/24/32 px, cifras tabulares,
bordes discretos y acción primaria consistente. Eliminar padding de página y altura
mínima de viewport en componentes anidados. Estado predictivo y revisión tienen
etiquetas y tratamientos distintos; confirmar una alerta no la vuelve verde/segura.

Objetivo WCAG 2.2 AA: contraste de texto normal >= 4.5:1, texto grande >= 3:1,
componentes e indicadores relevantes >= 3:1; teclado, foco visible/no oculto,
etiquetas, mensajes asociados y enlace para saltar al contenido. Controles principales
con objetivo de 44×44 CSS px. No depender del color, hover o `title` para información
necesaria. Identificadores completos accesibles con desplegables de teclado.

Verificar 360, 768 y 1440 px, además de reflow a 320 CSS px y zoom 200%.
No scroll horizontal global; tablas científicas pueden tener contenedor horizontal
identificado y utilizable por teclado. Respetar `prefers-reduced-motion` si se añade
movimiento. Anunciar guardados con `role="status"` y errores con `role="alert"` sin
repetir anuncios de todos los paneles en cada interacción.

Referencias: [WCAG 2.2](https://www.w3.org/TR/WCAG22/) y
[divulgación progresiva](https://www.nngroup.com/articles/progressive-disclosure/).
El cumplimiento se verifica durante la implementación; este documento no lo certifica.

## 6. Límites y evolución

Mantener la evidencia científica estática separada del sensor; preservar números,
procedencia y limitaciones existentes. No añadir curvas sin una serie disponible,
confianza agronómica, indicadores «en vivo», importancia de variables o recomendaciones
de riego no provistas por los contratos.

El resumen no debe llamar «actual» a un resultado histórico: usar «Último pronóstico
registrado». Los detalles de arquitectura siguen accesibles para la defensa. La mejora
se implementa por las entregas de `tasks.md`, sin reescribir todas las features a la vez.
