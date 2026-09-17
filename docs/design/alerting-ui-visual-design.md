# Decisiones de diseño visual: alerting-ui

## Actualización 2026-09-17: productor y agrónomo sin perfil tecnológico

La presentación principal prioriza lenguaje cotidiano y tareas. El resultado se
explica en palabras; el valor de la señal se consulta por un desplegable y no se
interpreta como porcentaje de certeza. Se explican las diferencias entre ausencia
de alerta, ausencia de datos y ausencia de resultados guardados. La aplicación no
indica cuánto ni cuándo regar.

La navegación usa Resumen, Historial y observaciones, Datos disponibles, Ajustar
próximos pronósticos y Acerca de esta herramienta, conservando los hashes existentes.
La documentación de arquitectura y los identificadores del predictor/linaje quedan
en detalles expandibles. Las variables conocidas se traducen al español. «Aplicar
observaciones» explica su efecto sobre la próxima ejecución y preserva resultados
anteriores. No promete mejorar el desempeño.

Esta actualización sustituye las etiquetas técnicas de la entrega 4 descritas a
continuación. Tests/lint/build aprobados; inspección visual y evaluación con usuarios
pendientes. Change: `openspec/changes/simplify-producer-ui/`.

Registro de las decisiones de estilo tomadas para no tener que re-derivarlas en
sesiones futuras. No es un ADR (no es una decisión arquitectónica): es una
referencia de diseño para `frontend/src/`. Reemplaza la versión anterior de
este documento (centrada solo en `ForecastPage`, previa a la reorganización
por destinos de `openspec/changes/improve-alerting-ui-decision-workflow/`).

## Motivo

La UI original era un único scroll largo organizado como un recorrido de
defensa (arquitectura → calidad → predicción → linaje → evidencia); consultar
un pronóstico existente exigía correr uno nuevo, el sensor se editaba dentro
de una sección aunque afectaba a toda la app, el "Rechazar" de un clic
inventaba una observación fija y adivinaba la etiqueta opuesta, y un contador
insinuaba una elegibilidad de recalibración que la API no expone. La Entrega
4 (`tasks.md`, sección 4) además encontró y corrigió deuda de estilo real:
tokens de color duplicados por componente, un tema oscuro parcial heredado
del boilerplate de `create-vite` que nunca se retiró, un layout de página
anidado (`.fp-page` con su propio `min-height:100vh` dentro de `.app-page`),
y el badge de "confirmada" reutilizando el mismo verde que "sin alerta".

## Concepto

Panel de instrumento de monitoreo agronómico: cada alerta se lee como una
señal de sensor, no como una fila de tabla administrativa. Se evitan a
propósito los tres looks por defecto de diseño generado por IA (crema+serif,
negro+neón, estilo periódico de columnas). Tema claro único y deliberado —
sin una segunda declaración de modo oscuro en ningún archivo.

## Tokens (centralizados en `frontend/src/index.css`, `:root`)

| Token | Valor | Uso |
|---|---|---|
| `--color-bg` | `#f4f6f2` | Fondo de página (verdoso pálido) |
| `--color-surface` | `#ffffff` | Tarjetas, filas, paneles |
| `--color-ink` | `#1b2a1e` | Texto principal |
| `--color-muted` | `#5c6b5f` | Texto secundario |
| `--color-border` | `#d9e0d5` | Bordes decorativos (divisores, barras de fondo) |
| `--color-border-strong` | `#5c6b5f` | Bordes de controles interactivos (inputs, botones, selects) — ≥3:1, ver tabla de contrastes |
| `--color-alert` / `--color-alert-bg` | `#c1440e` / `#fbeae1` | Señal de alerta (`alerta_generada`) — arcilla/herrumbre |
| `--color-alert-text-on-bg` | `#a83a0c` | Texto sobre `--color-alert-bg` (el `--color-alert` base no llega a 4.5:1 ahí) |
| `--color-safe` / `--color-safe-bg` | `#2f6e4f` / `#e7f1ea` | Señal de ausencia de alerta — verde hoja |
| `--color-action` / `--color-action-bg` | `#1f5b6b` / `#e5eef0` | Acción principal, navegación activa |
| `--color-review-pending(-bg)` | = muted/border | Badge "pendiente" |
| `--color-review-confirmed(-bg)` | = action/action-bg | Badge "confirmada" |
| `--color-review-corrected(-bg)` | `#6b4c8a` / `#eee6f2` | Badge "rechazada" (corrección registrada) |

