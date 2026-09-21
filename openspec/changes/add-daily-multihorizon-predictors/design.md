# Diseño del contrato operativo

## Inferencia y target
Tres predictores directos; cada uno estima soil_moisture(t+h) < threshold_h,
h en {1,2,3}, con fecha exacta de calendario, no h filas después de compactar huecos.
Usar los mismos datos disponibles hasta as_of_date y un snapshot común.
Entrenamiento de cada predictor solo con targets observados hasta su corte.
Sin objetivo futuro observado se permite inferir, no etiquetar para entrenamiento.
Conservar features actuales y causalidad de lags/ventanas del contrato existente.
No concatenar resultados de modelos emitidos en días distintos como una sola tanda.

threshold_h se ajusta solo con el período de entrenamiento autorizado y se guarda
en cada bundle. Para la primera evaluación, usar el mismo período de referencia
observada para los tres umbrales, de modo que sean numéricamente iguales; purgar
ejemplos supervisados después, según su horizonte. No recalcular en inferencia.

Contrato/bundle incluye horizonte, unidades, features, imputación, threshold,
trained_through, corte de datos, modelo, estado de calibración y versión.
Separar identidad/caché/MLflow por sensor, horizonte y contrato; nunca cargar un
bundle legacy por semejanza del nombre. Reutilizar estimadores solo con validación
completa. Falla de un horizonte no inventa su valor ni invalida los otros.

## Evaluación predeclarada de desarrollo
Antes del primer ajuste, versionar manifiesto con dataset permitido y SHA,
fechas, modelo/hiperparámetros efectivos, dependencias, semillas [0,1,2,3,4],
particiones y criterios siguientes. No acceder a fuentes o holdouts de v4.
Puede usarse el dataset local ya observado de v3 como DESARROLLO exclusivamente;
no presentar su último tramo como holdout independiente. Datasets sintéticos
solo acreditan funcionamiento, nunca calibración para datos reales.

Primera estrategia propuesta: Random Forest con parámetros operativos existentes,
congelados en manifiesto; partición cronológica 60% entrenamiento, 20% calibración,
20% evaluación de desarrollo (redondeo hacia abajo para los dos primeros cortes).
No barajar. Purga por target_date antes de cada corte; transformaciones ajustadas
solo en entrenamiento; referencias de features exclusivamente retrospectivas.
Calibración sigmoid por horizonte sobre predicciones del bundle congelado en
el tramo de calibración. No usar este tramo para ajustar el estimador.

### Qué se evalúa y qué no acredita
El evento es humedad observada bajo el umbral congelado, proxy relativo; no
diagnóstico fisiológico. La referencia de evaluación son mediciones futuras
observadas, sin imputar targets ni sustituirlos por feedback selectivo.
Una salida predict_proba, buena clasificación, mejor Brier o mejor log-loss
no demuestran por sí solos calibración. Las dos últimas métricas combinan
calibración y capacidad discriminativa. Repetir cinco semillas mide sensibilidad
del entrenamiento; no agrega cinco muestras independientes ni más días observados.

### Manifiesto previo obligatorio
Antes del ajuste, el manifiesto MUST fijar también:
- población, sensor/sitio, procedencia, horizonte, evento y uso pretendido;
- fecha de congelamiento, hash de datos y declaración de exposición previa;
- diez intervalos de probabilidad de igual amplitud (incluyendo 1 en el último),
  minimum_bin_count y minimum_class_count, ambos enteros positivos;
- tolerancias numéricas epsilon_ece y epsilon_bin en (0,1), expresadas en
  puntos de probabilidad, con justificación de la precisión útil para la UI;
- minimum_coverage en (0,1], proporción mínima de casos en intervalos con soporte;
- número mínimo de bloques temporales distintos que se exige para evaluar;
- método de incertidumbre por bloques temporales, longitud de bloque en días,
  tratamiento de huecos, número de réplicas y semilla de remuestreo;
- ventanas de estabilidad temporales no solapadas dentro de evaluación, con
  fechas fijadas y los mismos criterios de soporte y tolerancia;
- semilla de despliegue elegida de antemano; nunca elegir la de mejor resultado.

Los valores de soporte, tolerancia y longitud de bloque requieren justificación
usando el uso previsto, conocimiento del dominio o únicamente datos de
entrenamiento. Este change NO inventa una tolerancia universal ni considera
20 casos por clase garantía suficiente. Esos valores quedan como decisión
explícita de la tarea 1, previa al primer ajuste. Manifiesto incompleto bloquea
calificación: assessment_result=insufficient_evidence, motivo
incomplete_assessment_plan. No inferir valores por defecto para obtener aprobación.

### Evaluación directa y dependencia temporal
Publicar por horizonte: gráfico de confiabilidad, probabilidad media,
frecuencia observada, diferencia firmada, número de casos/eventos y banda de
incertidumbre por intervalo. Mostrar también intervalos vacíos y no respaldados.
Informar F1, precisión, recall, MCC, AP, prevalencia, Brier y log-loss; comparar
modelo calibrado, raw, climatología ajustada en entrenamiento y persistencia
sobre exactamente las mismas fechas. Definir clipping numérico de log-loss
en el manifiesto, igual para todos; no ocultar fallos de baselines.

