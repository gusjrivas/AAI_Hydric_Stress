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

- [ ] 2.1 Implementar cinco destinos por hash, compatibilidad de anchors existentes, Atrás/Adelante, título, foco y destino activo.
- [ ] 2.2 Construir Resumen: último pronóstico registrado, fechas diferenciadas, pendientes de revisión y contexto de calidad. Estados vacíos y parciales explícitos.
- [ ] 2.3 Agregar filtros de alerta, validación y rango de referencia; limpiar filtros, orden descendente y contadores generales independientes del filtro.
- [ ] 2.4 Reubicar arquitectura/evidencia y predictor/linaje manteniendo contenido y procedencia; desplegar detalles técnicos sin retirarlos.
- [ ] 2.5 Tests de navegación, conservación de contexto, selección del último registro, fechas calendario sin desplazamiento y filtros sin coincidencias.

**Salida:** acceso directo al pronóstico y su revisión, con recorrido de defensa disponible.

## 3. Revisión humana y trazabilidad — depende de 1 y 2

- [ ] 3.1 Formulario inline de corrección con etiqueta explícita, observación editable, cancelar sin POST y recuperación del foco.
- [ ] 3.2 Mostrar motivos de 409 junto a la fila conservando el formulario; mantener mensaje de que guardar feedback no reentrena.
- [ ] 3.3 Sustituir el contador engañoso de pendientes por correcciones registradas y fechas incorporadas, con desconocido si falta metadata. No inferir elegibilidad ni incorporación de ediciones posteriores.
- [ ] 3.4 Ubicar recalibración manual en Modelo y trazabilidad, refrescar predictor/linaje tras éxito y preservar el historial.
- [ ] 3.5 Tests de payload de corrección, cancelación, etiqueta igual a original, 409, metadata ausente, fecha ya incorporada y recalibración sin correcciones elegibles.

**Salida:** feedback explícito y estado fiel a los contratos existentes, sin cambios temporales.

## 4. Diseño coherente y verificación — depende de 2 y 3

- [ ] 4.1 Centralizar tokens, tema claro, tipografía y estados; retirar estilos globales heredados incompatibles y layout de página anidado.
- [ ] 4.2 Ajustar escritorio/móvil, formularios, navegación, estados de carga/error/vacío y mensajes accesibles.
- [ ] 4.3 Verificar teclado completo, foco, contraste WCAG 2.2 AA, reflow y zoom según `design.md`; documentar hallazgos y corregirlos.
- [ ] 4.4 Ejecutar en `frontend/`: `npm test`, `npm run lint`, `npm run build`. No sustituir inspección visual por tests de jsdom.
- [ ] 4.5 Revisar en navegador a 360/768/1440 px y 320 CSS px: vacío, error, historial extenso, alerta/sin alerta, guardado, 409, recalibración y linaje fallido. Usar fixtures identificados o sensor de prueba aislado; nunca datos experimentales históricos para escrituras de QA.
- [ ] 4.6 Registrar evidencia de consulta/revisión/lectura de linaje con teclado y móvil; distinguir pruebas con fixtures de integración real. Verificar que consultar y navegar no generan POST.
- [ ] 4.7 Actualizar `docs/design/alerting-ui-visual-design.md`, `docs/seguimiento-tareas.md` y spec canónica únicamente con lo efectivamente implementado. Registrar impacto nulo HU7/HU8 y aporte al capítulo 3.

## Matriz de cobertura

| Requisito del delta | Tareas / evidencia prevista |
|---|---|
| Contexto global de sensor y aislamiento de solicitudes | 1.1, 1.3, 1.5 |
| Consulta de historial independiente de la ejecución | 1.2, 1.5, 2.3, 2.5 |
| Navegación centrada en la decisión y resumen fiel | 2.1, 2.2, 2.5 |
| Operaciones explícitas y protección de mutaciones | 1.3–1.5 |
| Corrección humana explícita y recuperable | 3.1, 3.2, 3.5 |
| Estado honesto de correcciones y recalibración | 3.3–3.5 |
| Presentación accesible y adaptable | 4.1–4.6 |
| Conservación de evidencia y explicación científica | 2.4, 4.5–4.7 |

## Cierre

- [ ] Todos los escenarios tienen evidencia; ninguna casilla se completa solo por haber redactado el diseño.
- [ ] No hay cambios en `src/`, protocolos, configuraciones, artefactos científicos ni resultados históricos.
- [ ] El informe final distingue validación automatizada, visual e integración real y declara cualquier limitación pendiente.