Antes de esta entrega, el badge "confirmada" reutilizaba `--color-safe` (el
mismo verde de "sin alerta"): confirmar una alerta la pintaba visualmente de
segura. El estado de revisión (pendiente/confirmada/rechazada) tiene ahora
una paleta propia, completamente independiente de la señal predictiva
(alerta/sin alerta) — ver design.md §5 del *change* citado arriba.

Tipografía: sans del sistema para UI (sin fuentes externas — la app corre
local/Docker); `ui-monospace` para fechas y probabilidades (`font-variant-numeric:
tabular-nums` en los valores numéricos), dando lectura de instrumento de
medición. Escala de espaciado `--space-1` a `--space-8` (4/8/12/16/24/32 px).

## Estructura y navegación

Cinco destinos por hash (`frontend/src/features/navigation/`), sin router de
terceros — el navegador resuelve Atrás/Adelante sobre `location.hash`:

| Destino | Hash | Contenido |
|---|---|---|
| Resumen | `#resumen` (por defecto) | Último pronóstico registrado, fechas, pendientes de revisión, acción de generar pronóstico, contexto de calidad resumido |
| Alertas y revisión | `#prediccion` | Historial, filtros, confirmar/corregir |
| Calidad de datos | `#calidad` | Período disponible, faltantes, duplicados, anomalías |
| Modelo y trazabilidad | `#linaje` | Predictor activo, correcciones registradas/incorporadas, recalibración manual, linaje |
| Evidencia y arquitectura | `#evidencia` | Recorrido de defensa, evidencia congelada, limitaciones |

Los anchors previos a la reorganización (`#calidad`, `#prediccion`, `#linaje`,
`#evidencia`) siguen resolviendo a su destino equivalente. Cada cambio de
destino actualiza `document.title` y enfoca el `<h2>` del destino (`tabIndex=-1`,
con `outline` visible al recibir foco programático).

`useForecastWorkspace` (historial, resultado de la última corrida, bloqueo de
mutaciones) se instancia una única vez en `App.tsx` y se comparte entre
Resumen y Alertas y revisión: navegar entre ellos no reinicia el historial ni
pierde el resultado del último pronóstico. Calidad, predictor activo y linaje
mantienen sus propios estados independientes (un fallo de uno no oculta a los
demás).

## Layout

Cada alerta es un `<li class="fp-row">` (no una fila de tabla): barra
vertical de color a la izquierda según severidad (`fp-signal`), fecha +
veredicto en texto, probabilidad como número + mini-gauge horizontal, badge
de estado de revisión, acciones agrupadas a la derecha. Responsive: en
pantallas angostas (`max-width: 640px`) las columnas colapsan a una sola.

`.app-page` es el único contenedor con `padding`; ningún componente anidado
(`.fp-page`, paneles) declara su propio `min-height`/padding de página completa
— esa duplicación (layout de página anidado) fue uno de los hallazgos
corregidos en la Entrega 4.

## Explicitud sobre qué se está probando

- **Banner fijo** en Alertas y revisión: explica que consultar/filtrar no
  genera un pronóstico, que confirmar/corregir guarda la validación sin
  reentrenar el modelo, y que la recalibración manual vive en Modelo y
  trazabilidad.
- **Mensaje inline tras cada acción** (`role="status"`): p. ej. "Validación
  guardada del 2024-10-31 — el modelo no se actualizó." Se evita deliberadamente
  repetir la palabra "confirmada"/"rechazada" en este mensaje (duplicaría el
  texto del badge y generaba ambigüedad visual y en tests con `getByText`).
