# Emisión operacional conectada a Mi cultivo — HU4/HU5/HU6

Fecha: 2026-09-21. Rama: feat/hu6-productor-integracion-final, PR #207.
Estado: entrega incremental del PR #207; alcance de merge y pendientes vigentes en
[producer-ui-main-integration.md](producer-ui-main-integration.md).

## Capacidad entregada

`POST /api/v2/sensors/{sensor_id}/forecasts`, cuerpo `{}` e `Idempotency-Key`:
usa un snapshot común y bundles ya ajustados de h=1/2/3. No entrena por HTTP.
El adaptador local carga `PRODUCER_BUNDLE_ROOT/<sensor_id>/horizon_<h>/`;
la ruta es configuración de administrador, nunca entrada del cliente.

El exportador operacional agrega `bundle.json` como último marcador de cada
horizonte: contrato, configuración de features, entorno y SHA-256 de archivos.
La carga verifica sensor/horizonte, contrato temporal, unidades, entorno exacto,
features y clases; comprueba los bytes antes de deserializar. Joblib se usa solo
con archivos locales confiables. Los hashes detectan corrupción, no autentican
archivos que un tercero pueda reemplazar junto con su metadata.

Inferencia usa únicamente datos hasta la fecha solicitada, respeta retardos y
ventanas, rechaza huecos recientes y no retrocede para esconder faltantes.
El umbral de decisión continúa en 0.5, sin optimizarlo contra evaluación.
El umbral del evento se recupera congelado del contrato. Cada horizonte falla
independientemente. Un fallo no equivale a ausencia de alerta.

La persistencia registra conjuntamente bytes Parquet del snapshot, contratos de
bundles, emisiones y respuesta HTTP original. Replay se resuelve antes de leer
mediciones/modelos. Otra clave puede completar fallos, conservando éxitos y sus
contratos; datos diferentes para el mismo día dan conflicto. Un fallo de escritura
no deja media emisión. Otra operación concurrente retorna 409 operation_in_progress.
No hay nuevas mutaciones por GET ni cambios a la demo legacy/reserva demo-.

Mi cultivo permite consultar explícitamente los tres días, revisar resultados y
refrescar pendientes/historial. Avisa la antigüedad; las tarjetas ya no llaman
«mañana» a una fecha relativa a mediciones históricas. Los reintentos inciertos
conservan su clave; un cambio de sensor descarta respuestas tardías.

## Porcentajes y despliegue: límites explícitos

Esta entrega NO habilita porcentajes: `display_probability=null`,
`probability_status=not_qualified`, `probability_reason_code=incompatible_assessment`.
La presencia de un calibrador o de un resultado passed en disco no basta para
aprobar compatibilidad de dominio/rango. Ese adaptador/gate sigue pendiente.

El directorio de bundles es un adaptador local de integración sobre los artefactos
que ya exporta el orquestador. No reemplaza el registro/versionado MLflow de
ADR-0013: publicación, activación y evidencia operacional real siguen pendientes.
No copiar un bundle entre IDs para evitar controles; sensor e identidad deben
coincidir. Bundles antiguos sin bundle.json se conservan, pero no se reutilizan.
No se ejecutó la corrida de desarrollo real ni se abrieron holdouts.

## Activación

Habilitar PRODUCER_V2_ENABLED=true. En Docker, PRODUCER_BUNDLE_ROOT tiene por defecto
/workspace/data/operational_bundles, dentro del volumen de datos. Cada sensor requiere
sus propios bundles preparados y confiables; la UI no crea esos archivos ni ajusta
modelos. Sin modelos o sin lecturas se muestra indisponibilidad explícita.
Desactivar v2 conserva catálogo, mediciones, emisiones y opiniones almacenadas.

## Verificación

- Frontend: 136 tests; lint y build correctos.
- Datos/modelado afectados: 97 tests (storage, catálogo, históricos, preparación,
  contratos, manifiestos, orquestador, CLI e inferencia persistida).
- Tras reforzar la validación del contrato: 12 tests de inferencia nuevamente correctos.
- HTTP integrado: entrenamiento/exportación sintéticos, tres horizontes, snapshot,
  confirmación, replay exacto después de feedback, datos cambiados, fallo parcial,
  recuperación, ausencia de datos/modelos, reserva demo, escritura fallida y lock.
- Los dos changes afectados pasan OpenSpec estricto.
- Revisión visual pendiente: cua.getState no inició; el runtime reportó
  helper_unknown_error al aplicar deny-read ACLs. No se declara prueba de navegador
  ni viewport móvil por las pruebas DOM/HTTP.

Suite backend completa: **100 passed**, 11 warnings, 273 segundos. Tras el último ajuste de carga diferida, las 7 pruebas HTTP de emisión y 12 de inferencia pasaron nuevamente (**19 passed**). No se repitió la suite completa por ese ajuste acotado. El backend previo sigue siendo importable sin cargar el orquestador nuevo durante su arranque.
No se declara CI verde por estas verificaciones locales.

## Trazabilidad

HU2 (snapshot), HU4 (inferencia), HU5 (persistencia de opiniones) y HU6/UI.
Capacidades data-ingestion, predictive-modeling, human-feedback,
architecture-integration y alerting-ui. CRISP-DM despliegue/integración, con pruebas
sintéticas; sin nueva configuración experimental, hipótesis o arquitectura.
No se modifican manifiestos congelados, datos ni resultados históricos.
Sin nueva evidencia científica HU7/HU8; aporte al capítulo 3: identidad,
transacciones y recorrido funcional. Continúan pendientes de entregas posteriores la evidencia
real, gate, registro/activación, resumen/recalibración v2, experiencia completa y QA visual.

Actualización de cierre: el usuario aprobó la prueba funcional general en Docker.
La revisión móvil/teclado específica no está acreditada. Backend posterior: 101 tests
aprobados en bdb6a50; los conteos anteriores documentan sus respectivas entregas.
