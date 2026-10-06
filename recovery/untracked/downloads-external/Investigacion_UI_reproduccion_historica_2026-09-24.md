# Investigación de UI: explorar una predicción y contrastarla con lo observado

Fecha: 24/09/2026. Repositorio: `gusjrivas/AAI_Hydric_Stress`. Snapshot de `main`: `f17fe658bad4726202fe13784bb716c06468af9a`.

## Dictamen

La mejora principal consiste en convertir la reproducción histórica en el recorrido central de la demostración: elegir una fecha, comprender qué información estaba disponible, consultar la predicción archivada, revelar lo ocurrido y explicar el acierto o el error. La base técnica ya existe. Se requiere reorganizar la interacción, ampliar la representación temporal y hacer explícito qué se está comparando.

El candidato histórico disponible predice una clase binaria a +3 días. No predice un valor continuo de humedad ni la fecha del primer episodio de estrés. Por ello, una curva de «humedad pronosticada» o un indicador «se equivocó por dos días» no puede construirse legítimamente a partir de este resultado.

Se recomienda una primera entrega centrada en la evidencia existente, seguida de ampliaciones separadas para evaluación agregada, otros horizontes y comparación de configuraciones. No resulta necesario cambiar la hipótesis ni volver a entrenar para conseguir una mejora sustancial de comprensión.

## Alcance y comprobaciones

Se inspeccionaron la navegación, la vista del productor, la reproducción histórica, sus componentes gráficos, contratos de API, política de admisión, lector del paquete, proyección temporal, especificaciones OpenSpec y pruebas relacionadas. Se examinó también una captura histórica incluida en el repositorio; no corresponde a una sesión de navegador ejecutada durante esta revisión.

Se validó el paquete `base-seed4-1157696b7b-v2` mediante `load_package`. Se verificó mediante ejecución directa la proyección de sus 67 registros: ocultamiento anterior al origen, ausencia del resultado antes del objetivo, revelación en la fecha objetivo y nuevo ocultamiento al retroceder. Se comprobó además el filtro temporal del historial con una pequeña fixture. No se ejecutaron modelos, recalibraciones ni experimentos A/B/C.

La suite pytest no se ejecutó porque esa dependencia no estaba disponible en el entorno. La comprobación directa anterior no equivale a una prueba integral del backend, frontend o navegador. No se modificó el repositorio ni se certificó su CI.

## Hallazgos respaldados por código

| Hallazgo | Evidencia | Consecuencia para el diseño |
|---|---|---|
| Ya existe un recorrido retrospectivo con datos reales | `HistoricalReplayPage.tsx`, router `replay.py` | Conviene evolucionarlo en lugar de crear otra demo desconectada |
| El backend excluye observaciones futuras de las respuestas | `projection.py`, `history_view.py`, serialización del router | La revelación debe conservarse en el servidor, no limitarse a ocultar gráficos |
| La UI mantiene dos controles temporales independientes | `selectedOrigin`, `simulatedDate`; el selector solo cambia el primero | Puede quedar seleccionada una predicción posterior al reloj, o ya revelada sin que el usuario entienda por qué |
| Cambiar el origen no reinicia el reloj | `onChange` del selector | Para el recorrido guiado, seleccionar un caso debe situar el reloj en su origen |
| «Reiniciar» vuelve al primer origen del paquete | `resetClock()` | Deben distinguirse «Volver al inicio de este caso» y «Elegir otro caso» |
| El gráfico solo muestra historial de humedad | `MoistureHistoryChart.tsx` | No integra fecha de emisión, objetivo, umbral ni resultado posterior |
| El gráfico usa posiciones por índice de fila | `stepX`; vista SVG de 480 × 120 | Debe usarse una escala temporal real para no comprimir intervalos cuando falten fechas |
| Se preservan huecos con valores nulos | Segmentación del gráfico | Conservar este comportamiento y contemplar también fechas ausentes |
| El CSS limita el gráfico a 480 px | `HistoricalReplayPage.css` | La comparación principal merece todo el ancho disponible y etiquetas legibles |
| La comparación es «Coincide/Discrepa» | `prediction.coincide` | Falta explicar si hubo alerta correcta, falsa alerta u omisión |
| Solo se admite un candidato histórico | `admission_policy.py` | No ofrecer un selector de múltiples modelos que aparente soporte inexistente |
| El candidato es `base`, horizonte +3 | Manifiesto y configuración efectiva | No presentarlo como demostración de todas las variantes de la arquitectura |
| La salida del clasificador se excluye de la API | `schemas_replay.py` | No se puede mostrar un porcentaje de confianza con el contrato actual |
| La calibración no está acreditada para este run | Manifiesto | No denominar a `y_proba` «probabilidad de estrés» o «confianza» |
| El historial público solo expone humedad | `ReplayHistoryRow` | Mostrar radiación y humedad relativa exige ampliar la API de forma causal |
| La navegación principal no incluye replay entre sus destinos | `useHashRoute.ts`; enlace separado en `App.tsx` | La demostración queda subordinada a pantallas operativas; debe tener un acceso principal y estado activo propio |

