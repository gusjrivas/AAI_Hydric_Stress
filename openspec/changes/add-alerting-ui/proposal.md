# Change: Add alerting UI capability

## Trazabilidad

- **Épica:** 3. Integración y mejora.
- **Historias de usuario:** HU5 (mecanismo de retroalimentación humana) + HU6 (integración de la arquitectura experimental) — primera exposición de ambas capacidades a través de una interfaz de usuario real, tal como anticipaba ADR-0003 ("antes de implementar HU5... debe crearse el scaffolding real de `backend/` y `frontend/`").
- **Fase de CRISP-DM:** Despliegue.
- **Insumo de diseño:** [ADR-0003](../../../docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md) (stack FastAPI + React, fachada delgada), [`openspec/specs/architecture-integration/spec.md`](../../specs/architecture-integration/spec.md) (orquestador), [`openspec/specs/human-feedback/spec.md`](../../specs/human-feedback/spec.md) (registro de retroalimentación).

## Why

HU1-HU8 dejaron un pipeline completo, probado y ejecutado de punta a punta (ingesta → calidad → modelado → alertas → retroalimentación → recalibración → evaluación experimental), pero solo accesible por scripts de línea de comandos y notebooks. No hay todavía ninguna forma de que un usuario humano corra un pronóstico, vea las alertas generadas, y las valide, sin escribir Python. Esta es la primera prueba básica de esa interfaz — un escalón hacia la arquitectura final que el usuario ya adelantó: múltiples modelos combinados en un solo veredicto, e ingesta de datos de sensores en vivo (ambas explícitamente fuera de alcance de este *change*, ver más abajo).

## What Changes

- **Backend** (`backend/`, FastAPI, fachada delgada sobre `src/`, según ADR-0003):
  - `POST /forecast/run`: carga el dataset consolidado (nombre configurable por variable de entorno, no hardcodeado, para no acoplar la ruta a un dataset fijo cuando exista una fuente de datos en vivo), entrena un modelo Random Forest (configuración base, semilla fija) vía `architecture_integration.pipeline.run_end_to_end_pipeline`, genera alertas, combina (`human_feedback.registry.upsert_feedback_log`) con el feedback ya persistido, lo guarda, y devuelve solo el veredicto por fecha (alerta sí/no, probabilidad) — **sin mencionar qué modelo lo generó**, para que el contrato de la API ya sea compatible con un futuro motor de selección/ensamble entre varios modelos, sin tener que romper el contrato después.
  - `GET /feedback`: devuelve el registro de retroalimentación persistido.
  - `POST /feedback/{fecha}/confirm`: confirma una alerta.
  - `POST /feedback/{fecha}/reject`: rechaza una alerta con `etiqueta_corregida` y `observacion`.
- **Frontend** (`frontend/`, Vite + React + TypeScript, según ADR-0003 y la skill `frontend-react`): una página con un botón para correr el pronóstico y una tabla de alertas (fecha, probabilidad, estado de validación), con acciones de confirmar/rechazar por fila.
- **Persistencia**: el feedback se guarda a disco tras cada validación (`human_feedback.registry.save_feedback_log`), sobrevive a reinicios del backend — mismo contrato de datos que el resto del repo (ADR-0002).

## Impact

- **Specs afectadas:** nueva capacidad `alerting-ui`.
- **Código afectado:** nuevo `backend/` (FastAPI) y `frontend/` (Vite+React+TS) — primer código de ambas carpetas en el repo.
- **Fuera de alcance de este change** (explícitamente, para no expandir esta prueba básica sin diseño propio):
  - **Motor de selección/ensamble entre varios modelos**: hoy el pipeline usa un único modelo fijo (Random Forest); combinar varios modelos en un solo veredicto es una pieza de diseño propia, a abordar en una iteración futura. El contrato de la API ya está preparado para no tener que cambiar cuando eso se implemente.
  - **Ingesta de datos de sensores en vivo**: fuente de datos distinta de la ingesta histórica/batch de HU2 (NASA POWER, ESA CCI); requiere su propio diseño (validación de esquema, frecuencia, endpoints de captura).
  - **Disparo de recalibración desde la UI**: el mecanismo (`human_feedback.recalibration`) ya existe (HU5) pero conectarlo a un botón de la interfaz queda para después de que esta base funcione.
  - **Robustez ante escasez y ruido de datos en producción**: HU8 ya generó evidencia real sobre ambos escenarios (`docs/research/hu8-analisis-resultados.md`) — la próxima iteración de esta arquitectura debe partir de esa evidencia, no es parte de este *change*.

## Alternativas consideradas

- **Un único endpoint de feedback con el estado como parámetro** (en vez de `/confirm` y `/reject` separados): se descarta porque no reduce complejidad real — cada endpoint separado es una función de una sola responsabilidad, más simple de leer y testear que una rama condicional según el estado recibido.
- **Cachear el modelo entrenado en memoria del proceso**: se descarta para esta iteración porque agrega estado mutable al backend (dataset chico, entrena en segundos; no hay necesidad de esa optimización todavía).
- **Registrar cada corrida de la UI en MLflow**: se descarta por ahora — esta UI es una demo operativa de HU5/HU6, no un experimento de investigación de la Épica 4 (HU7); acoplarla a que Docker Desktop esté levantado no aporta valor a este alcance.
- **Permitir subir un dataset propio desde la UI**: se descarta para esta iteración; se usa el dataset real ya consolidado y versionado en el repo, evitando la complejidad de validación de esquema de un archivo subido por el usuario.
- **Nombre de dataset hardcodeado en la ruta**: se descarta explícitamente (aunque sería más simple) porque acoplaría el backend a un dataset fijo justo cuando se sabe que una fuente de datos en vivo (sensores) va a reemplazarlo — se usa una variable de entorno con el dataset actual como valor por defecto.

## Estado: implementado

Ver [`openspec/specs/alerting-ui/spec.md`](../../specs/alerting-ui/spec.md) para los requisitos vigentes y la verificación end-to-end real.
