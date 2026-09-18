# Spec: demo-simulation

Capacidad implementada (Épica 3, HU6 — demostración dinámica acelerada de la integración; HU2/HU5 relacionadas como capacidades consumidas, no modificadas). Origen: `openspec/changes/add-accelerated-sensor-demo/`. Este documento es la fuente de verdad vigente de la capacidad; el *change* que la originó queda como registro histórico de la decisión, no se actualiza en paralelo a este archivo.

No es un simulador agronómico validado ni automatiza el riego: reproduce un período pasado sintético contra los endpoints reales de ingesta y pronóstico (`alerting-ui`) para mostrar cómo crecen el historial y los pronósticos registrados, un día calendario por paso. No mide capacidad predictiva ni sustenta conclusiones HU7/HU8; no modifica el módulo de aumento sintético de HU3, el protocolo experimental ni resultados históricos.

## Requirements

### Requirement: Preparación aislada y reproducible

La herramienta DEBE preparar explícitamente por CLI un sensor nuevo de demostración, un manifiesto y un prefijo histórico sintético suficiente, sin sobrescribir recursos.

#### Scenario: Preparar una sesión

- **GIVEN** fechas pasadas, semilla e historial válidos y contrato operativo disponible
- **WHEN** se prepara una sesión
- **THEN** se asigna un sensor exclusivo, se registra la configuración y solo se publica historia anterior al primer día de reproducción
- **AND** todos los registros son sintéticos y una colisión con recursos existentes se rechaza sin sobrescritura.

#### Scenario: Configuración inválida

- **GIVEN** fechas no pasadas, período vacío o contrato no disponible
- **WHEN** se solicita preparación
- **THEN** se rechaza con motivo y no se inicia un worker ni una corrida experimental.

Implementado en `scripts/demo_simulation/{config,cli,prepare,manifest,payload}.py` (entrega 1): `prepare` asigna un sensor `demo-<id>` aleatorio (no elegible por quien ejecuta el comando), escribe directamente el prefijo histórico sintético al almacenamiento del backend (acceso de escritura explícito, igual que `scripts/seed_mock_sensor_dataset.py`, ADR-0007) y rechaza la preparación si el sensor, su dataset o su feedback log ya existen. El horizonte de pronóstico se consulta al backend (`client.get_active_contract`) en vez de asumirse fijo. Testeado en `tests/demo_simulation/test_config.py`, `test_cli.py`, `test_manifest.py`, `test_prepare.py` contra un backend real (`uvicorn` en un hilo) y MLflow aislado en sqlite temporal. Verificado además en Docker Compose real (entrega 4, 2026-09-18): cinco sesiones preparadas (`demo-be97e84561`, `demo-d8a94926ce`, `demo-139b36b992`, `demo-aaf5c81e7f`, `demo-ae84b66085`) contra el backend en contenedor, cada una con su sensor exclusivo verificado por `GET /quality/{sensor_id}` desde el backend real.

**Nota operativa de esta entrega (no un defecto del código):** al montar el volumen `data/` manualmente con `docker compose --profile demo run -v ...` desde Git Bash en Windows, la conversión automática de rutas de MSYS puede corromper el argumento `-v host:contenedor` y dejar el historial preparado fuera del volumen esperado por el backend (el contenedor lo ve con 1 fila en vez de la historia completa, y la sesión queda `blocked` tras el primer paso). Se soluciona con `MSYS_NO_PATHCONV=1` antes del comando; no se detectó ninguna inconsistencia real entre `prepare` y el backend una vez corregido el montaje (confirmado con `docker exec` leyendo el parquet desde el propio contenedor del backend antes de cualquier ingesta).

### Requirement: Avance diario causal mediante la API real

Cada paso DEBE incorporar exactamente el siguiente día calendario, verificarlo y solicitar el pronóstico antes de avanzar. El dataset usado no DEBE contener días futuros.

#### Scenario: Completar varios días

- **GIVEN** sesión preparada con historia entrenable
- **WHEN** se ejecutan cinco pasos exitosos
- **THEN** se observan cinco fechas nuevas consecutivas de datos y cinco registros de pronóstico, cada uno solicitado antes de ingerir el día siguiente
- **AND** se conserva procedencia sintética, ET0 y fecha objetivo informada por el backend.

#### Scenario: Datos posteriores o fallo de pronóstico

- **GIVEN** un día ingerido
- **WHEN** se detecta una fecha posterior no autorizada o el pronóstico retorna error
- **THEN** se detiene el avance, se conserva el dato ya aceptado y se informa que no se confirmó el pronóstico
- **AND** no se inventa una alerta ni se alteran umbrales para continuar.

