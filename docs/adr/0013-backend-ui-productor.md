# ADR-0013: Contratos operativos para una UI orientada al productor

Estado: **Aceptado por el autor el 2026-09-19**. Implementación incremental en
`feat/hu6-backend-soporte-ui`; la aceptación no declara completas las entregas.

## Contexto
El backend base PR #205 emite una predicción t+3 por sensor/día, usa la fecha
de origen como clave de feedback y exige que termine el día objetivo para validar.
No existe catálogo con nombres de sectores/sensores. El usuario pide +1/+2/+3,
revisión desde el mismo día sin vencimiento y lecturas visibles.

## Decisión propuesta
Mantener FastAPI como fachada (ADR-0003), persistencia local detrás del contrato
de acceso (ADR-0002), aislamiento por sensor (ADR-0008) y modelos en MLflow
(ADR-0006). Se agregan contratos operativos v2, con espacios de almacenamiento y
registro de modelos distintos de legacy y de la investigación.

- Catálogo descriptivo de sectores/puntos: no implica conexión de hardware ni
  genera mediciones. Un sector selecciona explícitamente una serie para pronosticar.
- Predictores independientes para h=1,2,3; una identidad por sensor, día de datos,
  horizonte y versión del contrato de emisión. No interpolar t+3.
- Feedback usa forecast_id, con revisiones versionadas y fechas del servidor.
  La captura desde el día objetivo se separa de la elegibilidad para entrenamiento.
- Rutas v2 aditivas; no cambiar la semántica de fechas/rutas legacy. La demo
  histórica actual conserva sus bloqueos y protocolo hasta una adaptación probada.
- Calendario UTC diario explícito en esta versión. No interpretar automáticamente
  el día local del navegador como día de registro o de elegibilidad.

## Impacto explícito
Se amplía el contrato operativo de HU4/HU5/HU6, no las capas de arquitectura ni
la hipótesis. El registro de opinión intradía es una nueva capacidad operativa,
no una reinterpretación de validated_at ni de la madurez de controlled_daily_v3.
La nueva identidad implica versionar almacenamiento, cachés y linaje y probar
compatibilidad legacy sin reescribir archivos históricos. No incluye migración automática.

## Alternativas descartadas
- Tres tarjetas repitiendo t+3 o emisiones antiguas: no son tres predicciones
  con los mismos datos disponibles.
- Usar fecha objetivo como única clave: colisionan emisiones/horizontes distintos.
- Habilitar intradía quitando el guard de recalibración: confunde opinión con
  objetivo maduro y permite fuga temporal.
- Catálogo que fusiona sensores automáticamente o autentica hardware: fuera del
  alcance y del beneficio funcional solicitado.

## Implementación y aprobación
El plan y los cuatro changes están en
[backend-producer-ui-plan.md](../design/backend-producer-ui-plan.md).
El autor aceptó este ADR y los cuatro changes vinculados el 2026-09-19. La
aceptación habilita su implementación incremental, pero no autoriza experimentos
formales ni reemplaza los gates metodológicos de cada change.

## Precision operacional del 2026-09-20
Se especifican identidad sin reemision exitosa y reserva permanente demo- para v2
en [dependencias](../design/backend-producer-ui-emission-dependencies.md).
La demo legacy sigue operativa; integrar reviews v2 en ella queda fuera de esta
entrega. Implementacion y pruebas pendientes; no habilita ajuste ni porcentajes.