La captura histórica consultada muestra cuánto espacio puede ocupar la ficha técnica al expandirse. En el código actual se implementa con `details` cerrado por defecto; no se afirma que siempre aparezca abierta.

## Qué representa realmente la predicción

El paquete contiene 67 predicciones archivadas, con orígenes entre el 19/10/2024 y el 28/12/2024. El horizonte es de tres días. La última fecha utilizada para entrenar es el 15/10/2024 y el corte de partición es el 19/10/2024. Estas fechas no deben confundirse.

La clase positiva indica humedad observada en la fecha objetivo inferior a **0,31678178906440735 m³/m³**, umbral P20 congelado a partir del entrenamiento. Es un indicador estadístico relativo; no constituye un diagnóstico agronómico validado.

Hay dos umbrales diferentes: el anterior define la clase observada; el valor **0,5** aplicado a la salida del clasificador define la decisión predicha. No comparten unidad ni significado. El detalle técnico actual no expone el segundo mediante la API, aunque RH-13 establece esa distinción. Se recomienda revisar la trazabilidad de ese requisito al ampliar el detalle técnico.

El dataset consolidado tiene 366 filas y 88 valores nulos de humedad. Esa cifra describe el archivo completo inspeccionado, no el historial visible para cualquier fecha. La pantalla deberá calcular su resumen únicamente sobre el intervalo permitido por el reloj.

La configuración efectiva utiliza humedad del suelo, radiación solar y humedad relativa, con retardos y medias móviles. No activa detección de anomalías en este candidato. La demostración debe mostrar qué componentes participaron efectivamente, sin iluminar todas las etapas como si todas hubieran intervenido.

## Recorrido propuesto

### 1. Situarse en una fecha

Título: **Explorar una predicción**.

Contexto visible: «Reproducción histórica · Melchor Romero · Datos de 2024». Nota breve permanente: «Alerta basada en un umbral estadístico de humedad; no es un diagnóstico agronómico».

Control principal: **Datos disponibles hasta [fecha de origen]**. Solo se podrán seleccionar fechas con predicciones archivadas. Al cambiarla, se reinicia el caso en esa fecha y se oculta la observación posterior. Un modo de exploración libre puede conservar ambos relojes, pero no debería ser el modo inicial.

Se mostrarán dos fechas con funciones distintas: «Predicción basada en datos hasta…» y «Reproducción avanzada hasta…». Al revelar el futuro, la primera queda fija. Los nuevos datos no deben parecer insumos de la predicción original.

### 2. Comprender los datos utilizados

Gráfico principal de humedad, con una ventana inicial de 30 días y opción de ampliar a 90 días o todo el historial permitido. El eje horizontal será temporal, con marcas de origen y fecha objetivo. La escala vertical permanecerá estable al revelar el resultado para facilitar la comparación.