ECE se define como suma de n_b/N por abs(frecuencia_b - probabilidad_media_b)
sobre los intervalos no vacíos del conjunto evaluado. Es diagnóstico dependiente
del agrupamiento, no prueba suficiente por sí solo ni garantía punto a punto.
No omitir intervalos de poco soporte del cálculo para mejorar la cifra.
Coverage es la proporción de observaciones en intervalos con minimum_bin_count;
publicar además el rango de probabilidades respaldado por esos intervalos.

Estimar incertidumbre con remuestreo por bloques de días contiguos de los pares
(probabilidad, resultado), conservando dependencia temporal. No usar bootstrap
iid de filas ni contar semillas o horizontes como observaciones independientes.
Usar nivel nominal 95%; el algoritmo debe construir límites superiores
simultáneos para ECE y errores absolutos de intervalos respaldados, en la familia
completa de horizontes, semillas y ventanas evaluadas. Predeclarar construcción
(por ejemplo, corrección de multiplicidad sobre intervalos por bloques), réplicas
y supuestos. Si la serie no permite estimarlos de forma estable con los bloques
mínimos predeclarados, declarar insufficient_evidence, no bandas de ancho cero
como certeza. Verificar el estimador de incertidumbre con fixtures conocidos.

### Regla de presentación, por horizonte
Para calificar un horizonte, todas las semillas previstas, el período completo
y cada ventana de estabilidad predeclarada deben ser evaluables. Se requiere:
1. Soporte por clase, bloques y coverage al menos iguales a lo predeclarado.
2. Límite superior de ECE <= epsilon_ece y de cada error absoluto por intervalo
   respaldado <= epsilon_bin. Que una banda amplia incluya la diagonal NO basta:
   se necesita acotar el error dentro de la tolerancia, no solo no detectar error.
3. Como controles adicionales de utilidad: Brier calibrado menor que climatología
   y no mayor que raw, y log-loss calibrado no mayor que raw.

Estos controles acotan una afirmación de calibración agrupada en el dominio y
períodos evaluados. No acreditan todas las condiciones agronómicas ni probabilidades
fuera de rangos respaldados. La inferencia solo publica porcentaje cuando el
horizonte califica, el bundle exacto coincide, la procedencia/sitio/unidades son
compatibles y el intervalo de su probabilidad tiene soporte en las evaluaciones
requeridas. Fuera de ese rango, display_probability=null con motivo
unsupported_probability_range; no extrapolar la calificación.

assessment_result=passed solo cuando se cumplen todos los requisitos.
Con evidencia suficiente pero tolerancias/controles incumplidos: failed.
Con soporte, plan o incertidumbre insuficientes: insufficient_evidence.
Sin evaluación: not_evaluated. No transformar ausencia de evidencia en éxito.
Salvo passed compatible, display_probability=null y probability_status=not_qualified.
Con passed compatible: probability_status=development_assessed y evidencia enlazada.
El informe conserva motivos, límites y casos no evaluables, además de predicciones
por fecha, hashes de modelos/calibradores, manifiesto y comando reproducible.

Solo es evaluación de desarrollo. Datos sintéticos acreditan funcionamiento,
no probabilidades reales. Una afirmación de validación externa exige datos reales
independientes y autorización/protocolo separado, sin reutilizar holdouts
protegidos. Ni esta corrección ni su implementación autorizan abrirlos.
Modificar el plan después de examinar resultados exige nueva versión y declarar
exploratorios los datos ya consultados; cambiar versión no los vuelve independientes.

El score de decisión es calibrated cuando pasa el gate, raw en caso contrario,
siempre con threshold=0.5 y score_kind explícito. La API distingue score de
display_probability; no presenta un raw como porcentaje validado.
Una aplicación real del calibrador requiere compatibilidad de procedencia,
unidades, sitio y horizonte; no aplicar uno real a demo sintética y declararlo
validado. Cada bundle nuevo o recalibrado invalida el gate anterior salvo
evidencia de evaluación correspondiente al nuevo artefacto.

## Disponibilidad y errores
Estados por horizonte: available o unavailable; motivo machine-readable.
No tener evidencia probabilística no equivale a no poder generar alerta:
puede existir score sin porcentaje publicable. Sin ambas clases entrenables,
contrato compatible o features suficientes, unavailable con nulos.
El permiso de activar UI con probabilidades ausentes debe ser visible en el
criterio de cierre; no falsificar porcentajes para coincidir con el mock.

## Referencias y trazabilidad de la corrección
- [scikit-learn: calibración, curvas y límites de Brier/log-loss](https://scikit-learn.org/stable/modules/calibration.html).
- [Dimitriadis, Gneiting y Jordan: diagramas de confiabilidad e incertidumbre](https://arxiv.org/abs/2008.03033).
La elección específica de bloques, tolerancias y regla de aceptación es una
propuesta de diseño operacional del proyecto; no un umbral universal de esas
referencias. HU4, Épica 2, predictive-modeling; CRISP-DM modelado/evaluación.
No cambia controlled_daily_v3/v4, configuraciones formales, hipótesis, alcance,
capas de arquitectura ni resultados HU7/HU8. Aporte a capítulos 2 y 3: límites
de la evidencia y publicación honesta de probabilidades.
