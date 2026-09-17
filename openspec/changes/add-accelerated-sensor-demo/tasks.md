# Tareas — add-accelerated-sensor-demo

Estado: entregas 1 (preparación y worker CLI) y 2 (control local y
recuperación) implementadas y verificadas. Entregas 3-4 (UI, verificación
integrada) pendientes.

## 0. Decisión y preparación

- [x] 0.1 Revisar el ADR-0012 propuesto y aceptar o ajustar explícitamente el proceso local auxiliar antes de implementarlo. Aceptado vía PR #201 (ver `docs/adr/0012-controlador-local-demo-acelerada.md`, sección Estado); la decisión de arquitectura queda aceptada, no su implementación.
- [x] 0.2 Fijar fixtures de datos y contrato para tests, carpetas temporales y registro de modelos aislado. Definir una sesión de demostración reproducible sin elegirla por las alertas obtenidas. Ver `tests/demo_simulation/conftest.py` (`live_backend`: backend real por `uvicorn` en hilo sobre `tmp_path`, registro MLflow en sqlite temporal; `reference_session_kwargs`: sesión fija de 5 días/120 de historial/semilla 42, documentada como no ajustada por resultado).

## 1. Preparación y worker CLI

- [x] 1.1 Crear paquete de herramientas y CLI; validar fechas, horizonte, parámetros y sensor exclusivo sin sobrescritura. `scripts/demo_simulation/{config,cli}.py`; `tests/demo_simulation/test_config.py`, `test_cli.py`.
- [x] 1.2 Implementar manifiesto atómico y preparación del prefijo histórico con procedencia sintética. No publicar días de reproducción anticipadamente. `scripts/demo_simulation/{manifest,prepare}.py`; `tests/demo_simulation/test_manifest.py`, `test_prepare.py`.
- [x] 1.3 Construir payload completo con ET0 usando el generador existente y semilla por día; test de continuidad y reproducción. `scripts/demo_simulation/payload.py`; `tests/demo_simulation/test_payload.py`.
- [x] 1.4 Implementar secuencia ingesta → verificación → pronóstico → GET de confirmación, registrando intención/fase y deteniendo el avance ante fallo. `scripts/demo_simulation/{client,worker}.py`.
- [x] 1.5 Verificar cinco pasos con API real en entorno temporal y dobles del registro declarados: orden HTTP, cinco nuevas fechas, ninguna lectura futura y resultados fieles a la API. `tests/demo_simulation/test_worker.py::test_five_consecutive_steps_complete_session` y `test_steps_are_causal_and_sequential`, contra backend real (`uvicorn`) y MLflow sqlite temporal.
- [x] 1.6 Verificar preservación de archivos centinela de sensores ajenos y evidencia histórica. Sin consultas de datos científicos para producir los fixtures. `test_prepare.py::test_prepare_leaves_other_sensor_files_untouched`, `test_worker.py::test_run_preserves_sentinel_files_of_other_sensors`; historial de fixtures generado íntegramente por `data_ingestion.mock_sensor`, nunca leído de datasets científicos.

## 2. Control y recuperación — depende de 1

