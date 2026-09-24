# Tasks: improve-replay-ui-guided-experience

- [x] 1. Relevamiento dirigido del estado actual (frontend, backend, specs,
      change `add-causal-historical-replay`) y verificación de hallazgos
      previos contra el código en `f17fe658` (base de esta rama).
- [x] 2. Navegación: integrar "Explorar una predicción" en
      `useHashRoute`/`DestinationNav`; eliminar el enlace duplicado.
- [x] 3. Selección temporal: origen reubica el reloj y oculta el resultado
      anterior; distinguir las tres fechas; "Volver al inicio de este caso"
      conserva el origen; agregar "Ver qué ocurrió el [fecha objetivo]".
- [x] 4. Gráfico principal integrado (`MoistureHistoryChart`): escala
      temporal real, huecos por nulo o fecha ausente, marcadores de
      origen/objetivo, umbral con sombreado, intervalo oculto explícito,
      banda de clase predicha separada, ventana inicial ~30 días con
      ampliación.
- [x] 5. Predicción explicada en palabras (`ReplayPredictionSummary`).
- [x] 6. Comparación explicativa con las cuatro categorías y distancia con
      signo al umbral (`ReplayComparisonCard`, `outcomeCategory.ts`).
- [x] 7. Estados explícitos de carga/errores/ausencia, sin convertir en "sin
      alerta".
- [x] 8. Pruebas: `HistoricalReplayPage.test.tsx` (reescrito),
      `MoistureHistoryChart.test.tsx` (nuevo), `outcomeCategory.test.ts`
      (nuevo), `dateUtils.test.ts` (nuevo), `App.test.tsx` (navegación,
      ampliado).
- [x] 9. Verificación mecánica: `npm test`, `npm run lint`, `npm run build`.
- [ ] 10. Comprobación visual en navegador con el paquete autorizado (antes
      de revelar, después de revelar, tras cambiar de caso, en pantalla
      pequeña) — ver evidencia y limitaciones en la descripción del PR.
- [x] 11. `proposal.md`, `tasks.md` y specs delta de esta capacidad y de
      `alerting-ui` (navegación).
