# AGENTS.md

## Orquestacion autonoma del cierre cientifico

Para HU7/HU8 leer openspec/scientific-closure/README.md, la spec
openspec/specs/scientific-closure/spec.md, matriz y change seleccionado.
OpenSpec es la fuente normativa del trabajo; protocolo v4 y decisiones
preejecucion conservan autoridad cientifica. No modificar v3.
Preparacion NO autoriza ejecutar A/B/C ni abrir holdouts.

- Seleccionar solo cambios aprobados con dependencias y gates satisfechos.
- scientific_explorer reune evidencia antes de implementar, sin modificar.
- scientific_implementer realiza un cambio acotado, prueba y registra evidencia.
- Un solo escritor por archivo; asignar rutas y congelar snapshot para revision.
- evidence_checker verifica resultados mecanicos, sin decisiones cientificas.
- scientific_critic intenta refutar criterios sin modificar el cambio.
- Hallazgos materiales vuelven al implementador; repetir pruebas y critica.
- scientific_auditor independiente interviene despues de superar las criticas.
- Cerrar un change solo con PASS del auditor sobre el snapshot revisado.
- FAIL vuelve al implementador; BLOCKED se registra y suspende dependientes.
- No avanzar A a B sin gate A; ni B a C sin gate B y permisos especificos.
- Nunca declarar cerrado el Trabajo Final unicamente por tests verdes.
- Ausencia de mejora general o resultado negativo valido no es error a corregir.
- Prohibido seleccionar modelos o conclusiones usando el holdout final.
- Prohibido completar evidencia faltante mediante inferencias.
- Toda ejecucion registra commit, imagen, configuracion, semillas, datos,
  hashes, comandos, entorno y resultados; distinguir SHA documental/ejecutable.
- Distinguir hechos, resultados, inferencias, limitaciones y trabajo pendiente.
- R/H/N/S solo se activan por necesidad de afirmaciones y alcance aprobado.
- Maximo cuatro subagentes, limitado ademas por capacidad efectiva del runtime.
- Usar .codex/agents; verificar modelo/esfuerzo/sandbox efectivo y documentar
  sustituciones o degradacion. Lectores no solicitan escritura.

Procedimientos: openspec/scientific-closure/operations.md. El orquestador
conserva informes exactos de lectores. Checkpoints no equivalen a PASS.
En preparacion: sin push, main/UI, merge, rebase, tag, release, PR ni A/B/C.

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

## Uso eficiente del contexto

No releer todo el repositorio para tareas acotadas.

Usar, en este orden:

1. `AGENTS.md`;
2. la spec de la capacidad afectada en `openspec/specs/`;
3. el ADR correspondiente;
4. los archivos directamente relacionados con la tarea.

Ampliar el contexto solo si aparece una dependencia, inconsistencia o impacto metodológico relevante.

Para tareas localizadas, evitar recorrer módulos, documentación o resultados históricos que no estén relacionados con el cambio.

Objetivo: reducir consumo innecesario de contexto y tokens en Codex y otros agentes, manteniendo la trazabilidad metodológica.