Implementado en `scripts/demo_simulation/{client,worker}.py` (entrega 1): secuencia ingesta (`POST /sensors/{sensor_id}/readings`) → verificación (`GET /quality/{sensor_id}`, sin días posteriores) → pronóstico (`POST /forecast/{sensor_id}/run`) → confirmación (`GET /feedback/{sensor_id}`). Testeado en `tests/demo_simulation/test_worker.py::test_five_consecutive_steps_complete_session` y `test_steps_are_causal_and_sequential`. Verificado con el contrato real de punta a punta (entrega 4, 2026-09-18) en dos sesiones completas de cinco días vía la UI (`demo-be97e84561`, `demo-d8a94926ce`, semilla 42, historial 120 días): `GET /feedback/{sensor_id}` devolvió cinco fechas consecutivas sin duplicados por sesión y `GET /quality/{sensor_id}` confirmó `duplicate_timestamps: []` y el total de filas esperado (historial + días reproducidos).

### Requirement: Pausa persistente y exclusión de ejecución

La herramienta DEBE mantener un único worker activo y persistir el cursor y fase. Pausar DEBE impedir el siguiente paso sin abandonar escrituras en curso.

#### Scenario: Pausar y continuar

- **GIVEN** un paso en curso
- **WHEN** se solicita pausa
- **THEN** el estado indica pausa solicitada hasta resolver el paso y luego queda pausado
- **AND** continuar comienza desde el primer paso incompleto, sin duplicar registros ni rebobinar.

#### Scenario: Clientes o procesos duplicados

- **GIVEN** una sesión activa y una orden ya aceptada
- **WHEN** otro proceso intenta tomarla o se repite el request de control
- **THEN** el lock impide otro worker y el request duplicado devuelve el resultado registrado; una revisión obsoleta recibe 409.

Implementado en `scripts/demo_simulation/lock.py` (`SessionLock`, `fcntl`/`msvcrt`, se libera solo si el proceso muere) y `control.py` (`_TRANSITIONS`, `handle_command`, `command_log` por `request_id`, `run_controlled_worker` — el chequeo de `pausing` ocurre solo entre pasos, nunca cancela un POST en vuelo) (entrega 2). Testeado en `tests/demo_simulation/test_control.py`. Verificado con el contrato real desde la UI (entrega 4, 2026-09-18, sesión `demo-d8a94926ce`, intervalo de 20s): pausa solicitada mientras el paso 1 estaba en curso → la UI mostró "Pausa solicitada — terminando el paso actual" → al terminar ese paso (cursor 1/5, un único registro en `GET /feedback`) pasó a "Pausada" sin iniciar el paso 2 → "Continuar" retomó desde el día 2 hasta completar los cinco días, sin duplicar registros. Se observó también, en uso real, una revisión obsoleta (409 "Revisión obsoleta") cuando el worker avanzó su propia revisión en segundo plano entre el último `GET` de la UI y el clic de pausa — la UI mostró el motivo sin aplicar la orden y sin fingir la pausa, exactamente el comportamiento no negociable documentado en `control.py`.

### Requirement: Recuperación conservadora de resultados inciertos

La herramienta DEBE persistir la intención antes de cada POST y reconciliar sus efectos antes de repetirlo. Un timeout no DEBE interpretarse como cancelación.

#### Scenario: Respuesta perdida con efecto comprobado

- **GIVEN** payload o pronóstico pendiente en el manifiesto, con request anterior terminado
- **WHEN** la lectura del estado persistido confirma el efecto esperado
- **THEN** se recupera el mismo registro, sin POST duplicado, y se conserva la secuencia.

#### Scenario: Reinicio con operación incierta

- **GIVEN** un reinicio o desconexión sin prueba de que el POST anterior terminó
- **WHEN** se intenta continuar
- **THEN** la sesión queda bloqueada y se explica la incertidumbre; no reintenta escrituras ni avanza automáticamente.

Implementado en `scripts/demo_simulation/recovery.py` (`diagnose_and_recover`, `_detect_external_change`, entrega 2): invocado al levantar `serve` y dentro de `resume` sobre una sesión `blocked`; la ingesta se considera segura de reintentar por su semántica de reemplazo por día, el pronóstico (no idempotente) solo se reconcilia por lectura (`GET /feedback`), nunca se reenvía. Testeado en `tests/demo_simulation/test_control.py` (reconciliación sin reenvío, bloqueo por incertidumbre, detección de cambio externo). Verificado con un caso real durante esta entrega (2026-09-18): un montaje de volumen incorrecto (ver nota operativa arriba) dejó el dataset de una sesión de prueba con menos filas de las esperadas tras ingerir; el worker lo detectó, bloqueó la sesión con el motivo exacto ("El dataset tiene 1 filas tras ingerir ...; se esperaban ...") y `resume` reintentó la reconciliación sin sobrescribir ni borrar nada, permaneciendo bloqueada hasta corregir la causa real (no un bug de reconciliación).

### Requirement: Separación de demostración y evidencia científica

