# Decisiones de diseño visual: alerting-ui (ForecastPage)

Registro de las decisiones de estilo tomadas para no tener que re-derivarlas en
sesiones futuras. No es un ADR (no es una decisión arquitectónica): es una
referencia de diseño para `frontend/src/features/forecast/`.

## Motivo

La UI original (tabla plana sin estilo) no distinguía visualmente las fechas
con alerta de las que no, y no dejaba explícito qué efecto tiene confirmar o
rechazar una alerta. Esto generaba una duda real al probar la interfaz: ¿el
modelo se actualiza al confirmar? (Respuesta verificada en el código:
`backend/app/routers/feedback.py` — confirmar/rechazar solo persisten el
estado de validación en el registro de retroalimentación; no disparan ningún
reentrenamiento. El disparo de recalibración desde la UI sigue fuera de
alcance, ver `openspec/changes/add-alerting-ui/proposal.md`.)

## Concepto

Panel de instrumento de monitoreo agronómico: cada alerta se lee como una
señal de sensor, no como una fila de tabla administrativa. Se evitan a
propósito los tres looks por defecto de diseño generado por IA (crema+serif,
negro+neón, estilo periódico de columnas).

## Tokens (definidos en `ForecastPage.css`, scope `.fp-page`)

| Token | Valor | Uso |
|---|---|---|
| `--fp-bg` | `#f4f6f2` | Fondo de página (verdoso pálido) |
| `--fp-ink` | `#1b2a1e` | Texto principal |
| `--fp-muted` | `#5c6b5f` | Texto secundario |
| `--fp-border` | `#d9e0d5` | Bordes, fondo de badge "pendiente" |
| `--fp-alert` / `--fp-alert-bg` | `#c1440e` / `#fbeae1` | Alerta activa (arcilla/herrumbre — estrés) |
| `--fp-safe` / `--fp-safe-bg` | `#2f6e4f` / `#e7f1ea` | Sin alerta / confirmada (verde hoja) |
| `--fp-action` / `--fp-action-bg` | `#1f5b6b` / `#e5eef0` | Acción principal (azul-riego), banner informativo |

Tipografía: sans del sistema para UI (sin fuentes externas — la app corre
local/Docker, evita dependencia de red); `ui-monospace` para fechas y
probabilidades, dando lectura de instrumento de medición.

## Layout

Cada alerta es un `<li class="fp-row">` (no una fila de tabla): barra vertical
de color a la izquierda según severidad (`fp-signal`), fecha + veredicto en
texto, probabilidad como número + mini-gauge horizontal, badge de estado
(`pendiente`/`confirmada`/`rechazada`) con color propio, acciones agrupadas a
la derecha. Responsive: en pantallas angostas las columnas colapsan a una sola.

## Explicitud sobre qué se está probando

Dos mecanismos, no uno solo:

1. **Banner fijo** arriba de la lista, siempre visible: explica que
   confirmar/rechazar guarda la validación pero no reentrena el modelo en
   esta iteración.
2. **Mensaje inline tras cada acción** (`role="status"`): p. ej. "Guardada la
   validación del 2024-10-31 — el modelo no se actualizó." Refuerza el punto
   en el momento exacto en que alguien podría asumir lo contrario. Se evitó
   deliberadamente repetir la palabra "confirmada"/"rechazada" en este
   mensaje: duplicaba el texto del badge de estado y generaba ambigüedad
   tanto visual (dos textos iguales en pantalla) como en los tests
   (`getByText` con múltiples coincidencias).

Si en una iteración futura se implementa disparo de recalibración desde la
UI, ambos mensajes deben actualizarse para reflejar el nuevo comportamiento
real — no dejar el texto desactualizado.

## Alcance de este cambio

Solo `frontend/src/features/forecast/ForecastPage.tsx` y su nuevo
`ForecastPage.css`. No se agregó ninguna librería de UI (sin Tailwind, sin
componentes de terceros) para mantener el frontend sin dependencias nuevas.