- **Formulario de corrección** (`CorrectionForm.tsx`): muestra resultado
  original y fecha objetivo; no escribe nada hasta elegir explícitamente una
  etiqueta opuesta a la original (la misma etiqueta muestra un aviso y
  orienta a "Confirmar" en su lugar); cancelar no escribe y devuelve el foco
  al botón que abrió el formulario; un 409 del backend se muestra junto a la
  fila conservando el contenido del formulario.
- **Correcciones y recalibración** (`RecalibrationPanel.tsx`, en Modelo y
  trazabilidad): cuenta las correcciones registradas y, por separado, si cada
  fecha ya aparece en `applied_feedback_dates` del predictor activo — sin
  calcular un total de "elegibles" (la API no expone ese preflight) y sin
  inferir que una edición posterior a esa fecha fue incorporada. Si la
  consulta del predictor falla, la incorporación se informa como
  "desconocida", nunca como "no incorporada".

## Accesibilidad (WCAG 2.2 AA)

- **Enlace para saltar al contenido** (`.skip-link` en `App.tsx`): primer
  elemento del documento, oculto hasta recibir foco por teclado, salta a
  `#main-content` (`<main tabIndex={-1}>`).
- **Foco visible**: regla global `:focus-visible { outline: var(--focus-ring); }`
  en `index.css`; los encabezados de destino (`tabIndex=-1`, foco programático
  tras navegar) usan `:focus` explícito para garantizar el anillo también ahí,
  dado que el comportamiento de `:focus-visible` ante `element.focus()` vía
  script varía entre navegadores.
- **Objetivo de 44×44 CSS px** en controles principales (botones de acción,
  enlaces de navegación, input de sensor): aplicado vía `min-height: 44px`.
  Best-effort — no se midió cada control renderizado en un viewport real (ver
  limitaciones).
- **Tabla de evidencia formal** (`EvidencePanel.tsx`): su contenedor de
  scroll horizontal (`.ep-table-wrap`) es ahora un `role="region"` con
  `aria-label` y `tabIndex={0}`, alcanzable y desplazable por teclado —
  antes solo funcionaba con mouse/trackpad.
- **Anuncios**: `role="status"` para guardados/mensajes informativos,
  `role="alert"` para errores — sin repetir el anuncio de cada panel en cada
  interacción.
- **`prefers-reduced-motion`**: la app no tiene animaciones reales; la regla
  global en `index.css` es una salvaguarda para cualquier transición que se
  agregue a futuro.

### Contrastes — verificados por cálculo, no solo inspección visual

Fórmula de luminancia relativa y contraste de WCAG 2.2, aplicada a los pares
de color efectivamente usados (script ad hoc, no versionado en el repo —
resultado documentado acá para no tener que re-derivarlo):

| Par | Contraste | Umbral | Resultado |
|---|---|---|---|
| `--color-ink` sobre `--color-bg` | 13.83:1 | 4.5:1 | ✅ |
| `--color-ink` sobre `--color-surface` | 15.04:1 | 4.5:1 | ✅ |
| `--color-muted` sobre `--color-bg` | 5.19:1 | 4.5:1 | ✅ |
| `--color-muted` sobre `--color-surface` | 5.64:1 | 4.5:1 | ✅ |
| `--color-alert` sobre `--color-alert-bg` | 4.38:1 | 4.5:1 | ❌ → corregido con `--color-alert-text-on-bg` (5.48:1) |
| `--color-alert` sobre `--color-surface`/`--color-bg` | 5.12:1 / 4.71:1 | 4.5:1 | ✅ |
| `--color-safe` sobre `--color-safe-bg` | 5.24:1 | 4.5:1 | ✅ |
| `--color-action` sobre `--color-action-bg` | 6.44:1 | 4.5:1 | ✅ |
| Blanco sobre `--color-action` (botones, nav activa) | 7.59:1 | 4.5:1 | ✅ |
| `--color-review-corrected` (`#6b4c8a`) sobre su fondo (`#eee6f2`) | 5.70:1 | 4.5:1 | ✅ |
| `--color-border` sobre `--color-bg`/`--color-surface` (decorativo) | ~1.3:1 | — | No conlleva información por sí solo; no se usa como borde de control interactivo |
| `--color-border-strong` sobre `--color-bg`/`--color-surface` (controles) | 5.19:1 / 5.64:1 | 3:1 (no-texto) | ✅ |

