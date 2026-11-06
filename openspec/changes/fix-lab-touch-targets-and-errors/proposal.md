# Proposal: objetivos táctiles y errores de red en español en el laboratorio (F5)

- HU: HU6 (UI). Capacidad: `alerting-ui`. Fase CRISP-DM: evaluación/despliegue.
- Impacto científico: ninguno. No cambia modelos, umbrales, protocolos, contrato OpenAPI ni resultados históricos.
- Problema: a <=600 px los selects (~36 px), los `summary` (~21 px) y el enlace «Ir al Laboratorio» (~20 px) del laboratorio quedaban bajo 44 px; con el backend apagado se mostraba el texto crudo «Failed to fetch».
- Cambio (sólo presentación): regla CSS `@media (max-width: 600px)` acotada a `.sensor-lab`; helper compartido `userFacingErrorMessage` (`frontend/src/features/shared/errorMessage.ts`) usado por el laboratorio, `QualityPanel` y `useForecastWorkspace`. Los detalles de error enviados por el servidor se conservan sin cambios.