El umbral se mostrará como línea horizontal y zona inferior sombreada. La leyenda dirá «Umbral estadístico del experimento». Los huecos permanecerán visibles y no se completarán por razones estéticas.

Antes de revelar, el espacio posterior al origen quedará vacío y etiquetado «Observaciones todavía ocultas». Los indicadores de clase predicha se ubicarán en una banda separada del eje de humedad: una clase no tiene coordenada física en m³/m³.

En un panel secundario «Qué información utilizó» podrán incorporarse humedad relativa y radiación solar, cada una con su unidad y escala, después de ampliar el contrato. No se mezclarán variables diferentes en un único eje.

### 3. Consultar la predicción

Tarjeta principal: «Para el [fecha objetivo], se anticipó humedad por debajo del umbral» o «Para el [fecha objetivo], no se anticipó humedad por debajo del umbral».

Etiqueta visible: «Predicción archivada · horizonte de 3 días». Botón principal: **Ver qué ocurrió el [fecha objetivo]**. Botón secundario: **Avanzar un día**.

En el modo actual no corresponde usar «Ejecutar arquitectura» o una animación que aparente entrenar e inferir: el backend consulta evidencia archivada. La ejecución nueva debe constituir un modo separado si se incorpora en el futuro.

### 4. Revelar y explicar el resultado

Al avanzar, el backend devuelve únicamente las observaciones que ya corresponda revelar. El historial posterior al origen usa un trazo distinto y la leyenda «Observaciones reveladas después de la predicción». La predicción queda congelada.

La tarjeta de resultado debe responder, en este orden:

1. ¿Qué anticipó el modelo?
2. ¿Qué humedad se observó en la fecha objetivo?
3. ¿Quedó por debajo o por encima del umbral?
4. ¿Fue una alerta correcta, falsa alerta, omisión o ausencia de alerta correcta?

El feedback se ofrecerá después, con el texto «Registrar una observación sobre este caso». Debe aclararse que conserva el pronóstico original y no modifica automáticamente los próximos resultados.

## Cómo mostrar «qué tan lejos estuvo»

| Comparación | Qué permite afirmar | Disponibilidad |
|---|---|---|
| Clase predicha frente a clase observada | Acierto, falsa alerta u omisión para la fecha objetivo | Disponible |
| Humedad observada menos umbral congelado | Cuánto se ubicó la observación por debajo o por encima del umbral | Derivable de campos actuales tras revelación |
| Fecha objetivo menos fecha de origen | Horizonte con el que se emitió la predicción | Disponible: 3 días |
| Humedad pronosticada menos humedad observada | Error numérico de predicción en m³/m³ | No disponible en este candidato binario |
| Inicio pronosticado frente a inicio observado de episodio | Error temporal y anticipación respecto del inicio | Requiere definición de episodio y contrato adicional |
| Precisión, sensibilidad y falsas alertas del conjunto | Rendimiento de una colección evaluable de casos | Requiere extensión de evaluación; la spec actual excluye métricas agregadas |

La distancia observada al umbral **no es el error numérico del modelo**. Debe llamarse «Distancia de la observación al umbral». Tampoco permite concluir por sí sola la gravedad agronómica de un caso.

Un pronóstico positivo a +3 días no demuestra tres días de anticipación al inicio de un episodio: la humedad podría estar ya por debajo del umbral en el origen. Para evaluar anticipación real se necesita definir inicio, continuidad, recuperación y tolerancia de asociación entre alertas y episodios; los huecos no deben resolverse suponiendo continuidad.

## Casos reales que permiten demostrar los cuatro resultados

Datos leídos del paquete autorizado. Humedad redondeada a cuatro decimales; clasificación con el umbral original sin redondear.

