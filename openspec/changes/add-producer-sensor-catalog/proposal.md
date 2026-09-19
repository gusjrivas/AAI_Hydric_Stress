# Change: Catálogo de sectores, puntos y lecturas para productores

Estado: primera entrega implementada y validada en
`feat/hu6-backend-soporte-ui`; change todavía no archivado. No modifica specs
canónicas ni resultados históricos.

## Why
La UI exige escribir códigos de sensores y no expone el conjunto de lecturas
que alimenta la predicción. Dar de alta un nombre no debe simular datos o
hacer creer que un equipo está conectado.

## What Changes
Catálogo persistente de sectores y puntos, selección explícita de la serie de
pronóstico, consulta de lecturas por ventana y metadatos de procedencia/unidades.
Servicios de datos reutilizables; exposición HTTP a cargo de add-producer-forecast-api.

## Trazabilidad
HU2, Épica 1; capacidad data-ingestion. CRISP-DM comprensión/preparación de datos.
Relación HU6: presentación. Capa 2 con contrato de almacenamiento existente.
Configuraciones base/+sintéticos/+anomalías/completa: sin cambios.
Hipótesis/alcance/arquitectura: sin cambios; ampliación de metadatos operativos,
registrada en ADR-0013 propuesto. HU7/HU8 y datos históricos intactos.
Memoria: capítulo 3; capítulo 2 conserva procedencia y aislamiento.

## Fuera de alcance
Hardware, autenticación productiva, sensores cruzados, eliminación de datasets,
generación de backfill por HTTP y modelo agronómico del mock.
