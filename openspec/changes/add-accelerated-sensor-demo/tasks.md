# Tareas — add-accelerated-sensor-demo

Estado: entrega 1 (preparación y worker CLI) implementada y verificada. Entregas
2-4 (control local, UI, verificación integrada) pendientes.

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

- [ ] 2.1 Lock de proceso, máquina de estados, revisión monotónica y deduplicación de órdenes de control.
- [ ] 2.2 Adaptador HTTP local para sesión preparada, start/pause/resume; GET sin efectos secundarios, validación de Origin y CORS configurado.
- [ ] 2.3 Recuperación por fase y payload: respuestas perdidas, caída antes/después de persistir, request aún en vuelo, resultado confirmado sin cursor avanzado y cambios externos. Bloquear incertidumbre no resuelta.
- [ ] 2.4 Pausa al terminar paso, intervalo entre pasos y continuación explícita tras reinicio. Probar dos clientes y dos workers.
- [ ] 2.5 Perfil Docker opcional `demo`, URL del backend fija por entorno, almacenamiento y README de preparación/ejecución; no modificar override del usuario ni activar demo en arranque normal.

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
