# AGENTS.md

Este repositorio implementa el Trabajo Final de la Maestría en Inteligencia Artificial FIUBA.

## Fuente de verdad

Antes de realizar cambios, leer:

- `openspec/project.md`
- la spec correspondiente en `openspec/specs/<capacidad>/`
- ADR relacionados en `docs/adr/`
- `docs/research/protocolo-experimental-v3.md` para tareas HU7/HU8 o cambios metodológicos.

No duplicar en prompts el contenido de estos documentos.

## Trazabilidad

Todo cambio debe identificar:

- HU afectada;
- capacidad OpenSpec;
- fase CRISP-DM;
- impacto sobre configuración experimental;
- impacto sobre hipótesis, alcance o arquitectura, si existiera.

Mapa principal:

- HU2 → `data-ingestion`
- HU3 → `data-quality`
- HU4 → `predictive-modeling`
- HU5 → `human-feedback`
- HU6 → `architecture-integration`
- HU7 → `experiment-runner`
- UI → `alerting-ui`

## Reglas metodológicas

- IA es el núcleo del trabajo.
- IoT/sensores son fuentes de datos, no contribución central.
- No introducir data leakage.
- Respetar causalidad temporal.
- No optimizar mirando test.
- Preservar corridas históricas.
- No cambiar hipótesis, propósito, alcance ni arquitectura sin advertencia explícita.
- Deep Learning no es obligatorio.
- El sistema es apoyo a la decisión, no automatización del riego.

## Protocolo experimental

Para cualquier cambio que afecte experimentos, leer primero:

`docs/research/protocolo-experimental-v3.md`

No modificar `controlled_daily_v3` salvo bug metodológico demostrado.

## Validación

Antes de considerar finalizado un cambio relevante:

- ejecutar tests afectados;
- mantener trazabilidad;
- no modificar resultados históricos;
- reportar cualquier impacto sobre HU7/HU8 y memoria técnica.

## Memoria técnica

Las decisiones técnicas deben poder justificarse en:

- Capítulo 2: metodología y fundamento científico.
- Capítulo 3: arquitectura e implementación.

Evitar funcionalidad que no aporte a estos objetivos.
