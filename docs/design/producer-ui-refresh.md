# UI renovada del productor — HU5/HU6

Rama feat/hu6-productor-ui-renovada, sobre 3081a96 del PR #209. No se fusiona a main.
Worktree C:/Repo/AAI_Hydric_Stress_ui_refresh, separado de la evidencia científica.

## Entregado

Espacio con hero verde profundo e ilustración SVG decorativa, acento lima en
consulta y ámbar en alertas. Selectores y tarjetas se adaptan a móvil. Datos
simulados, antigüedad, faltantes y ausencia de porcentaje siguen explícitos.
Detalles temporales, fechas futuras e historial se despliegan a demanda.
La navegación anterior sigue en Más herramientas y antecedentes.

Estado compartido de opiniones por sensor/forecast_id, con revisiones monotónicas.
La API invalid_cursor ofrece recargar sin cursor; fallos de Ver más conservan
la página y ofrecen reintento. Un fallo de refresco tras conflicto no anuncia éxito.
No se modifican backend, modelos, manifiestos ni resultados científicos.

## Prueba local independiente

Desde esta rama en PowerShell:

```powershell
$env:PRODUCER_PREVIEW_UI_PORT="5182"
$env:PRODUCER_PREVIEW_API_PORT="8182"
$env:PRODUCER_PREVIEW_BACKEND_IMAGE="aai-producer-ui-refresh-backend:local"
docker compose -p aai-producer-ui-refresh -f compose.producer-preview.yml up -d --build
```

UI http://localhost:5182; API http://localhost:8182/docs. Proyecto, imagen y volumen
propios. No reemplaza la demo de 5180. Para detener conservando las opiniones,
usar las mismas variables y `docker compose -p aai-producer-ui-refresh -f
compose.producer-preview.yml down` (en una sola línea, sin -v).

## Evidencia y límites

Suite frontend completa, lint y build verificados. Detalle del conteo final en PR.
Chrome real contra backend Docker: selección de Huerta norte, consulta de tres
fechas, confirmación del resultado del 21/09 con comentario explícito de prueba,
contador 6→5 y revisables 3→2, historial con Confirmado por vos sin recargar.
Ese registro permanece solo en el volumen sintético nuevo.

Viewport 390x844: controles y tarjetas en una columna, sin overflow horizontal
(documentWidth 375, innerWidth 390); foco violeta visible en navegación con Tab.
Revisión escritorio y consola sin errores observados. No equivale a una auditoría
WCAG exhaustiva ni a pruebas en un teléfono físico. Se restauró el viewport.
La aceptación estética/comprensión final corresponde al usuario: PR en borrador.

HU5/HU6/UI, capacidad alerting-ui, CRISP-DM integración; aporte al capítulo 3.
Sin cambios a hipótesis, arquitectura o configuraciones experimentales HU7/HU8.
No se habilitan porcentajes ni se promete validez agronómica. Las correcciones
backend siguen en PR #209 y esta rama incorpora su commit sin merge a main.