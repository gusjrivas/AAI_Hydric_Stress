# D-06 — Propuesta: exponer `estado` por fila en `GET /replay/history`

**Estado:** propuesta pendiente de aprobación normativa. NO implementada.
No autoriza a Claude Code (ni a ningún ejecutor) a modificar
`schemas_replay.py`, `history_view.py` ni `replay.py` sin aprobación
explícita de quien tiene autoridad sobre la spec `historical-replay`.

## Origen y obligación vigente

`openspec/changes/add-causal-historical-replay/specs/historical-replay/spec.md`
contiene dos requirements **DEBE (MUST)** vigentes:

- **RH-05** (líneas 122-140): para una fecha del historial mostrado antes
  de la revelación cuyo marcador de imputación no fue recomputado, el
  estado DEBE quedar en `no_determinado` — nunca `medida` ni un valor
  numérico inferido.
- **RH-08** (líneas 235-247): ante cualquier dato no resoluble, el
  sistema DEBE mostrar un estado explícito **acompañado de la causa
  concreta** (p. ej. "no_determinado: marcador de imputación no
  recomputado para esta instancia"), "en vez de omitir el campo o
  completarlo por inferencia".

`backend/app/schemas_replay.py::ReplayHistoryRow` hoy solo tiene `fecha`
y `soil_moisture: float | None` — sin campo de estado. Esto es
exactamente lo que RH-08 prohíbe. `traceability.md` marca RH-05/RH-08
como "[implementada]" pese a admitir esta brecha en su propio texto.

## Base técnica ya existente (bajo riesgo, no requiere construir desde cero)

- `src/historical_replay/imputation_markers.py::reconstruct_imputation_markers`
  ya reconstruye el marcador `<columna>_imputado` de forma determinista y
  verificada (`verify_imputation_source_matches_verified_commit`).
- `src/historical_replay/observations.py` ya define las 4 constantes de
  estado (`MEASURED`, `IMPUTED`, `UNDETERMINED`, `MISSING_FROM_SOURCE`) y
  la lógica de derivación (`link_observation`), hoy usada solo para
  `medicion_original.estado`.
- `backend/app/routers/replay.py:215` ya invoca el código que consume
  `imputation_markers_df`, pero con `imputation_markers_df=None` — la
  brecha es que `history_view.py::filtered_history` nunca lo expone.

## Propuesta concreta

1. **Campo nuevo:** `ReplayHistoryRow.estado: Literal["medida", "imputada", "no_determinado", "sin_dato_en_fuente"]`,
   reutilizando exactamente las constantes de `observations.py`.
2. **Campo nuevo, obligatorio salvo `medida`:** `ReplayHistoryRow.causa: str | None`,
   con la causa concreta exigida literalmente por RH-08 ("acompañado de
   la causa concreta", no solo el nombre del estado). `causa` es `None`
   únicamente cuando `estado == "medida"` (no hay nada que explicar); en
   cualquier otro estado, `causa` es una cadena no vacía y concreta —
   nunca un texto genérico como `"no determinado"` repetido sin motivo.
   Ejemplos: `"marcador de imputación no recomputado para esta
   instancia"`, `"ImputationSourceDriftError: código de imputación
   cambió sin actualizar el hash verificado"`, `"fecha fuera del rango
   cubierto por reconstruct_imputation_markers"`.
3. **Semántica por valor** (idéntica a la ya usada en
   `medicion_original.estado`, extendida a cada fila):
   - `medida`: hay valor crudo para esa fecha y el marcador indica que no
     fue rellenado. `causa=None`.
   - `imputada`: hay valor (crudo o reconstruido) y el marcador indica
     que sí fue rellenado por `interpolate_missing_causal`. `causa`
     describe el mecanismo de relleno (p. ej. `"interpolate_missing_causal
     rellenó esta fecha desde el valor causal anterior"`).
   - `sin_dato_en_fuente`: no hay valor crudo para esa fecha *incluso
     después de aplicar la imputación causal* (espejo exacto de la
     definición de RH-05/`link_observation` para `medicion_original`,
     no una definición nueva) — el marcador de imputación cubre esa
     fecha y confirma que no había dato disponible en la fuente ni
     relleno posible. `causa` identifica la fecha y que la reconstrucción
     de marcadores confirma la ausencia real en la fuente.
   - `no_determinado`: no se pudo reconstruir el marcador para esa fecha
     (p. ej. `ImputationSourceDriftError`, o la fecha queda fuera del
     rango cubierto) — nunca se infiere un estado por defecto optimista.
     `causa` identifica cuál de esas condiciones aplicó, para que un
     consumidor pueda distinguir "drift de código de imputación" de
     "fecha fuera de rango cubierto", en vez de recibir el mismo texto
     genérico para causas distintas.
4. **Procedencia:** `estado` y `causa` se derivan exclusivamente de
   `reconstruct_imputation_markers` sobre `dataset/*.parquet` ya
   empaquetado y verificado por hash — nunca de una imputación ad hoc en
   el endpoint. Si `ImputationSourceDriftError` se dispara, la fila queda
   en `no_determinado` (con `causa` citando el drift) para todas las
   fechas afectadas, nunca falla silenciosamente ni devuelve un valor sin
   marcar.
5. **Comportamiento ante indeterminación:** nunca omitir el campo (lo
   que RH-08 prohíbe); nunca sustituir por `medida` u otro valor
   optimista por defecto; el valor explícito es siempre
   `no_determinado`, siempre acompañado de una `causa` concreta y no
   genérica (RH-08 exige la causa, no solo el nombre del estado).
6. **Compatibilidad:** campos aditivos en un modelo Pydantic — no rompen
   consumidores que ignoren campos nuevos; no cambia `soil_moisture` ni
   el contrato de `medicion_original` ya existente.
7. **Corrección de trazabilidad asociada (si se aprueba):**
   `openspec/changes/add-causal-historical-replay/traceability.md` debe
   reflejar "parcialmente implementada: cubre `medicion_original`,
   pendiente en `/replay/history`" para RH-05/RH-08 hasta que la
   Corrección 5 la cierre.

## Qué NO decide esta propuesta

No decide "extender la API" vs. "acotar la spec" — sigue la orientación
ya dada por el usuario de conservar el requisito vigente (RH-05/RH-08
tal como están escritos), y presenta la opción "extender" al nivel de
detalle necesario para que la aprobación sea sobre un diseño concreto.
Si se aprueba, la implementación (con pruebas de aceptación análogas a
las de las Correcciones 2/3 de este mismo cierre) se encarga por
separado, como Corrección 5 de un encargo posterior — no en este PR.

## Qué recibiría un consumidor de `/replay/history` en cada estado

| Estado | `soil_moisture` | `estado` | `causa` | Significado para el consumidor |
| --- | --- | --- | --- | --- |
| `medida` | valor numérico | `"medida"` | `null` | Observación cruda del dataset empaquetado, no rellenada. |
| `imputada` | valor numérico (reconstruido o crudo) | `"imputada"` | p. ej. `"interpolate_missing_causal rellenó esta fecha desde el valor causal anterior"` | El marcador de imputación confirma que este valor fue completado por `interpolate_missing_causal`; no es una medición directa. |
| `sin_dato_en_fuente` | `null` | `"sin_dato_en_fuente"` | p. ej. `"marcador de imputación confirma ausencia en la fuente para esta fecha, incluso tras aplicar interpolate_missing_causal"` | Se sabe con certeza — tras aplicar la imputación causal, no solo antes — que no había dato disponible; el marcador lo confirma. |
| `no_determinado` | `null` o el valor crudo si existe, pero sin garantía de estado | `"no_determinado"` | p. ej. `"ImputationSourceDriftError: código de imputación cambió sin actualizar el hash verificado"` o `"fecha fuera del rango cubierto por reconstruct_imputation_markers"` | No se pudo reconstruir el marcador. Nunca se infiere `medida` por defecto. |

Ningún estado se acompaña de un valor numérico cuando ese valor sería una
estimación no marcada como tal, y ningún `null` se presenta sin una causa
concreta (`estado` + `causa`, no solo `estado`) explícita — esto es
exactamente lo que RH-05/RH-08 exigen ("con causa concreta", no solo un
nombre de estado).
