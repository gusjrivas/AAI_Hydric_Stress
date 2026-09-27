## ADDED Requirements

### Requirement: Narrativa canónica de tesis y defensa

El sistema SHALL mantener una única narrativa documental vigente para HU7/HU8
que preserve el veredicto de RB-05, diferencie evidencia exploratoria de
confirmación y conserve íntegros los registros históricos superseded.

#### Scenario: Estado vigente consistente

- **GIVEN** RB-05 ejecutada con veredicto `FAIL`, GD-40 y las decisiones auditadas sobre H y R/N/S
- **WHEN** una persona consulta README, checkpoint, siguiente sesión, matriz, claims o síntesis
- **THEN** encuentra `sc-06`, `SC-GOV-025` y `GF` en `FAIL`; H ejecutado y auditado; R/N/S `NOT_APPLICABLE` a nivel requisito con sus changes bloqueados por gate negativo; y B/C como evidencia retrospectiva exploratoria

#### Scenario: Historia preservada

- **GIVEN** documentos que registran estados anteriores verdaderos en su momento
- **WHEN** esos estados dejan de ser vigentes
- **THEN** se conservan como historia con una cabecera supersesora y no se borran ni reescriben eventos, evidencia o informes

#### Scenario: Sin nueva ejecución científica

- **GIVEN** que la campaña v4 terminó y el holdout fue consumido
- **WHEN** se normaliza la documentación para la tesis
- **THEN** no se ejecutan A/B/C ni auxiliares, no se inicializan ledgers, no se inspecciona ni reabre el holdout y no se declara una campaña pendiente

#### Scenario: Tres carriles de evidencia separados

- **GIVEN** evidencia formal v3 de Melchor Romero, resultados v4 A/B/C/H de Pergamino y una demostración técnica posterior del ensamble en Pergamino
- **WHEN** se redacta la posición de defensa
- **THEN** cada carril declara objeto, resultados permitidos, límites y fuentes propias, sin presentar el ensamble demostrativo como reejecución o confirmación de v4

#### Scenario: Semántica exacta de la alerta del ensamble

- **GIVEN** tres probabilidades calibradas, sus votos individuales y el umbral común 0,5
- **WHEN** se describe la alerta vigente
- **THEN** se identifica `combined_alert` como comparación del promedio aritmético contra el umbral, `positive_votes` y `agreement_category` como metadata, la mayoría como cambio futuro no implementado y `display_probability` como no calificada

#### Scenario: Circuitos de feedback no equivalentes

- **GIVEN** review v2, review histórico, recalibración legacy/HU5 y complemento H
- **WHEN** se explica el feedback en la defensa
- **THEN** se declara que los reviews registran una opinión sobre `combined_alert` sin modificar los nueve bundles ni recalibrar, que `/recalibrate/{sensor_id}` es un circuito manual separado de un solo modelo, y que H es una simulación sin evidencia de beneficio humano
