# Contrato operacional v2 — objetivo e implementación incremental

Estado: contrato aceptado, implementación parcial. PR #207 entrega catálogo,
lecturas, GET/POST de emisiones y reviews. Resumen, assessments y recalibración
v2 siguen pendientes. El OpenAPI del backend describe las rutas ejecutables;
este documento conserva también el contrato objetivo de las entregas futuras.
Base /api/v2. JSON en UTF-8; nombres de campos estables en inglés.
La UI traduce etiquetas y motivos a lenguaje cotidiano.

## Convenciones comunes
- Identificadores opacos salvo sensor_id, que conserva regex [a-zA-Z0-9_-]{1,64}.
- date: YYYY-MM-DD calendario UTC. timestamp: RFC3339 UTC terminado en Z.
- calendar_timezone: UTC; server_today calculado por servidor. Nunca reloj cliente.
- revision: entero creciente; expected_revision obligatorio al editar.
- Idempotency-Key obligatorio en POST de emisión/recalibración. Reutilización con
  cuerpo distinto: 409 idempotency_conflict. Reviews usa request_id en el cuerpo.
  Conservar resultados idempotentes al menos mientras exista el recurso; reinicio
  no pierde las claves. Operación en curso devuelve 409 operation_in_progress
  reintentable, sin ejecutar dos veces. Error transitorio no crea éxito ficticio.
- GET no muta. Timestamps de emisión no son fecha de medición ni fecha objetivo.
- NaN e infinito nunca se serializan: null más incidencia de calidad.
- Listados: items, next_cursor nullable. limit default 50, rango 1..200;
  cursor opaco ligado a filtros. Cambio de filtros con cursor previo: 422.
  Consultas paginadas usan orden estable con ID de desempate y corte de consulta
  fijado en cursor para no perder pendientes por nuevas inserciones.
- Error: {error:{code,message,details,request_id}}. message apto para registro;
  UI traduce code. 422 validación; 404 recurso desconocido; 409 estado/concurrencia;
  503 dependencia no disponible. Un fallo de almacenamiento nunca equivale a vacío.
- Aplicar acceso existente y aislamiento en todos los cruces sensor/forecast.

## Catálogo
GET /sectors y GET /sensors: listado paginado; sensor admite sector_id opcional.
POST /sectors: {display_name,crop?}; crea sector_id, revision=1.
PATCH /sectors/{sector_id}: {expected_revision,display_name?,crop?,primary_sensor_id?}.
El primario debe existir y pertenecer al sector; null lo desasigna.
POST /sensors: {sensor_id,display_name,sector_id?,source_kind}.
PATCH /sensors/{sensor_id}: {expected_revision,display_name?,sector_id?,source_kind?}.
POST retorna 201; duplicado 409. PATCH retorna 200; revisión obsoleta 409.
Nombres y cultivo: trim, longitud 1..80; crop nullable. source_kind declarado:
real | synthetic | unknown. Declaración no sobrescribe procedencia de lecturas.
No reasignar sector si el sensor ya tiene lecturas o emisiones: 409.
Respuesta sector: sector_id,display_name,crop,primary_sensor_id,revision,created_at.
Respuesta sensor: sensor_id,display_name,sector_id,source_kind,revision,created_at,
registered (boolean). Descubrimiento legacy puede devolver registered=false y
display_name=sensor_id; adoptar con POST no cambia datos ni modelo.
GET no persiste descubrimientos. Sin catálogo no se invalida ingestión legacy.

