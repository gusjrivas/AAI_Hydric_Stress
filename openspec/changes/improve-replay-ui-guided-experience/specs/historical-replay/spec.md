# Spec delta: historical-replay (presentación e interacción)

Este delta agrega requisitos de presentación/interacción de la capacidad
`historical-replay` sobre el comportamiento causal ya especificado por
RH-01…RH-13 (`openspec/changes/add-causal-historical-replay/specs/historical-replay/spec.md`,
todavía no archivado en `openspec/specs/`). No modifica, relaja ni reemplaza
ninguno de esos requisitos: el backend sigue siendo la única autoridad sobre
qué se oculta y cuándo se revela.

## ADDED Requirements

### Requirement: UI-01 — Recorrido guiado en una pantalla central

La interfaz DEBE ofrecer una pantalla central que permita, sin explicación
oral, seguir el recorrido datos disponibles → predicción archivada →
revelación de observaciones → explicación del resultado, con una
instrucción inicial breve y los detalles extensos en una sección
desplegable.

#### Scenario: Instrucción inicial visible

- **GIVEN** se abre la pantalla de reproducción histórica
- **WHEN** se renderiza por primera vez
- **THEN** se muestra una instrucción breve del recorrido y una
  identificación visible de que es una reproducción retrospectiva basada en
  un umbral estadístico, sin diagnóstico agronómico validado

### Requirement: UI-02 — Selección temporal comprensible con reloj dependiente del origen

La interfaz DEBE reubicar el reloj simulado en el origen elegido al cambiar
de origen, ocultando de inmediato cualquier resultado posterior, y DEBE
distinguir explícitamente la fecha de los datos usados para predecir, la
fecha alcanzada por la reproducción y la fecha objetivo de la predicción.
"Volver al inicio de este caso" DEBE conservar el origen seleccionado.

#### Scenario: Cambiar de origen reinicia el caso

- **GIVEN** un resultado ya revelado para un origen
- **WHEN** se selecciona otro origen disponible
- **THEN** el reloj se reubica en ese origen y el resultado anterior deja de
  mostrarse de inmediato, sin depender de que termine ninguna solicitud en
  vuelo

#### Scenario: Volver al inicio del caso conserva el origen

- **GIVEN** el reloj avanzado más allá del origen de un caso
- **WHEN** se activa "Volver al inicio de este caso"
- **THEN** el reloj vuelve al origen seleccionado y el origen elegido no
  cambia

### Requirement: UI-03 — Gráfico principal integrado en escala temporal real

El gráfico principal DEBE usar una escala temporal real (no por índice de
fila), preservar huecos por valores nulos y por fechas ausentes sin
interpolar, marcar el origen, el objetivo y el umbral estadístico, sombrear
el intervalo futuro todavía oculto, distinguir estilísticamente el
historial disponible de las observaciones reveladas, ofrecer una ventana
inicial de aproximadamente 30 días con ampliación explícita, y representar
la clase predicha en una banda separada del eje numérico de humedad, nunca
como una curva de humedad pronosticada.

#### Scenario: Fecha ausente por completo se trata como un hueco

- **GIVEN** una fecha de calendario dentro de la ventana visible sin fila
  alguna en la respuesta del historial
- **WHEN** se dibuja el gráfico
- **THEN** esa fecha corta el trazo igual que un valor nulo, sin unir sus
  vecinos con una línea recta

#### Scenario: La clase predicha nunca es una curva de humedad

- **GIVEN** una predicción archivada con `y_pred` conocido
- **WHEN** se dibuja el gráfico
- **THEN** la clase se muestra en una banda separada del eje numérico de
  humedad, sin agregar un punto o segmento a la serie de humedad

### Requirement: UI-04 — Predicción explicada en palabras sin lenguaje de ejecución

La interfaz DEBE explicar la predicción archivada en una oración en
lenguaje llano ("Para el [fecha objetivo], se/no se anticipó humedad por
debajo del umbral"), acompañada de la etiqueta "Predicción archivada" y el
horizonte del contrato, sin usar lenguaje que sugiera una ejecución o
entrenamiento nuevo.

#### Scenario: Redacción sin lenguaje de ejecución nueva

- **GIVEN** cualquier estado de la predicción archivada
- **WHEN** se presenta al usuario
- **THEN** el texto no contiene "Ejecutar arquitectura", "Entrenar" ni
  ninguna animación que simule una inferencia nueva

### Requirement: UI-05 — Comparación explicativa con cuatro categorías y distancia física al umbral

Tras revelar la observación, la interfaz DEBE mostrar qué anticipó el
modelo, la humedad observada con su unidad, el umbral utilizado, la
relación de la observación con el umbral, y la categoría del resultado
(alerta correcta, falsa alerta, omisión de alerta, ausencia de alerta
correcta), calculada a partir de `y_pred` e `y_true` archivados sin
reclasificar. La distancia al umbral, cuando se muestre, DEBE expresarse en
la unidad física del umbral, con signo explícito, y nunca denominarse
"error del modelo".

#### Scenario: Las cuatro categorías se derivan sin reclasificar

- **GIVEN** un par archivado `(y_pred, y_true)`
- **WHEN** se muestra la comparación
- **THEN** la categoría exhibida corresponde exactamente a la tabla
  (1,1)→alerta correcta, (1,0)→falsa alerta, (0,1)→omisión de alerta,
  (0,0)→ausencia de alerta correcta, sin excepciones

#### Scenario: Distancia al umbral solo con medición válida

- **GIVEN** una observación revelada cuyo estado de medición no es "medida"
  o cuyo valor es nulo
- **WHEN** se muestra la comparación
- **THEN** no se calcula ni se muestra una distancia numérica al umbral,
  se declara explícitamente que no es calculable

### Requirement: UI-06 — Estados explícitos sin conversión a "sin alerta"

La interfaz DEBE distinguir, con texto propio, los estados cargando,
predicción no disponible, resultado todavía oculto, observación no
disponible, resultado revelado y error de consulta, sin presentar ninguno
de los tres últimos casos de ausencia/error como si fuera "sin alerta".

#### Scenario: Objetivo no observado no se confunde con ausencia de alerta

- **GIVEN** `target_observed=false` para la predicción vigente
- **WHEN** se muestra el resultado
- **THEN** se declara "observación no disponible" y no se ofrece feedback ni
  se etiqueta como una categoría de resultado
