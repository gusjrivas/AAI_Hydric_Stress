# Protocolo experimental vigente — calendario, objetivo y generalización (HU4–HU8)

Estado: implementación técnica aprobada por el autor el 2026-09-05. Versión
`controlled_daily_v3`. Sustituye el protocolo operativo anterior, preservando
las corridas `hu7-epica4`, `hu7-epica4-leakage-fix` y `hu7-epica4-purged-cv`.
No modifica hipótesis, propósito, alcance, entregables ni los cuatro componentes.
Las corridas locales `reference-v3-*` se conservan como evidencia histórica
provisional: fueron generadas antes del cierre completo de este protocolo y
contienen metadata de procedencia incompleta; no sustentan por sí solas nuevas
conclusiones de HU8.

## Definición del experimento

Una serie por localización/sensor, una fila por día UTC representado sin zona
horaria. Se rechazan fechas nulas, duplicadas, subdiarias y calendarios con días
omitidos. La preparación de otra fuente debe agregar/reindexar explícitamente;
no se mezclan localizaciones ni se compactan filas antes de calcular retardos.
Las medias móviles incluyen el día actual: la emisión supone que las observaciones
diarias ya están disponibles. Un backtest sobre archivos retrospectivos no acredita
por sí mismo la latencia de una alerta operativa.

El objetivo es `humedad_observada(t+3 días) < umbral_congelado`, proxy relativo,
no diagnóstico fisiológico de un cultivo. Las entradas se imputan por forward-fill;
el objetivo no se imputa. Las filas sin observación futura se excluyen únicamente
después de generar features, tanto en entrenamiento como en evaluación. La purga
usa la fecha objetivo anterior al corte, no el número de filas restantes.

Para experimentos de modelo fijo, el percentil se calcula sobre las observaciones
reales del entrenamiento limpio completo y se comparte entre condiciones. Para
selección automática se reserva el primer 20 % cronológico del entrenamiento como
calibración anterior a todos los folds; ese prefijo no participa como ejemplos en
la selección. El detector de anomalías se ajusta dentro de cada fold mediante una
transformación sklearn; el gap del horizonte y los diagnósticos se conservan.
El umbral congelado y el detector final se serializan con el estimador.

La selección automática falla como no evaluable si algún fold no contiene ambas
clases para entrenamiento y validación; no se descartan folds por candidato.

La evaluación es secuencial: las observaciones anteriores del período de test
pueden alimentar los retardos de días posteriores, pero nunca un ajuste del modelo.
Las fechas objetivo de entrenamiento deben ser anteriores a las fechas de evaluación.

## Contrato del modelo

`raw_input_features` describe entradas físicas; `model_features` y `model_dtypes`
describen la matriz efectiva, ordenada, del estimador. El contrato registra unidades,
frecuencia, día/momento de emisión, imputación, lags, ventanas, inclusión del día
actual, anomalías, contaminación, variable objetivo, horizonte, percentil, regla,
clase positiva, umbral de alerta y versiones. El paquete contiene el umbral de
estrés numérico, detector ajustado, fin de calibración, última fecha objetivo usada,
identidad del modelo y correcciones humanas aplicadas.

Cargar exige comparar el contrato antes de descargar y verificar después que las
columnas del estimador coincidan. Los modelos históricos incompletos se conservan,
pero no se reutilizan automáticamente. Inferencia no recalcula umbral ni detector.
Requiere el historial diario necesario para reconstruir causalmente las features.

## Escasez: dos mecanismos diferentes

Con el mismo conjunto elegible, objetivo y test se comparan:

1. `coverage`: se divide cronológicamente el entrenamiento en tantos estratos como
   ejemplos disponibles en el presupuesto; se elige una fecha por estrato con semilla.
2. `recent`: se toman las últimas N fechas elegibles con exactamente el mismo presupuesto.

Fracciones predefinidas para la fase científica: 1, 0.75, 0.5 y 0.25. La referencia
inicial de esta corrección usa 0.5. Ambas modalidades conservan el calendario de
observaciones para crear features; por ello miden escasez de ejemplos supervisados,
no ausencia de mediciones. El detector y el generador sintético solo se ajustan con
los ejemplos seleccionados. El período utilizado para calibrar el objetivo es común
al experimento y no debe confundirse con el presupuesto supervisado.

Un futuro escenario de escasez observacional debe enmascarar mediciones sobre la
grilla diaria, declarar cobertura por variable y registrar imputación/antigüedad de
la última observación. No debe eliminar filas ni cambiar silenciosamente el target.

## Ruido: observación separada de referencia

