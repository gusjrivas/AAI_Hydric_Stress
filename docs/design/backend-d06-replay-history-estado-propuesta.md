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
  sistema DEBE mostrar un estado explícito con causa concreta, "en vez
  de omitir el campo".

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
2. **Semántica por valor** (idéntica a la ya usada en
   `medicion_original.estado`, extendida a cada fila):
   - `medida`: hay valor crudo para esa fecha y el marcador indica que no
     fue rellenado.
   - `imputada`: hay valor (crudo o reconstruido) y el marcador indica
     que sí fue rellenado por `interpolate_missing_causal`.
   - `sin_dato_en_fuente`: no hay valor crudo para esa fecha y el
     marcador sí cubre esa fecha (se sabe con certeza que faltaba en la
     fuente).
   - `no_determinado`: no se pudo reconstruir el marcador para esa fecha
     (p. ej. `ImputationSourceDriftError`, o la fecha queda fuera del
     rango cubierto) — nunca se infiere un estado por defecto optimista.
3. **Procedencia:** `estado` se deriva exclusivamente de
   `reconstruct_imputation_markers` sobre `dataset/*.parquet` ya
   empaquetado y verificado por hash — nunca de una imputación ad hoc en
   el endpoint. Si `ImputationSourceDriftError` se dispara, la fila queda
   en `no_determinado` para todas las fechas afectadas, nunca falla
   silenciosamente ni devuelve un valor sin marcar.
4. **Comportamiento ante indeterminación:** nunca omitir el campo (lo
   que RH-08 prohíbe); nunca sustituir por `medida` u otro valor
   optimista por defecto; el valor explícito es siempre
   `no_determinado`.
5. **Compatibilidad:** campo aditivo en un modelo Pydantic — no rompe
   consumidores que ignoren campos nuevos; no cambia `soil_moisture` ni
   el contrato de `medicion_original` ya existente.
6. **Corrección de trazabilidad asociada (si se aprueba):**
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

| Estado | `soil_moisture` | `estado` | Significado para el consumidor |
| --- | --- | --- | --- |
| `medida` | valor numérico | `"medida"` | Observación cruda del dataset empaquetado, no rellenada. |
| `imputada` | valor numérico (reconstruido o crudo) | `"imputada"` | El marcador de imputación confirma que este valor fue completado por `interpolate_missing_causal`; no es una medición directa. |
| `sin_dato_en_fuente` | `null` | `"sin_dato_en_fuente"` | Se sabe con certeza que no había dato en la fuente para esa fecha; el marcador lo confirma. |
| `no_determinado` | `null` o el valor crudo si existe, pero sin garantía de estado | `"no_determinado"` | No se pudo reconstruir el marcador (drift de fuente de imputación, fecha fuera de rango). Nunca se infiere `medida` por defecto. |

Ningún estado se acompaña de un valor numérico cuando ese valor sería una
estimación no marcada como tal, y ningún `null` se presenta sin una causa
(`estado`) explícita — esto es exactamente lo que RH-05/RH-08 exigen.
