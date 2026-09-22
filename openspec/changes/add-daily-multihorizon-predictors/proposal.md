# Change: Predictores operativos independientes a uno, dos y tres días

Estado: aceptado por el autor el 2026-09-19; implementación parcial en
`feat/hu6-backend-soporte-ui`. No modifica `main`, specs canónicas ni resultados
históricos. El primer ajuste continúa bloqueado hasta congelar el manifiesto previo.

## Why
El predictor actual responde únicamente t+3. La UI requiere estimaciones para
cada uno de los próximos tres días con el mismo corte de información.

## What Changes
Contrato operativo producer_daily_h123_v1, predictores directos para h=1,2,3,
disponibilidad por horizonte y evaluación de desarrollo de sus probabilidades.
No se sustituyen experimentos ni modelos vigentes.

## Trazabilidad e impacto explícito
HU4, Épica 2; predictive-modeling. CRISP-DM modelado/evaluación de desarrollo.
Ampliación metodológica OPERATIVA del horizonte: nuevas etiquetas y artefactos.
Hipótesis y alcance de tesis sin cambios, arquitectura por capas preservada.
Base/+sintéticos/+anomalías/completa formales no cambian; el nuevo contrato parte
de configuración base operativa sin activar síntesis/anomalías por esta UI.
HU7/HU8: no editar protocolos, resultados, holdouts ni métricas históricas.
Nueva evaluación separada, no evidencia confirmatoria externa.
Memoria: capítulo 2 explica límites/causalidad; capítulo 3 integra el contrato.
ADR-0013 propuesto y ADR-0009; ADR-0010/0011 conservados.

## Fuera de alcance
t+7, interpolación de riesgos, búsqueda de semillas favorables, optimización de
umbrales mirando test, nuevos datasets externos y uso de holdouts científicos.

## Corrección del criterio de evidencia
Se exige evaluación directa de calibración con incertidumbre temporal, soporte,
cobertura y estabilidad por horizonte. Brier/log-loss quedan como controles
complementarios. Tolerancias numéricas y método estadístico se justifican y
congelan antes del ajuste; hasta completar ese plan no hay calificación.
No cambia protocolos formales ni autoriza nuevos experimentos HU7/HU8.