El único hallazgo real de esta medición: `--color-alert` (`#c1440e`) sobre
`--color-alert-bg` (`#fbeae1`) daba 4.38:1, por debajo del umbral de texto
normal (4.5:1) — usado en el badge "rechazada" antes de que ese estado se
rediseñara con paleta propia (`--color-review-corrected`). El texto sobre
fondo de alerta que pudiera necesitarse a futuro debe usar
`--color-alert-text-on-bg` (5.48:1), no `--color-alert` directamente.

### Verificado en navegador (Claude in Chrome, sin backend real — `fetch`
interceptado en el propio navegador con datos sintéticos)

- Estados de historial: vacío (404), error de red (500, con reintento),
  histórico extenso (18 filas), alerta/sin alerta mezclados.
- Guardado exitoso de una corrección y 409 con formulario preservado.
- Recalibración exitosa con su mensaje visible en Modelo y trazabilidad, y
  fallo de integridad de linaje mostrado explícitamente (no oculto ni vacío).
- Badge "confirmada" en azul de acción (no verde) conviviendo con una fila en
  estado de alerta (barra roja) en la misma captura — confirma visualmente
  que la corrección no altera la señal predictiva.
- Enlace de salto al contenido: confirmado por consulta directa del DOM que
  es el primer elemento enfocable (`querySelectorAll` en orden de documento)
  y que su destino (`#main-content`) es programáticamente enfocable.
- Sin scroll horizontal global a 1864 px de viewport (`scrollWidth === clientWidth`).

### Limitaciones no resueltas, declaradas explícitamente

- **Viewport móvil real y zoom 200% sin verificar**: la herramienta de
  redimensionado de ventana del navegador de esta sesión no tuvo efecto
  (`window.innerWidth` no cambia pese a pedir 375×812 o 390×844) en ninguna
  de las cuatro entregas de este *change*. El comportamiento responsive
  (`flex-wrap`, columna única por defecto en `ResumenView`, colapso de
  `.fp-row` a `max-width: 640px`) se sostiene en la revisión de código, no en
  una captura móvil real.
- **Trazado manual de Tab por teclado inconcluyente** en esta sesión de
  automatización (comportamiento inconsistente entre intentos, atribuible a
  la herramienta de automatización, no reproducido de forma confiable); el
  orden de foco correcto se verificó en cambio por inspección directa del DOM
  (`querySelectorAll` de elementos enfocables) y por tests de
  `@testing-library` que sí ejercitan foco programático (cancelar devuelve el
  foco al activador, navegar enfoca el encabezado del destino).
- **44×44 px no medido en un viewport real**: aplicado vía CSS, no verificado
  con una regla o captura a escala real.
- Sin integración real contra `backend/` — toda la verificación en navegador
  usó un `fetch` interceptado con datos sintéticos, nunca el dataset
  histórico real ni un backend corriendo.

## Alcance de este documento

Cubre `frontend/src/index.css` (tokens globales) y las hojas de estilo de
`frontend/src/App.css` y de cada feature (`forecast/`, `summary/`,
`navigation/`, `quality/`, `lineage/`, `evidence/`, `architecture-flow/`). No
se agregó ninguna librería de UI ni de routing (sin Tailwind, sin componentes
de terceros, sin React Router) para mantener el frontend sin dependencias
nuevas — decisión reafirmada en cada una de las cuatro entregas de
`openspec/changes/improve-alerting-ui-decision-workflow/`.
