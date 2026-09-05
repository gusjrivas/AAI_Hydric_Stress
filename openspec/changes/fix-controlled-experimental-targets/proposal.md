# Objetivo observado común, ruido y escasez controlados

## Trazabilidad

HU7/HU8, CRISP-DM: preparación, modelado, evaluación e integración experimental.
Plan auditado y aprobado por el autor el 2026-09-05.

## Problema y cambio

Implementar las correcciones delimitadas en docs/research/protocolo-experimental-v3.md.
Archivos: src/experiment_runner; scripts/run_hu7_experiments.py; scripts/run_hu7_scenarios.py.
Afecta las cuatro configuraciones cuando usan estas capacidades; ET0 sigue deshabilitada.
No modifica hipótesis, propósito, alcance, entregables ni arquitectura general.

## Verificación

Tests causales, contratos incompatibles, separación temporal, objetivos comunes, conservación de
resultados históricos y pruebas de integración pertinentes. Resultados finales en seguimiento-tareas.

## Evolución científica

Los nuevos datasets y ablaciones quedan protocolizados para la siguiente fase; no se presentan
como experimentos ejecutados en este cambio.