- [x] 2.1 Lock de proceso, máquina de estados, revisión monotónica y deduplicación de órdenes de control. `scripts/demo_simulation/lock.py` (`SessionLock`, `fcntl`/`msvcrt`, se libera si el proceso muere); `scripts/demo_simulation/control.py` (`_TRANSITIONS`, `handle_command`, `command_log` por `request_id`); `manifest.py` agrega `pausing`/`paused` y `command_log`. Tests: `test_control.py::test_lock_prevents_two_workers`, `test_duplicate_request_id_returns_same_result_and_launches_worker_once`, `test_stale_revision_is_rejected_explicitly`, `test_invalid_transition_is_rejected`, `test_session_mismatch_is_rejected`.
- [x] 2.2 Adaptador HTTP local para sesión preparada, start/pause/resume; GET sin efectos secundarios, validación de Origin y CORS configurado. `scripts/demo_simulation/service.py` (FastAPI, `CORSMiddleware` + middleware propio de validación de `Origin` en mutaciones). No agrega preparación por HTTP (ADR-0007/0012). Tests: `test_service.py::test_get_session_is_read_only`, `test_get_session_missing_returns_404_without_creating_anything`, `test_duplicate_start_request_is_idempotent_over_http`, `test_stale_revision_rejected_over_http`, `test_unauthorized_origin_is_rejected_on_mutating_request`, `test_get_is_not_blocked_by_origin_validation`, `test_backend_url_cannot_be_overridden_from_the_request`, `test_start_launches_worker_and_get_reflects_progress`.
- [x] 2.3 Recuperación por fase y payload: respuestas perdidas, caída antes/después de persistir, request aún en vuelo, resultado confirmado sin cursor avanzado y cambios externos. Bloquear incertidumbre no resuelta. `scripts/demo_simulation/recovery.py` (`diagnose_and_recover`, `_detect_external_change`): ingesta idempotente por reemplazo de día → segura de reintentar; pronóstico no idempotente → solo se reconcilia por lectura (`GET /feedback`), nunca se reenvía. Tests: `test_recovery_reconciles_confirmed_forecast_without_reposting`, `test_recovery_blocks_when_forecast_cannot_be_confirmed`, `test_recovery_detects_external_change_and_blocks_without_overwriting`.
- [x] 2.4 Pausa al terminar paso, intervalo entre pasos y continuación explícita tras reinicio. Probar dos clientes y dos workers. `control.run_controlled_worker` (chequeo de `pausing` solo entre pasos, nunca cancela un POST en vuelo) y `WorkerSupervisor` (dedup de hilo por sesión). Tests: `test_pause_completes_current_step_before_stopping` (1 `skip` documentado por temporización, ver README), `test_resume_continues_from_first_incomplete_step`, `test_run_controlled_worker_noop_when_lock_held_elsewhere` (segundo worker no toca la sesión ajena), `test_duplicate_request_id_...` (dos "clientes" con el mismo `request_id`).
- [x] 2.5 Perfil Docker opcional `demo`, URL del backend fija por entorno, almacenamiento y README de preparación/ejecución; no modificar override del usuario ni activar demo en arranque normal. `docker-compose.yml` (`profiles: ["demo"]`, puerto enlazado a `127.0.0.1`), `docker/demo-control/Dockerfile`. Verificado: `docker build`, `docker compose --profile demo config` (aparece solo con el perfil) y `docker compose config`/`up --dry-run` sin el perfil (no rompe, no requiere `DEMO_SESSION_ID`). No se tocó `docker-compose.override.yml`. Documentación de preparación/arranque/pausa/continuación/diagnóstico en `scripts/demo_simulation/README.md`.

## 3. UI — depende de 2

- [ ] 3.1 Vista secundaria con rótulo de simulación, sensor, fecha, progreso e iniciar/pausar/continuar; no crear sesión desde HTTP.
- [ ] 3.2 Polling sin solapamiento, refresco GET por revisión, descarte de respuestas obsoletas, conservación de filtros y recuperación al volver a pestaña.
- [ ] 3.3 Bloquear mutaciones manuales del sensor demo antes de completar; conservar consulta de otros sensores y comunicar que cerrar pestaña no pausa.
- [ ] 3.4 Al completar, habilitar revisión solo de objetivos observables y mantener los errores del backend. No cambiar el reloj ni fabricar feedback.
- [ ] 3.5 Tests UI de estados, navegación sin POST, pausa pendiente, desconexión, finalización, última fecha sin objetivo y doble clic en controles.

## 4. Verificación y documentación — depende de 3

- [ ] 4.1 Ejecutar tests afectados de herramientas/backend/frontend, lint/formato Python según repo, `npm test`, `npm run lint`, `npm run build`.
- [ ] 4.2 Integración local sobre sensor nuevo: preparar → iniciar → pausar → continuar → completar al menos cinco días; revisar manualmente una fila con objetivo observable. Registrar valores reales sin exigir mezcla de clases.
- [ ] 4.3 Inspección en navegador escritorio/móvil y teclado; capturas identificadas como demo. Diferenciar evidencia con fixtures de API/registro reales.
- [ ] 4.4 Registrar recursos creados y posibles fallos; no borrar automáticamente datasets ni versiones. Probar que UI sin perfil demo continúa funcionando.
- [ ] 4.5 Consolidar únicamente capacidades implementadas en specs canónicas y actualizar seguimiento/diseño/README con HU6, relación HU2/HU5, capítulo 3 e impacto nulo HU7/HU8.

## Cobertura de requisitos

| Requisito | Tareas |
|---|---|
| Preparación aislada y reproducible | 1.1–1.3, 1.6 |
| Avance diario causal mediante la API real | 1.4–1.5 |
| Pausa persistente y exclusión de ejecución | 2.1, 2.4 |
| Recuperación conservadora de resultados inciertos | 2.3 |
| Separación de demostración y evidencia científica | 1.6, 4.2–4.5 |
| Control explícito de demostración opcional | 2.2, 2.5, 3.1, 3.5 |
| Refresco por progreso confirmado | 3.2, 3.5 |
| Revisión humana posterior a la reproducción | 3.3–3.5, 4.2 |

## Cierre

- [ ] Todos los escenarios tienen evidencia y no se declara exactamente-una-vez sobre APIs que no lo garantizan.
- [ ] Ningún cambio en protocolos, aumento sintético HU3, resultados científicos ni datasets existentes del usuario.
- [ ] Límites del mock, exclusión frente a clientes externos y verificaciones pendientes declarados; no se afirma validación agronómica o productiva.
