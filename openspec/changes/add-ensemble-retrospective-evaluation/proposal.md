# Change: evaluacion retrospectiva del ensamble demostrativo

## Motivacion

Los nueve bundles demostrativos de Pergamino tienen evidencia de carga e
inferencia, pero no una evaluacion aplicable a 2023. Esta brecha impide asociar
desempeno historico a cada familia/horizonte y comparar la politica vigente de
promedio con persistencia y con la mayoria propuesta.

## Alcance

- HU4, HU7 y HU8; capacidad `experiment-runner`; CRISP-DM: evaluacion.
- Evaluacion retrospectiva exploratoria, no independiente, sobre emisiones y
  targets observados dentro de 2023.
- Nueve artefactos fijos: regresion logistica, Random Forest e
  HistGradientBoosting para +1/+2/+3.
- Comparaciones preespecificadas: familias, promedio aritmetico vigente,
  persistencia y mayoria secundaria.
- Filtrado secuencial de entradas mixtas antes de pandas, inferencia causal sin
  persistir emisiones, metricas, cobertura, episodios e incertidumbre pareada.

## Exclusiones e impacto

No modifica ni ejecuta `controlled_daily_v3`, A/B/C/H, gates, ledgers,
resultados historicos, modelos, calibradores, hiperparametros, contratos,
politica productiva, UI, emisiones o feedback. No entrena ni recalibra. No
recalcula P20. No cambia hipotesis, alcance ni arquitectura. El resultado no es
confirmatorio ni demuestra utilidad agronomica.

## Trazabilidad

- HU4: evaluacion de artefactos predictivos existentes.
- HU7: evaluador reproducible y trazable.
- HU8: interpretacion de resultados y limitaciones.
- Memoria: capitulo 2 (metodo), capitulo 3 (implementacion) y capitulo 4
  (resultados exploratorios).
