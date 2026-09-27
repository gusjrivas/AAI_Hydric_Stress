## ADDED Requirements

### Requirement: evaluacion inmutable y causal de bundles demostrativos

El sistema SHALL evaluar los nueve bundles fijos de Pergamino sobre emisiones
de 2023 con target tambien en 2023, sin ajustar modelos, calibradores, umbrales
ni P20, y SHALL usar la carga e inferencia operativas con sus controles de
identidad, entorno y features.

#### Scenario: incompatibilidad fail-closed

- **GIVEN** un artefacto ausente, alterado o incompatible con el entorno
- **WHEN** se intenta preparar la evaluacion
- **THEN** la ejecucion real se bloquea sin fixtures, relajacion del loader ni
  sustitucion del artefacto

### Requirement: aislamiento temporal previo a ingesta numerica

El sistema SHALL copiar por streaming solo 2022-12-26..2023-12-31, interpretando
de filas excluidas unicamente fecha estructural, antes de invocar pandas,
agregacion o conversion de sentinelas. SHALL registrar que los bytes posteriores
se recorrieron aunque sus mediciones no se interpretaron.

#### Scenario: filas futuras sin influencia

- **GIVEN** dos CSV mixtos identicos hasta 2023 y distintos en 2024-2025
- **WHEN** se producen snapshots restringidos
- **THEN** sus bytes permitidos y resultados de evaluacion son identicos

### Requirement: comparacion preespecificada sobre casos comunes

El sistema SHALL evaluar por horizonte LR, RF, HGB, promedio, persistencia y
mayoria sobre la interseccion de casos validos, informando disponibilidad y
exclusiones individuales. SHALL conservar 0.5 y P20 contractuales. Un componente
ausente SHALL NOT contarse como voto negativo.

#### Scenario: promedio y mayoria permanecen distintos

- **GIVEN** tres scores disponibles
- **WHEN** se combinan
- **THEN** promedio coincide exactamente con produccion y mayoria usa al menos
  dos decisiones positivas, sin convertir votos en probabilidad

### Requirement: resultados trazables y honestos

El sistema SHALL producir predicciones fechadas, metricas con estado
defined/undefined, confiabilidad de diez bins, episodios descriptivos,
bootstrap pareado por bloques moviles no circulares de 30 dias, manifiesto,
reporte y resumen UI. JSON SHALL usar null y nunca NaN.

#### Scenario: resultado exploratorio

- **GIVEN** que 2023 fue usado antes en el proyecto
- **WHEN** se informa cualquier resultado
- **THEN** se rotula retrospectivo exploratorio no independiente, sin declarar
  ganador confirmatorio, probabilidad acreditada ni utilidad agronomica