La herramienta DEBE conservar modelos, datos, feedback y manifiestos de demo identificables y separados de sensores existentes y artefactos experimentales.

#### Scenario: Finalizar la sesión

- **GIVEN** todos los pasos confirmados
- **WHEN** termina la reproducción
- **THEN** se preservan los registros como demostración sintética y no se calculan conclusiones de desempeño ni métricas HU7/HU8
- **AND** no se modifica el módulo de aumento sintético, el protocolo ni resultados históricos.

Todo dataset/feedback/manifiesto de demo usa el prefijo `demo-<id>` (`data_ingestion.sensor_naming`), separado por construcción de `sensor-a` y de los datasets históricos formales de HU7/HU8. `data/sensor__demo-*.parquet`, `data/feedback__demo-*.parquet` y `demo_sessions/` están excluidos de control de versiones (`.gitignore`). Verificado en esta entrega (2026-09-18): cinco sesiones de demostración completas se conservan en `data/`/`demo_sessions/` como evidencia de la verificación integrada, sin haber tocado `sensor-a` ni ningún dataset del usuario; no se borraron automáticamente.

### Requirement: Adaptador HTTP local de control opcional

El sistema DEBE ofrecer un adaptador HTTP local opcional (perfil Docker `demo`) que controle una sesión ya preparada por CLI —inicio, pausa, continuación y consulta de estado—, sin exponer una operación de preparación por HTTP ni permitir reconfigurar el backend de destino desde una request.

#### Scenario: Consultar y controlar por HTTP

- **GIVEN** una sesión preparada y el servicio de control levantado
- **WHEN** se consulta `GET /demo/session` o se envía `POST /demo/session/{start,pause,resume}`
- **THEN** `GET` nunca crea, inicia ni avanza nada; las órdenes de control validan `Origin`, deduplican por `request_id` y rechazan revisión obsoleta o transición inválida con 409

Implementado en `scripts/demo_simulation/service.py` (FastAPI, entrega 2): `CORSMiddleware` más middleware propio de validación de `Origin` en mutaciones, enlazado a loopback (`127.0.0.1:8010`) fuera del perfil Docker `demo`. Testeado en `tests/demo_simulation/test_service.py` contra un backend real servido por `uvicorn`. Verificado con el contrato real desde la UI en cinco sesiones distintas (entrega 4, 2026-09-18) y confirmado por los logs de acceso del contenedor que la navegación, el refresco y el polling periódico solo generan `GET /demo/session` — un único `POST` por acción explícita del usuario (Iniciar/Pausar/Continuar), nunca por cargar o refrescar la página.

## Interfaz de usuario

La vista de demostración, sus controles, el bloqueo de mutaciones manuales del sensor de demo y la habilitación de revisión humana posterior a la reproducción son requirements de `alerting-ui` (ver `openspec/specs/alerting-ui/spec.md`, sección agregada por esta misma HU6): esta capacidad expone el contrato HTTP y el worker; `alerting-ui` lo consume.

## Limitaciones conocidas

- El generador (`data_ingestion.mock_sensor`) es un random walk acotado, no un modelo físico de cultivo: no garantiza estacionalidad, balance hídrico ni escenarios de secado/lluvia realistas. Con la semilla de referencia (42) las cinco sesiones verificadas en esta entrega generaron alerta en los cinco días de cada corrida — no se buscó ni se exigió una mezcla de alertas y resultados sin alerta, ni se ajustó la semilla para obtenerla (instrucción explícita del change).
- No hay garantía de ejecución única del modelo o del pronóstico ante una pérdida de respuesta HTTP: el backend/MLflow subyacentes no ofrecen una clave de idempotencia. El requisito es no duplicar registros ni avanzar sin confirmación (recuperación conservadora, con bloqueo explícito ante incertidumbre), nunca una garantía exactamente-una-vez sobre la ejecución interna del modelo.
- La exclusión de proceso (`SessionLock`) protege contra dos workers de esta herramienta (CLI directa o adaptador HTTP) sobre la misma sesión; no excluye a otros clientes HTTP externos que operen directamente contra el backend con el mismo `sensor_id` de demostración.
- El perfil Docker `demo` no fue verificado con el stack de Compose completo levantado por `docker compose --profile demo up` de punta a punta con volúmenes por defecto; en esta entrega se verificó controlando sesiones reales con el servicio levantado por Compose, pero preparando cada sesión con un montaje adicional de `data/` vía `docker compose --profile demo run -v` (ver nota operativa de MSYS arriba) en vez del flujo documentado en el README paso a paso. El comportamiento del contrato en sí (lock, máquina de estados, recuperación, adaptador HTTP) quedó verificado igual contra el backend y MLflow reales.
- Viewport móvil real y navegación exclusivamente por teclado sobre la vista de demostración: ver limitación equivalente documentada en `openspec/specs/alerting-ui/spec.md`.
