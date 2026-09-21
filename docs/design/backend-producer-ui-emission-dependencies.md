# Dependencias de emisiones y feedback v2 — decisiones previas

Fecha: 2026-09-20. Decisiones especificadas para implementación; no implementadas.
HU4/HU5/HU6; predictive-modeling, human-feedback y architecture-integration.
CRISP-DM: modelado operacional e integración. Configuraciones base/+sintéticos/
+anomalías/completa, protocolos v3/v4 y evidencia HU7/HU8 intactos.
No cambia hipótesis, alcance de tesis ni capas de arquitectura. Capítulo 3:
identidad, persistencia y exclusión; capítulo 2 conserva límites metodológicos.

## 1. Identidad e inmutabilidad
Una tanda tiene clave lógica (sensor_id, as_of_date, contract_version).
Una emisión tiene clave (sensor_id, as_of_date, horizon_days, contract_version).
target_date NO es clave. Ejemplo: datos 2026-09-20/h=3 y datos 2026-09-21/h=2
apuntan a 2026-09-23, pero son emisiones distintas y admiten opiniones separadas.
La misma clave no admite dos emisiones exitosas aunque cambie el modelo.

Codificación v1 determinista:
- batch_id = "batch_" + SHA256 del JSON UTF-8 compacto del array
  ["producer-batch-id-v1",sensor_id,as_of_date,contract_version].
- forecast_id = "fc_" + SHA256 del JSON UTF-8 compacto del array
  ["producer-forecast-id-v1",sensor_id,as_of_date,horizon_days,contract_version].
- Fechas YYYY-MM-DD UTC, horizonte entero, ensure_ascii=true, sin espacios,
  hash hexadecimal completo en minúsculas. Persistir y verificar también las
  claves originales: ante discordancia, error de integridad, no sobrescritura.
- model_reference, snapshot_id e issued_at son evidencia congelada de la emisión,
  no componentes que permitan esquivar la unicidad. No incrementar artificialmente
  contract_version para generar otra emisión el mismo día.

Una tanda persistida conserva los bytes de su snapshot y su hash. Éxitos inmutables.
Cada slot successful se crea una sola vez; unavailable no genera forecast_id.
Reintento con otra clave de idempotencia puede completar slots ausentes del
snapshot original; no recalcula éxitos. El modelo del nuevo slot debe respetar
as_of_date: ni entrenamiento ni calibración pueden incorporar targets posteriores.
Registrar su identidad real al emitir; no deducirla del modelo activo después.
Cambio de snapshot para la misma clave: 409 issued_snapshot_conflict.
Una nueva fecha de datos origina otra tanda. Sin datos, devolver disponibilidad
vacía sin crear tanda/forecast persistidos; batch_id=null, revision=0.
Una clave de idempotencia ya terminada se consulta antes de recapturar datos:
reproduce la respuesta guardada, incluso si llegaron días nuevos.

## 2. Persistencia transaccional e idempotencia
Repositorio operacional v2 separado por sensor, detrás del contrato de acceso.
Para esta PoC, documento versionado por sensor con tandas, emisiones, eventos de
review y resultados idempotentes. Lock entre procesos por sensor y reemplazo
atómico usando las primitivas existentes; no múltiples archivos que puedan
dejar un review guardado sin su resultado idempotente.
Snapshots inmutables por hash se escriben antes de referenciarlos; un fallo puede
dejar un snapshot huérfano, nunca una referencia publicada a un archivo inexistente.
No crear una infraestructura de base de datos adicional en esta entrega.

En futura inferencia, calcular fuera del lock; al adquirirlo revalidar la clave y
conservar el primer resultado ya publicado. Puede repetirse cálculo tras una caída;
se garantiza unicidad de registros, no ejecución de ML exactamente una vez.
Reviews: verificar request_id antes de expected_revision; un retry idéntico
devuelve el resultado original aunque la revisión actual haya avanzado.
Misma clave y otro payload: 409 idempotency_conflict.
Alcance de claves: sensor+ruta/operación+clave (incluye forecast_id para reviews).
Persistir evento, nueva revisión y resultado de request en el mismo commit atómico.
Revisión nueva: revision anterior+1; no reescribir eventos anteriores.
No registrar un éxito de HTTP si la persistencia falló.

## 3. Autoridad del bloqueo: reserva permanente del espacio demo-
Decisión explícita que reemplaza para v2 la política ambigua "solo demo activa".
El productor v2 no participa del ciclo del simulador legacy. Todo sensor_id que
empiece exactamente por "demo-" queda reservado a ese flujo, en cualquier estado:
prepared/running/pausing/paused/blocked/completed, incluso sin manifiesto local.
Base observada: DEMO_SENSOR_PREFIX en scripts/demo_simulation/config.py y
generación de ID exclusivo en prepare.py.

Backend/dominio rechaza POST v2 forecasts, reviews y recalibrations para ese
espacio con 409 demo_write_locked y details.reason=legacy_demo_sensor_reserved.
No depende de frontend, PID, timeout, reloj cliente o disponibilidad de manifiestos.
No se libera por finalizar la sesión. Así no hay carrera entre consultar estado
y escribir ni necesidad de comunicar locks entre contenedores.
No inferir reserva desde source_kind: sensores sintéticos fuera de demo- siguen
siendo elegibles para flujos v2 según sus otros requisitos.
GET y catálogo descriptivo/adopción siguen permitidos. No reasignar IDs para
sortear la reserva. Las rutas legacy no cambian y no se les atribuye exclusión
de clientes externos que actualmente no tienen.

Precedencia: validar entrada/recurso y pertenencia (404 si corresponde), luego
reserva demo-, luego idempotencia y reglas temporales/concurrencia del recurso.
Los replays v2 exitosos de sensores demo- no existen en esta versión: no migrar
ni sembrar tales emisiones. Si aparece un almacén incompatible, fallar explícito.
Limitación funcional: la demo acelerada actual no podrá demostrar reviews v2.
Una demo v2 futura requiere change propio; no introducir copias de datasets ni
fixtures como pronósticos reales para aparentar esa integración.

## 4. Alcance de la próxima implementación
Construir repositorio de emisiones y revisiones con fixtures aislados, identidad,
guard de reserva y lecturas/revisión HTTP. Sin endpoint público para cargar
pronósticos inventados. Emisión desde modelos, entrenamiento, probabilidades y
recalibración real permanecen pendientes. No conectar UI a fixtures.
Sin emisiones reales, la API devuelve vacío/no emitido honestamente.

Aceptación mínima:
- mismo target con distinta fecha/horizonte: IDs distintos;
- misma clave con otro modelo: emisión original preservada;
- idempotencia tras reinicio, nuevas lecturas y corrección posterior;
- dos procesos: una emisión o review, sin pérdida ni commit parcial;
- fallo antes/después del reemplazo: estado previo o nuevo completo;
- fallo de snapshot: no referencia rota publicada;
- reserva demo- en todos los estados y sin manifiesto; catálogo y GET permitidos;
- sensor sintético no demo- no bloqueado por procedencia;
- apertura UTC, review tardía sin vencimiento y madurez de entrenamiento intactas.

## 5. Estado y límites
Estas decisiones resuelven las dos dependencias de diseño. Sus pruebas e
implementación siguen pendientes. El manifiesto de calibración permanece DRAFT.
No se redefine la política de segunda revisión madura de HU5 ni se aprueban
tolerancias estadísticas. La advertencia canónica de archivado sigue pendiente.