Las escalas se ajustan con entrenamiento limpio, nunca con test. La humedad usada
para etiquetar permanece sin perturbación experimental. No se afirma que sea una
señal fisiológica latente conocida. `both` perturba train y test; `test_only` mide
cambio de calidad al desplegar. Persistencia usa la misma observación ruidosa que
el modelo. Se conservan faltantes y se aplica la misma imputación causal.

Se usan streams de semillas distintos para selección, ruido de train, ruido de
test y síntesis, derivados reproduciblemente de cada semilla de repetición.
Intensidad 0.3 es una perturbación hipotética, no una caracterización validada de
un sensor. No se recortan resultados para producir mejoras.

## Métricas y evidencia

Precision, recall, F1, ROC-AUC, balanced accuracy, MCC y average precision (AP;
no integración trapezoidal de la curva PR). Baselines de persistencia, clase
mayoritaria de entrenamiento y siempre estrés, evaluados sobre las mismas fechas.
Se registran tamaños, prevalencia, umbral, configuraciones efectivas, semillas,
versiones de dependencias, SHA del dataset y commit, estado del árbol de trabajo,
predicciones por fecha y métricas por repetición. Métricas no definidas quedan como
NaN, nunca sustituidas por evidencia favorable; los entrenamientos sin ambas clases
o sin CV evaluable fallan explícitamente.

La dispersión entre semillas mide aleatoriedad del procedimiento sobre un test
común, no incertidumbre entre cinco poblaciones independientes. El test de 2024 ya
fue inspeccionado: las nuevas mediciones sobre él son una referencia de desarrollo,
no una confirmación externa independiente.

## Retroalimentación e inferencia

El pronóstico publica la última fecha observable aunque su target todavía no exista.
Se conserva una predicción emitida por sensor/día con versión, probabilidad, fecha
objetivo, umbral, fecha de emisión y fecha de validación. Repetir la solicitud devuelve
la predicción original de ese día para no cambiar el objeto que revisó el usuario.
Validar requiere que el día objetivo haya terminado. Registros antiguos sin metadata
son consultables, pero requieren una migración documentada antes de recalibrar.

Recalibrar usa objetivos observados maduros y correcciones maduras, preserva las
correcciones ya aplicadas y rechaza repeticiones sin nueva información. La frontera
`trained_through` es monótona y la recalibración falla si no puede reaplicar alguna
corrección histórica. El período
usado pasa a entrenamiento; solo fechas posteriores a su última fecha objetivo
pueden evaluarse fuera de muestra. El detector se mantiene congelado en este ciclo;
recalibración no redefine el objetivo. Umbrales incompatibles de feedback se rechazan.

## Próxima fase científica: diseñada, todavía no ejecutada

- **Datos:** incorporar primero otros años con humedad y clima compatibles, luego
  otra localización y un dataset independiente in situ preferentemente hortícola.
  Verificar acceso actual, licencia, profundidad, calidad, unidades, latencia y píxel
  real; no presentar dos puntos del mismo píxel como validación espacial independiente.
  Las entradas del catálogo HU2 son candidatos, no accesos revalidados en esta fase.
- **Particiones:** entrenar en períodos anteriores; reservar un período/localización
  externo que no se use para elegir variables, modelos ni umbrales. Informar por
  sitio/período además del agregado, y analizar cambio de prevalencia y distribución.
- **Variables:** actuales; temporales; actuales+temporales; combinación anterior con
  temperatura, precipitación y viento. Mantener target, test, semillas y baselines.
- **ET0:** comparar la última combinación sin/con ET0, con las mismas fechas y la misma
  información climática base. `estimate_et0` está en `data_quality/reference_et.py`,
  invocada por el mock, no por HU7/HU8. El consolidado tiene ET0 totalmente nula. Validar
  unidades, latitud, elevación y aproximación por temperatura media antes de derivarla.
- **Componentes:** cruzar base, síntesis, anomalías y ambas con pocas condiciones de
  ruido/escasez predefinidas. Comparaciones pareadas e intervalos por bloques temporales;
  ningún ajuste mirando test. Variar horizonte, cantidad sintética y contaminación
  en sensibilidad acotada, sin búsqueda dirigida a maximizar F1.
- **Humano:** entrenamiento inicial, adquisición de feedback, evaluación posterior.
  Comparar modelo congelado, reentrenamiento con datos recientes sin correcciones y
  con correcciones sobre los mismos datos. Fijar presupuesto e incluir también
  ausencia de alertas; toda simulación debe declararse como simulación.

Estas extensiones producen nueva evidencia, no corrigen artificialmente los
resultados desfavorables. La revisión sistemática pendiente de HU1 sigue pendiente.
ET0, deep learning, nuevas bases de datos, servicios de serving, despliegue productivo,
validación agronómica longitudinal y automatización del riego no se incorporan aquí.