## Historial y aportes de datos
GET /sensors/{sensor_id}/readings?days=30&end=YYYY-MM-DD.
days 1..365, default 30; end default última fecha almacenada, o server_today si
no hay lecturas. Ventana inclusiva de days días calendario. Filtro nunca cambia
con silenciosos fallbacks. Datos futuros y conflictos diarios se reportan, no
se normalizan escondiendo inconsistencias.
Respuesta:
- sensor_id, calendar_timezone, server_today, snapshot_id.
- window: start_date,end_date,expected_days.
- status: ready | no_readings; rows ordenadas por date.
- rows: date, variables (siete campos numéricos nullable), origin, quality_flags.
- origin: real | synthetic | unknown por fila, según procedencia guardada.
- missing_dates, variable_coverage (variable,observed_days,missing_days).
- units y input_roles: {variable,role,basis,model_reference}; role=model_input |
  context_only | unknown; basis=issued | configured | unknown. Roles corresponden a un modelo identificado o a una
  configuración explícitamente etiquetada; no afirmar uso real sin emisión.
- last_reading_date nullable, data_age_days nullable; no campo online derivado
  del histórico. Procedencia agregada: real | synthetic | mixed | unknown;
  unknown si falta procedencia; mixed cuando constan fuentes real y synthetic.

Variables/unidades: soil_moisture=m3/m3; relative_humidity=%;
solar_radiation=MJ/m2/day; temperature=degC; precipitation=mm/day;
wind_speed=m/s; et0=mm/day. Mantener valores y unidades del contrato de ingestión.
La UI puede formatear humedad en porcentaje solo con conversión explícita.
Sensor registrado sin datos: 200 no_readings, rows=[]; desconocido: 404.
Faltantes permanecen ausentes/null, nunca mediciones sintetizadas por GET.
Contadores son diagnósticos descriptivos. Anomalías existentes no pasan a ser
features del predictor por agregarlas a la pantalla.
La carga conserva POST /sensors/{sensor_id}/readings legacy y sus validaciones;
este change no agrega una segunda semántica de escritura de mediciones.

## Emisión
POST /sensors/{sensor_id}/forecasts, cuerpo {}, Idempotency-Key requerido.
Selecciona la última fecha almacenada y evalúa elegibilidad de cada bundle;
as_of_date es la última fecha almacenada, sin retroceder silenciosamente para
ocultar faltantes. Captura snapshot antes de inferir. Datos insuficientes por
horizonte dan unavailable. Un error global de persistencia responde 503.
Respuesta 201 para nueva tanda, 200 para recuperación existente. Reintento de
misma clave devuelve mismo código/cuerpo original.
Tanda:
- batch_id, revision, sensor_id, contract_version=producer_daily_h123_v1.
- as_of_date, issued_at, snapshot_id, calendar_timezone, server_today.
- data_age_days, provenance; slots exactamente h=1,2,3.
- slot: horizon_days,target_date,status,reason_code,forecast_id,
  alert,score,score_kind,display_probability,probability_status,
  decision_threshold,event_threshold,model_reference,review.
- status available | unavailable. En unavailable forecast_id,alert,score,
  score_kind,display_probability,decision_threshold,event_threshold,
  model_reference,review y probability_status son null; reason_code obligatorio.
- available: forecast_id estable, alert boolean, score [0,1],
  score_kind raw_model_score | calibrated_probability.
  alert corresponde a score >= decision_threshold; threshold explícito.
  display_probability [0,1] solo con gate aprobado; no valor multiplicado por 100.
  probability_status development_assessed | not_qualified; model_reference.assessment_reference
  identifica evidencia si calificada. No implica validación agronómica externa.
- event_threshold: {variable:soil_moisture,value,unit:m3/m3,comparison:lt}.
  No confundir umbral del evento con umbral del clasificador.
- model_reference: {model_version,horizon_days,contract_version,trained_through,
  calibration_version,assessment_reference}; valores desconocidos son null
  y bloquean emisión si impiden verificar compatibilidad.
- review se define abajo. Identidad estable por sensor+as_of_date+h+contrato;
  target_date=as_of_date+h. No deducir identidad únicamente de target_date.