| Origen | Objetivo | Predicción | Humedad observada m³/m³ | Resultado |
|---|---|---|---:|---|
| 19/10/2024 | 22/10/2024 | Sin alerta | 0,2785 | Omisión: hubo humedad inferior al umbral |
| 21/10/2024 | 24/10/2024 | Alerta | 0,3495 | Falsa alerta: la humedad no fue inferior al umbral |
| 22/10/2024 | 25/10/2024 | Sin alerta | 0,3633 | Ausencia de alerta correcta |
| 30/10/2024 | 02/11/2024 | Alerta | 0,2990 | Alerta correcta |

Ejemplo de explicación del primer caso: «Con datos hasta el 19 de octubre no se anticipó una alerta para el 22. Ese día se observaron 0,2785 m³/m³, aproximadamente 0,0383 m³/m³ por debajo del umbral. El modelo omitió la alerta».

Estos ejemplos ilustran categorías; no estiman el rendimiento general ni justifican seleccionar el modelo. Un catálogo didáctico con resultados etiquetados debe estar separado del modo de exploración con futuro oculto, porque elegir «falsa alerta» ya revela el desenlace.

## Diseño técnico propuesto

### Primera entrega: presentación y estado de interacción

Reutilizar los endpoints actuales. Separar la página en componentes como `ReplayTimeline`, `ReplayComparisonChart`, `ReplayPredictionSummary` y `ReplayOutcomeCard`; mantener un coordinador de selección y reloj.

Estados explícitos: carga, sin predicción disponible, predicción visible con resultado oculto, resultado revelado, observación no disponible y error de consulta. No sustituir observaciones faltantes por ceros ni clasificar errores de red como ausencia de alerta.

Conservar la protección por generación monotónica y la comprobación de identidad en cada render. El cambio A→B→A y los envíos de feedback en vuelo ya motivaron correcciones; el rediseño no debe eliminarlas. La selección y el reloj deben cambiar juntos para iniciar un caso, sin mostrar resultados transitorios del anterior.

Mostrar las cuatro categorías de resultado mediante una función pura de `y_pred` y `y_true`, solamente cuando `target_observed` sea verdadero. Derivar la distancia al umbral a partir de la medición original; validar previamente que el valor sea finito y exista. Conservar la clase archivada; no reemplazarla por una reclasificación silenciosa del valor redondeado.

### Segunda entrega: explicar los insumos y la arquitectura

Ampliar el historial con las variables efectivamente utilizadas, unidades y procedencia. La API debe distinguir datos originales, transformaciones e imputaciones. El paquete contiene marcadores derivados de imputación, pero el contrato de historial no los expone: su existencia no basta para presentarlos como disponibles en pantalla.

Incorporar «Cómo se obtuvo» con hechos de la configuración: datos disponibles, preparación aplicada, variables temporales, modelo utilizado y decisión de alerta. Anomalías, sintéticos y retroalimentación deberán aparecer como aplicados, no aplicados o no acreditados según evidencia, no como una secuencia ficticia.

La ficha técnica puede añadir la regla de decisión 0,5 y su procedencia. Si se expone la salida del clasificador, hacerlo en detalle técnico, con la limitación de calibración y mediante cambio explícito del contrato.

### Tercera entrega: comparación de rendimiento

Una nueva especificación deberá definir evaluación agregada, población elegible, denominadores, faltantes, horizontes y punto del reloj hasta el que se computa. Los resultados ocultos no deben filtrarse por contadores o resúmenes. No mezclar feedback humano con medición objetiva ni usar confirmaciones manuales como verdad observada.

La comparación con persistencia puede ser útil: el archivo contiene esa referencia, pero la API actual no la expone. Su incorporación requiere mantener su definición y comparar sobre las mismas fechas evaluables.

Agregar otros candidatos o +1/+2 requiere comprobar identidad, entrenamiento anterior a la predicción, madurez de etiquetas de entrenamiento, procedencia y compatibilidad temporal. No basta con reutilizar modelos operativos actuales para fechas históricas.

## Prioridades y criterios de aceptación

