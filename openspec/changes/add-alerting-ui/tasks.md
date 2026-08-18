# Tareas — add-alerting-ui

Primer scaffolding de `backend/` y `frontend/` (ADR-0003), exponiendo HU5 (retroalimentación) y HU6 (pipeline completo) a través de una interfaz de usuario.

- [ ] Scaffolding de `backend/` (FastAPI) con configuración de dataset por variable de entorno.
- [ ] Endpoint `POST /forecast/run`.
- [ ] Endpoints `GET /feedback`, `POST /feedback/{fecha}/confirm`, `POST /feedback/{fecha}/reject`.
- [ ] Tests de backend con `TestClient` contra la app real, `data_dir` temporal inyectado.
- [ ] Scaffolding de `frontend/` (Vite + React + TypeScript).
- [ ] Página de pronóstico y alertas (botón de correr pronóstico, tabla, acciones confirmar/rechazar).
- [ ] Tests de frontend con React Testing Library + Vitest.
- [ ] Verificación manual end-to-end (backend + frontend corriendo, navegador) con el dataset real.
- [ ] Actualizar CI (`.github/workflows/ci.yml`) con jobs acotados a `backend/`/`frontend/`, sin modificar el job de Python existente (ADR-0003).
- [ ] Actualizar `docs/seguimiento-tareas.md` y las specs vigentes (`architecture-integration`, `human-feedback`, nueva `alerting-ui`).
