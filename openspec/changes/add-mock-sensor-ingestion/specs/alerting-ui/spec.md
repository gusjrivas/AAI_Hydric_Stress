# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Ingesta de lecturas de sensores desde la interfaz de datos

El sistema DEBE poder recibir una lectura individual (timestamp y valores, parcial permitido) y agregarla al dataset configurado, sin distinguir si el origen es un sensor real o un generador sintético. El timestamp se normaliza a granularidad diaria (medianoche, sin timezone); una segunda lectura del mismo día reemplaza a la anterior en vez de duplicarla.

#### Scenario: Ingesta de una lectura válida

- **GIVEN** el dataset configurado por `ALERTING_UI_DATASET`, con o sin historia previa
- **WHEN** se envía una lectura con timestamp y al menos un valor de columna obligatoria
- **THEN** la lectura queda persistida como una fila nueva de ese dataset, con procedencia según lo indicado en la lectura

#### Scenario: El dataset en vivo es independiente del dataset histórico de investigación

- **GIVEN** el dataset histórico `melchor_romero_2024_consolidado` ya usado para verificar HU7/HU8
- **WHEN** se ingieren lecturas de sensores sobre un dataset configurado con otro nombre
- **THEN** el dataset histórico permanece sin modificaciones
