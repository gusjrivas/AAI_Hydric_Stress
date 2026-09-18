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

Soporte mínimo propuesto: ambas clases y al menos 20 observaciones de cada clase
en calibración y evaluación por horizonte, después de purga/faltantes.
Si no se cumple, declarar insufficient_evidence; no cambiar cortes para salvarlo.
Informar F1, precisión, recall, MCC, AP, prevalencia, Brier, log-loss y diagrama de
calibración de diez bins de igual amplitud con conteos (bins vacíos explícitos).
Comparar con score sin calibrar y climatología de entrenamiento, en las mismas
fechas; incluir persistencia. No seleccionar semilla por sus resultados.

Gate de presentación propuesto y predeclarado: para cada horizonte, en todas las
semillas evaluables, Brier calibrado menor que climatología y no mayor que raw,
y log-loss calibrado no mayor que raw. Todas las semillas deben ser evaluables.
Si no pasa, display_probability=null y probability_status=not_qualified.
Si pasa, probability_status=development_assessed y evaluación/versiones enlazadas.
Esto NO es validación agronómica ni generalización externa. Revisión del criterio
solo por nueva versión predeclarada, nunca ajuste retrospectivo para pasar.

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
