# Tareas — improve-alerting-ui-decision-workflow

Estado: especificado, no implementado. Cada entrega conserva los contratos actuales
y añade evidencia de sus escenarios antes de marcar tareas completas.

## 1. Flujos confiables — primera entrega

Estado: implementada y verificada (ver evidencia por tarea). Rama
`feat/alerting-ui-reliable-flows`, PR contra `main` referenciando HU6/HU5.

- [x] 1.1 Separar sensor borrador/activo en la cabecera, validación asociada y aplicación explícita. Cubrir edición sin consultas y respuesta tardía A→B. — `frontend/src/App.tsx`; tests en `frontend/src/App.test.tsx`.
- [x] 1.2 Extraer estado compartido de historial y operación; cargar `GET /feedback` al activar sensor. Distinguir 404, error y datos incompletos; ordenar por fecha sin descartar filas sin probabilidad. — `frontend/src/features/forecast/useForecastWorkspace.ts`; tests en `frontend/src/features/forecast/ForecastPage.test.tsx`.
- [x] 1.3 Incorporar bloqueo compartido de mutaciones, progreso local, errores de fila y protección frente a respuestas obsoletas. No reintentar POST automáticamente. — `useForecastWorkspace.ts` (`activeMutation`, `rowErrors`, comparación contra el sensor activo); sin reintento automático de POST.
- [x] 1.4 Separar éxito del POST de fallos de refresco. Reconciliar resultado por fecha y ofrecer GET ante resultado de escritura incierto. — `useForecastWorkspace.ts` (`upsertVerdicts`, `refreshPending`, distinción `HttpError` vs. fallo de red).
- [x] 1.5 Tests de integración App/Forecast: consulta sin POST, cambio de sensor, 404 frente a 500, doble clic, dos filas, pronóstico frente a recalibración y fallo de GET posterior a éxito. — `frontend/src/App.test.tsx`, `frontend/src/features/forecast/ForecastPage.test.tsx` (43 tests, `npm test`/`npm run lint`/`npm run build` verdes).

**Salida:** consultar y confirmar historial existente sin generar un pronóstico nuevo,
sin mezclar sensores ni permitir escrituras superpuestas desde esta UI.

**Limitaciones de esta entrega:** verificación en navegador realizada sin backend
levantado (falla de red uniforme en los tres paneles, sin datos reales de la API);
no se corrió una integración real contra `backend/`. Los escenarios de filtrado de
historial, navegación por destinos, corrección humana explícita y diseño/accesibilidad
quedan fuera de esta entrega (Entregas 2 a 4).

## 2. Navegación y resumen — depende de 1

Estado: implementada y verificada (ver evidencia por tarea). Rama
`feat/alerting-ui-navigation-summary`, PR contra `main` referenciando HU6/HU5.

- [x] 2.1 Implementar cinco destinos por hash, compatibilidad de anchors existentes, Atrás/Adelante, título, foco y destino activo. — `frontend/src/features/navigation/useHashRoute.ts`, `DestinationNav.tsx`, cableado en `App.tsx`; tests en `frontend/src/App.test.tsx` (describe "navegación por hash").
- [x] 2.2 Construir Resumen: último pronóstico registrado, fechas diferenciadas, pendientes de revisión y contexto de calidad. Estados vacíos y parciales explícitos. — `frontend/src/features/summary/ResumenView.tsx`; tests en `ResumenView.test.tsx`.
- [x] 2.3 Agregar filtros de alerta, validación y rango de referencia; limpiar filtros, orden descendente y contadores generales independientes del filtro. — `frontend/src/features/forecast/ForecastPage.tsx` (`fieldset` de filtros); tests en `ForecastPage.test.tsx` (describe "filtros de historial").
- [x] 2.4 Reubicar arquitectura/evidencia y predictor/linaje manteniendo contenido y procedencia; desplegar detalles técnicos sin retirarlos. — `ArchitectureFlow`/`EvidencePanel` bajo el destino "evidencia"; `ActivePredictorSummary`/`LineageChain` bajo "linaje", ambos en `App.tsx`. Contenido y provenance sin cambios, solo reubicados.
- [x] 2.5 Tests de navegación, conservación de contexto, selección del último registro, fechas calendario sin desplazamiento y filtros sin coincidencias. — `App.test.tsx`, `ResumenView.test.tsx`, `ForecastPage.test.tsx` (57 tests totales, `npm test`/`npm run lint`/`npm run build` verdes).