Una tanda sin lecturas no se persiste: batch_id=null, revision=0 y as_of_date=null y slots con target_date=null,
status=unavailable, reason_code=no_readings; no inventar días observables.
El primario no altera el sensor real al cual pertenece la emisión.
Completar slots previamente fallidos requiere otra clave, mismo snapshot
persistido y nueva revisión de tanda; éxitos previos no cambian. Snapshot cambiado
para una clave emitida: 409 issued_snapshot_conflict, no sobreescritura.
Unavailable no es emisión revisable ni registro de alerta.

Ejemplo de slot disponible (IDs y valor son ilustrativos, no evidencia real):
```json
{
  "horizon_days": 1,
  "target_date": "2026-09-19",
  "status": "available",
  "reason_code": null,
  "forecast_id": "fc-example-h1",
  "alert": true,
  "score": 0.72,
  "score_kind": "calibrated_probability",
  "display_probability": 0.72,
  "probability_status": "development_assessed",
  "probability_reason_code": null,
  "decision_threshold": 0.5,
  "event_threshold": {
    "variable": "soil_moisture", "value": 0.18,
    "unit": "m3/m3", "comparison": "lt"
  },
  "model_reference": {
    "model_version": "example-v1", "horizon_days": 1,
    "contract_version": "producer_daily_h123_v1",
    "trained_through": "2026-09-17",
    "calibration_version": "example-cal-v1",
    "assessment_reference": "example-development-assessment"
  },
  "review": {
    "status": "pending", "revision": 0, "review_open_at": "2026-09-19T00:00:00Z",
    "reviewable": false, "blocked_reason": "review_not_open",
    "latest_review": null, "training_eligibility": "no_review",
    "applied_review_references": []
  }
}
```
Este ejemplo presupone as_of_date=2026-09-18, server_today=2026-09-18
y evaluación de desarrollo calificada. No fijar esos valores en implementación.

## Consulta, resumen y filtros
GET /sensors/{sensor_id}/forecasts: historial de emisiones disponibles.
Filtros opcionales target_from,target_to inclusivos (fecha objetivo, no emisión),
horizon_days 1|2|3, review_status pending|confirmed|rejected, cursor,limit.
Sin filtro de fechas consulta todo el historial. Orden target_date DESC,
issued_at DESC,forecast_id ASC. Respuesta agrega pending_total y
reviewable_pending_total del sensor completo, independientes de ventana y página.
GET /sensors/{sensor_id}/forecasts/{forecast_id}: emisión y review actuales.
GET /sensors/{sensor_id}/overview: sensor, sector nullable, server_today,
calendar_timezone, last_reading_date,data_age_days,provenance,
latest_batch nullable, pending_total,reviewable_pending_total,
active_models (por horizonte), applied_feedback_count por bundle y
latest_applied_review_at nullable. Contadores de incorporaciones representan
revisiones exactas aplicadas, no todas las opiniones registradas.
latest_batch null significa no emitido, no ausencia de riesgo.
El mismo forecast_id debe mostrar la misma review en resumen, detalle e historial.
No cachear estados de apertura atravesando medianoche sin recalcularlos.
GET /sectors/{sector_id}/overview: sector y selected_sensor_id=primary_sensor_id;
overview nullable y selection_required=true si falta primario. No elegirlo
automáticamente ni promediar sensores.

## Revisión humana
POST /sensors/{sensor_id}/forecasts/{forecast_id}/reviews
cuerpo {request_id,expected_revision,action,comment?}.
action confirm | reject; comment nullable, hasta 2000 caracteres.
Etiqueta derivada en servidor: confirm=alert; reject=complemento.
201 revisión nueva. Reintento idéntico devuelve respuesta original.
409 review_not_open, revision_conflict, idempotency_conflict o demo_write_locked.
Emisión perteneciente a otro sensor: 404 sin filtrar información.
review:
- status pending | confirmed | rejected; revision inicial 0.
- review_open_at,reviewable,blocked_reason nullable.
- latest_review nullable: review_id,request_id,action,observed_label,comment,reviewed_at.
- training_eligibility: no_review | waiting_target_maturity |
  requires_mature_revalidation | compatible_correction | confirmation_only |
  incompatible_source_model | incompatible_contract | insufficient_data |
  applied. El orden de evaluación es madurez, compatibilidad y acción.