| Prioridad | Entrega | Criterio verificable |
|---|---|---|
| P0 | Caso guiado y controles temporales | Elegir una fecha fija el origen y sitúa el reloj allí; el resultado vuelve a estar oculto |
| P0 | Gráfico integrado | Origen, objetivo, umbral, huecos y datos revelados se distinguen con texto y forma, además de color |
| P0 | Explicación del resultado | Cada caso produce la categoría correcta; no se muestra un falso error de humedad |
| P0 | Acceso principal al replay | La navegación identifica correctamente la vista activa y evita confundirla con operación en tiempo real |
| P1 | Insumos y procesamiento | Cada variable o componente mostrado tiene respaldo en el contrato y la configuración del caso |
| P1 | Observaciones faltantes | La UI diferencia resultado oculto, ausente y error de consulta |
| P2 | Resumen de evaluación | Solo cuenta objetivos revelados y elegibles, con denominadores visibles y contrato aprobado |
| P2 | Otros modelos y horizontes | Cada candidato supera admisión independiente; no se habilitan opciones ficticias |

Pruebas necesarias: transición origen→objetivo→retroceso; respuesta tardía A→B→A; cambio de caso durante feedback; todas las categorías; objetivo no observado; fechas ausentes y nulas; navegación por teclado; lectura en pantalla pequeña. En el caso real todas las filas tienen `target_observed=true`; los estados ausentes necesitan fixtures identificadas como pruebas.

Se recomienda validar comprensión con personas que no conozcan la implementación. Sin explicación oral, deberán poder identificar la fecha de los datos, la fecha predicha, qué se anticipó, qué ocurrió y si se acertó. Registrar errores y dudas antes de ampliar funciones. Esta validación permanece pendiente; no se presenta como realizada.

## Impacto sobre el Trabajo Final

La primera entrega mejora la demostración de HU6 y la comunicación de HU8, conservando hipótesis, propósito y alcance. La IA permanece en el centro; no se incorpora hardware obligatorio ni automatización de riego.

La segunda entrega aumenta la trazabilidad comunicada, pero exige adaptar contratos y pruebas. La tercera incorpora análisis y debe especificarse separadamente. La regresión de humedad o la predicción del inicio de episodios ampliaría el problema técnico y la validación: no se recomienda como requisito para resolver esta mejora de UI.

El presupuesto y la dedicación base de 600 horas se mantienen como referencia. No se asignan horas nuevas sin descomposición y revisión del cronograma. La prioridad propuesta reduce el riesgo de introducir modelado adicional mientras se prepara la memoria.

La memoria podrá explicar la separación entre predicción archivada, reloj simulado y observación posterior. Una captura del resultado revelado, con fechas y umbral legibles, aportaría más que una captura de la ficha técnica. La UI no convierte este replay en evidencia de utilidad agronómica ni cierra por sí misma los gates científicos.

## Fuentes principales del snapshot

Todos los enlaces apuntan al commit inspeccionado, para evitar referencias móviles.

- [Página de reproducción histórica](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/frontend/src/features/historical-replay/HistoricalReplayPage.tsx)
- [Gráfico de humedad](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/frontend/src/features/historical-replay/MoistureHistoryChart.tsx)
- [Router de reproducción](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/backend/app/routers/replay.py)
- [Contratos de reproducción](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/backend/app/schemas_replay.py)
- [Política de admisión](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/src/historical_replay/admission_policy.py)
- [Paquete autorizado](https://github.com/gusjrivas/AAI_Hydric_Stress/tree/f17fe658bad4726202fe13784bb716c06468af9a/replay_packages/base-seed4-1157696b7b-v2)
- [Especificación de reproducción](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/openspec/changes/add-causal-historical-replay/specs/historical-replay/spec.md)
- [Vista del productor](https://github.com/gusjrivas/AAI_Hydric_Stress/blob/f17fe658bad4726202fe13784bb716c06468af9a/frontend/src/features/producer/ProducerView.tsx)

Se trata de una investigación de implementación y propuesta de diseño fundamentada en el repositorio. No constituye un estudio de usabilidad con participantes ni una revisión bibliográfica externa.