**Salida:** acceso directo al pronóstico y su revisión, con recorrido de defensa disponible.

**Limitaciones de esta entrega:** verificación en navegador con Claude in Chrome
realizada sin backend levantado (misma limitación de la Entrega 1); confirmé
navegación por hash, foco de encabezado, título de documento, Atrás/Adelante,
compatibilidad de anchors y navegación por teclado (Tab + Enter) en escritorio.
No pude verificar visualmente el layout en un viewport móvil real: la
herramienta de redimensionado de ventana del navegador no tuvo efecto en este
entorno (`window.innerWidth` permaneció en 1864px pese a pedir 390×844) — el
diseño responsive de esta entrega (`ResumenView` en columna única por defecto,
fila solo desde `min-width: 900px`; nav con `flex-wrap`) se apoya en las reglas
CSS ya escritas y en la revisión de código, no en una captura móvil real.
Capturas de escritorio adjuntas en el PR para Resumen y Alertas y revisión.

## 3. Revisión humana y trazabilidad — depende de 1 y 2

Estado: implementada y verificada (ver evidencia por tarea). Rama
`feat/alerting-ui-human-review-traceability`, PR contra `main` referenciando HU6/HU5.

- [x] 3.1 Formulario inline de corrección con etiqueta explícita, observación editable, cancelar sin POST y recuperación del foco. — `frontend/src/features/forecast/CorrectionForm.tsx`, cableado en `ForecastPage.tsx` (ref por fila para devolver el foco); tests en `ForecastPage.test.tsx` (describe "corrección inline").
- [x] 3.2 Mostrar motivos de 409 junto a la fila conservando el formulario; mantener mensaje de que guardar feedback no reentrena. — `CorrectionForm.tsx` (`serverError` desde `workspace.rowErrors[fecha]`, formulario no se cierra en error); `useForecastWorkspace.ts` (mensaje "Validación guardada... el modelo no se actualizó").
- [x] 3.3 Sustituir el contador engañoso de pendientes por correcciones registradas y fechas incorporadas, con desconocido si falta metadata. No inferir elegibilidad ni incorporación de ediciones posteriores. — `frontend/src/features/forecast/RecalibrationPanel.tsx` (consulta independiente de `GET /models/{sensor_id}/active`, estado `unknown` ante fallo); `ForecastPage.tsx` ya no muestra "Correcciones sin incorporar a la recalibración".
- [x] 3.4 Ubicar recalibración manual en Modelo y trazabilidad, refrescar predictor/linaje tras éxito y preservar el historial. — `RecalibrationPanel.tsx` montado en `App.tsx` bajo `#linaje`, junto a `ActivePredictorSummary`/`LineageChain`; `predictorRefreshToken`/`lineageRefreshToken` se incrementan tras éxito (`handleRecalibrated`); el historial de `Alertas y revisión` no se toca.
- [x] 3.5 Tests de payload de corrección, cancelación, etiqueta igual a original, 409, metadata ausente, fecha ya incorporada y recalibración sin correcciones elegibles. — `ForecastPage.test.tsx`, `RecalibrationPanel.test.tsx`, `App.test.tsx` (66 tests totales, `npm test`/`npm run lint`/`npm run build` verdes).

**Salida:** feedback explícito y estado fiel a los contratos existentes, sin cambios temporales.

**Limitaciones de esta entrega:** verificación en navegador con Claude in Chrome
usando un `fetch` interceptado en el propio navegador (sin backend real levantado)
para poder ejercitar el formulario de corrección, el 409, el guardado exitoso y
la recalibración con datos realistas — confirmé apertura sin escritura, la
orientación a Confirmar ante la misma etiqueta, el 409 junto a la fila con el
formulario conservado, el guardado exitoso con foco y badge actualizados, y el
mensaje de recalibración en Modelo y trazabilidad (se detectó y corrigió en el
camino que ese mensaje no se mostraba ahí antes de moverse el botón). Esto usa
mocks de red controlados por mí en la consola del navegador, no una integración
real contra `backend/`. No pude verificar visualmente un viewport móvil real
(misma limitación de las Entregas 1 y 2: `resize_window` no tuvo efecto en este
entorno). Capturas adjuntas en el PR.