- applied_review_references: revisiones y bundles que realmente las utilizaron.
reviewable significa puede registrar/actualizar opinión ahora, no que será usada
para entrenar. Después de revisar puede volver a corregir con expected_revision.
No vence. La captura mismo día no requiere posterior acción para quedar guardada.

## Recalibración explícita
POST /sensors/{sensor_id}/recalibrations
cuerpo {horizon_days}; Idempotency-Key requerido.
Opera solo sobre contrato v2 y fuente compatible siguiendo HU5. 200 con estado
updated | no_eligible_corrections; model_reference y applied_review_references.
No entrenar con opiniones inmaduras ni mezclar horizontes. No forma parte de un
GET ni se dispara automáticamente al confirmar. Fallo de dependencia: 503;
demo_write_locked:409. No obliga a mostrar un botón técnico en UI del productor.

## Casos mínimos de contrato
Probar fechas +1/+2/+3, sensor vacío, huecos, unidades, desconocido, parcial,
sin calibración calificada, snapshot cambiado, revisión temprana/tardía,
revisión duplicada/concurrente, aislamiento, filtros que cambian resultados,
pendientes fuera de ventana, cursor, medianoche UTC, fallos de almacenamiento
y bloqueo demo. Validar ejemplos con los esquemas generados al implementar.

## Evidencia de calibración y publicación (corrección del criterio)
assessment_reference identifica un informe inmutable con assessment_result:
not_evaluated | insufficient_evidence | failed | passed, motivos, versión/hash
del manifiesto, artefactos evaluados, dominio, rangos respaldados y diagnósticos
con incertidumbre definidos en add-daily-multihorizon-predictors/design.md.
No alcanza un Brier/log-loss favorable para obtener passed.
La respuesta de un slot available agrega probability_reason_code nullable:
not_evaluated | incomplete_assessment_plan | insufficient_evidence |
calibration_criteria_failed | unsupported_probability_range |
incompatible_assessment. Es null si el porcentaje se publica.
En unavailable es null: reason_code ya explica la indisponibilidad del predictor.
Un informe passed no habilita porcentajes fuera de su rango/dominio ni para
otro bundle. En esos casos probability_status=not_qualified y
display_probability=null, aunque la alerta binaria siga disponible.
El ejemplo de slot disponible anterior presupone probability_reason_code=null.
development_assessed significa evidencia limitada al desarrollo, no validación
agronómica o externa. El detalle del informe debe poder recuperarse mediante
GET /sensors/{sensor_id}/assessments/{assessment_reference}, de solo lectura,
con el mismo aislamiento y política de acceso; desconocido o de otro sensor:404.
No devolver rutas locales ni permitir acceso arbitrario a archivos.


## Dependencias resueltas el 2026-09-20
La identidad exacta, transacciones y reserva demo- se rigen por
[decisiones de emisiones y feedback](../../../docs/design/backend-producer-ui-emission-dependencies.md).
La reserva permanente reemplaza la comprobacion de demo activa para mutaciones v2.

## Robustez de listados (corrección posterior al PR #207)

Los cursores de pronósticos están ligados también al sensor de la ruta. Reusar
un cursor en otro sensor devuelve 422 invalid_cursor. Cursores anteriores sin
esa asociación deben descartarse y reiniciar la consulta desde la primera página;
no se requiere migración de datos persistidos.

El orden continúa siendo target_date DESC, issued_at DESC, forecast_id ASC.
La continuación compara esa clave aunque el registro ancla haya cambiado de
estado. El corte congela las emisiones incluidas, no las opiniones: filtros de
revisión y contadores reflejan el estado actual en cada lectura. Para recuperar
cambios anteriores al cursor se inicia otra consulta; no es un snapshot de reviews.
Un rango target_from > target_to devuelve 422 invalid_date_range.