## 4. Diseño coherente y verificación — depende de 2 y 3

Estado: **parcialmente implementada**. Rama `feat/alerting-ui-design-verification`,
PR contra `main` referenciando HU6/HU5, **abierto como draft**: 4.3, 4.5 y 4.6
quedan pendientes por una limitación de entorno (ver abajo), no por falta de
intención. No se declara terminada esta entrega ni el *change* completo.

- [x] 4.1 Centralizar tokens, tema claro, tipografía y estados; retirar estilos globales heredados incompatibles y layout de página anidado. — `frontend/src/index.css` (tokens `--color-*`/`--space-*`/`--font-*` únicos; se eliminó el boilerplate de `create-vite` con acento violeta y una declaración `@media (prefers-color-scheme: dark)` que sí alteraba `--bg`/`--text` del documento aunque ningún componente propio la usara — el "tema oscuro parcial" que `design.md` pedía retirar); `.fp-page`/`.app-page` ya no duplican `min-height:100vh`+padding (layout de página anidado); estado de revisión (pendiente/confirmada/rechazada) separado en paleta propia — confirmar ya no pinta de verde. Detalle en `docs/design/alerting-ui-visual-design.md`.
- [x] 4.2 Ajustar escritorio/móvil, formularios, navegación, estados de carga/error/vacío y mensajes accesibles. — Reglas responsive existentes revisadas y mantenidas (`flex-wrap` en filtros/nav, columna única por defecto en `ResumenView`, colapso de `.fp-row` a `max-width:640px`); controles principales con `min-height:44px`. Verificado en escritorio real (~1864 px); **el ajuste móvil se apoya en revisión de código, no en una captura real** (ver limitaciones).
- [ ] 4.3 Verificar teclado completo, foco, contraste WCAG 2.2 AA, reflow y zoom según `design.md`; documentar hallazgos y corregirlos. — **Parcial.** Contraste: medido por cálculo (fórmula de luminancia relativa de WCAG), no solo inspección visual — encontré y corregí un par real por debajo de 4.5:1 (badge "rechazada" antes del rediseño de paleta de revisión) y reforcé bordes de controles interactivos a ≥3:1; tabla completa en `docs/design/alerting-ui-visual-design.md`. Foco: agregado enlace "Saltar al contenido" y región de scroll por teclado en la tabla de evidencia; el salto de foco tras navegar se reconfirmó por consulta directa de `document.activeElement`. Teclado: el trazado manual de Tab en esta sesión de automatización dio resultados inconsistentes entre intentos (atribuible a la herramienta, no reproducido de forma confiable) — se verificó en cambio el orden de foco por inspección directa del DOM y por los tests existentes que ejercitan foco programático. **Reflow a 320 CSS px y zoom 200% no se pudieron verificar**: sin acceso a redimensionado de viewport real en este entorno (ver limitaciones). Pendiente para quien retome esta rama con un navegador real.
- [x] 4.4 Ejecutar en `frontend/`: `npm test`, `npm run lint`, `npm run build`. No sustituir inspección visual por tests de jsdom. — 68 tests en verde, `npm run lint` sin hallazgos, `npm run build` correcto. La verificación visual en navegador (ver 4.2/4.3/4.5) se hizo aparte, no en reemplazo de esto.
- [ ] 4.5 Revisar en navegador a 360/768/1440 px y 320 CSS px: vacío, error, historial extenso, alerta/sin alerta, guardado, 409, recalibración y linaje fallido. Usar fixtures identificados o sensor de prueba aislado; nunca datos experimentales históricos para escrituras de QA. — **Parcial.** Todos los estados listados (vacío/404, error/500, historial extenso de 18 filas, alerta/sin alerta mezclados, guardado exitoso, 409 con formulario conservado, recalibración exitosa, fallo de integridad de linaje) se revisaron y capturaron, pero solo en el ancho de escritorio disponible en este entorno (~1864 px) — **no en 360/768/1440/320 px reales**, por la misma limitación de redimensionado. Datos vía `fetch` interceptado en el navegador con un sensor de prueba sintético (`sensor-qa`), nunca el dataset histórico real.
- [ ] 4.6 Registrar evidencia de consulta/revisión/lectura de linaje con teclado y móvil; distinguir pruebas con fixtures de integración real. Verificar que consultar y navegar no generan POST. — **Parcial.** "Consultar y navegar no generan POST" ya está cubierto por tests existentes (`App.test.tsx`: el conteo de `listFeedback`/`runForecast` no aumenta al navegar entre destinos ni al volver a Resumen) y se reconfirmó de forma manual. La evidencia por **teclado** de consulta/revisión/linaje es parcial (ver 4.3); la evidencia **móvil** no se pudo producir (ver limitaciones). Fixtures y mocks distinguidos de integración real en todo momento (nunca hubo integración real disponible en esta rama).
- [x] 4.7 Actualizar `docs/design/alerting-ui-visual-design.md`, `docs/seguimiento-tareas.md` y spec canónica únicamente con lo efectivamente implementado. Registrar impacto nulo HU7/HU8 y aporte al capítulo 3. — Los tres documentos actualizados (ver PR). Impacto nulo sobre HU7/HU8: ningún cambio toca `src/`, protocolos, configuraciones experimentales ni resultados históricos — solo `frontend/`. Aporte al capítulo 3 (arquitectura e implementación) de la memoria técnica: consolidación del sistema de diseño y de la accesibilidad de la interfaz de decisión, sin afectar metodología ni evidencia científica.

**Limitación de entorno, declarada explícitamente (afecta 4.3, 4.5 y 4.6):**
la herramienta de redimensionado de ventana del navegador no tuvo efecto en
esta sesión de automatización en ninguna de las cuatro entregas de este
*change* (`window.innerWidth` no cambia pese a pedir 375×812, 390×844 o
320 px). No hay integración real contra `backend/` en ninguna entrega. El
trazado manual de Tab por teclado fue inconsistente entre intentos en esta
sesión — no se reporta como verificado con confianza, aunque el orden de
foco correcto sí se confirmó por inspección del DOM. Estas tres tareas
quedan **pendientes**, no marcadas como completas, y el PR de esta entrega se
abre como **draft** en consecuencia.

## Matriz de cobertura

| Requisito del delta | Tareas / evidencia prevista | Estado |
|---|---|---|
| Contexto global de sensor y aislamiento de solicitudes | 1.1, 1.3, 1.5 | ✅ completo |
| Consulta de historial independiente de la ejecución | 1.2, 1.5, 2.3, 2.5 | ✅ completo |
| Navegación centrada en la decisión y resumen fiel | 2.1, 2.2, 2.5 | ✅ completo |
| Operaciones explícitas y protección de mutaciones | 1.3–1.5 | ✅ completo |
| Corrección humana explícita y recuperable | 3.1, 3.2, 3.5 | ✅ completo |
| Estado honesto de correcciones y recalibración | 3.3–3.5 | ✅ completo |
| Presentación accesible y adaptable | 4.1–4.6 | 🟡 parcial — reflow/zoom/móvil/teclado completo pendientes |
| Conservación de evidencia y explicación científica | 2.4, 4.5–4.7 | 🟡 parcial — 4.5/4.6 pendientes en móvil |

## Cierre

- [ ] Todos los escenarios tienen evidencia; ninguna casilla se completa solo por haber redactado el diseño. — **No cerrado**: 4.3/4.5/4.6 quedan pendientes (ver arriba). El resto de las entregas (1–3) sí tiene evidencia completa por escenario.
- [x] No hay cambios en `src/`, protocolos, configuraciones, artefactos científicos ni resultados históricos. — Confirmado en las cuatro entregas; esta (4) solo tocó `frontend/` y estos tres documentos.
- [x] El informe final distingue validación automatizada, visual e integración real y declara cualquier limitación pendiente. — Ver PR de esta entrega y las limitaciones declaradas arriba.

**El *change* `improve-alerting-ui-decision-workflow` no se declara completo.**
Las Entregas 1, 2 y 3 están implementadas, verificadas y mergeadas. La
Entrega 4 está parcialmente implementada: el trabajo de diseño (4.1, 4.2,
4.4, 4.7) está hecho y verificado; la verificación de accesibilidad en
viewport móvil real, reflow a 320 px, zoom 200% y trazado de teclado
completo (4.3, 4.5, 4.6) queda pendiente para quien retome esta rama con
acceso a un navegador sin la limitación de entorno descripta arriba.
