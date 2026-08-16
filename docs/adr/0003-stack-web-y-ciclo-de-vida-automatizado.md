# ADR-0003: Stack web (backend/frontend) y ciclo de vida de desarrollo automatizado con IA

## Estado

Aceptado (2026-08-16)

## Contexto

ADR-0001 define la capa 4 (salidas) de la arquitectura como "alertas de estrés en tiempo real, paneles de monitoreo, recomendaciones de riego", sin fijar su implementación concreta. ADR-0002 fija el stack de modelado y persistencia (Python, MLflow, contrato de acceso a datos), pero no cubre cómo se expone esa información a un usuario ni cómo se gobierna el ciclo de vida de desarrollo del proyecto.

Todo el desarrollo de este trabajo de tesis se realiza mediante Claude Code como único agente de implementación, sin otro desarrollador humano que revise pull requests. Esta condición cambia el cálculo habitual de gobernanza de un equipo: no hay un revisor humano que detecte por inspección si un cambio se aparta del plan de tesis o si se pierde trazabilidad entre código y las historias de usuario (HU1-HU8) del backlog. La auditoría registrada en `docs/seguimiento-tareas.md` ya identificó este riesgo: "los PRs anteriores pueden haber transmitido una sensación de avance más rápida de lo real, porque cada PR fue un artefacto concreto... pero 'artefacto creado' no es lo mismo que 'tarea del plan de tesis completada'".

Es necesario, entonces, fijar dos cosas antes de continuar con la implementación de código de las capas 3 y 4: el stack técnico para exponer alertas y paneles de monitoreo, y un mecanismo automatizado que sostenga la trazabilidad entre código y plan de tesis sin depender de la disciplina manual del agente en cada sesión.

## Decisión

### Backend y frontend (capa 4 de ADR-0001)

Se adopta **FastAPI** (Python) como backend y **React** como frontend, dentro del mismo repositorio (monorepo), en carpetas `backend/` y `frontend/` nuevas, sin scaffolding inicial hasta que exista una historia de usuario que las requiera (HU5 en adelante).

El backend constituye una **fachada delgada** sobre las capas 1-3 de ADR-0001: dentro del mismo proceso y entorno de ejecución, importa y llama directamente a las librerías Python de datos y modelado (`src/`), y expone esos resultados mediante endpoints HTTP para que el frontend los consuma. El backend no incorpora lógica de negocio propia (orquestación de cuándo correr ingesta, entrenamiento o generación de alertas): esa lógica permanece en las capas 1-3, invocada por el backend, no reimplementada en él.

Esta decisión no contradice el rechazo de microservicios de ADR-0001: no hay comunicación por red entre capas internas, solo entre el backend (capa 4) y el frontend, que es la separación estándar de cualquier aplicación web de dos niveles. Mantener el backend como fachada delgada, en lugar de agregarle lógica de orquestación propia, es lo que preserva la posibilidad de escalar más adelante: si en una fase posterior se necesita extraer una pieza como servicio independiente (por ejemplo, un proceso de entrenamiento pesado separado de la exposición HTTP), el límite entre capas ya existe y ya está limpio, sin lógica de negocio mezclada en el backend que deba desacoplarse primero.

### Estructura de repositorio

Se mantiene un único repositorio (monorepo) con la siguiente organización de alto nivel:

```
src/               # capas 1-3: paquetes Python de datos y modelado (ya existente)
backend/           # capa 4: app FastAPI (se crea cuando una HU lo requiera)
frontend/          # capa 4: app React (se crea cuando una HU lo requiera)
tests/             # tests de src/ (ya existente)
docs/, openspec/   # gobernanza y especificación (ya existente)
```

### Integración continua (CI)

Se incorpora un workflow de GitHub Actions (`.github/workflows/ci.yml`) que ejecuta, en cada pull request contra `main`, lint (`ruff check`) y verificación de formato (`black --check`) sobre `src/`, además de la suite de tests (`pytest`). Esto convierte la corrección del código en evidencia verificable de forma automática, en lugar de depender de la palabra del agente que lo generó, criterio alineado con la exigencia de reproducibilidad de la sección 12.1 del plan de tesis.

El alcance actual del CI se limita al código Python existente. Cuando se cree contenido en `backend/` o `frontend/`, se agregan jobs adicionales acotados a esas carpetas (mediante filtros de ruta), sin modificar el job de Python existente.

### Gate de trazabilidad OpenSpec/ADR/seguimiento

Se incorpora un hook de Claude Code que intercepta la ejecución del comando `gh pr create` y bloquea la apertura del pull request si:

1. El diff de la rama contra `main` no referencia ningún *change* de `openspec/changes/` ni menciona explícitamente una historia de usuario (HU1-HU8) en el título o el cuerpo del PR, o
2. El diff modifica archivos bajo `src/` o `docs/research/` sin modificar también `docs/seguimiento-tareas.md`.

La condición 1 se verifica tanto en el título/cuerpo del PR (la cadena de comando de `gh pr create`) como en los mensajes de commit de la rama (`git log origin/main..HEAD`): cualquiera de los dos lugares donde aparezca la referencia a una HU alcanza. Esto es deliberado, no una relajación accidental: reduce falsos negativos, porque es fácil olvidar restatear la HU al abrir el PR pero casi siempre queda registrada en el historial de commits de la rama.

Este mecanismo reemplaza, para el caso puntual de la trazabilidad plan-de-tesis-a-código, la función que en un equipo tradicional cumpliría un revisor humano: convierte una convención hoy documentada en `openspec/project.md` (sección "Convenciones para *changes*") pero no verificada, en una condición mecánicamente exigida antes de integrar cualquier cambio a `main`.

El hook admite un salvado explícito para el caso descrito en "Consecuencias" (PR fuera del esquema de trazabilidad, sin HU asociada): la variable de entorno `SKIP_PR_TRACEABILITY=1` hace que el script permita la operación sin evaluar ninguna regla, dejando registro en stderr de que el bypass se usó. Uso: `SKIP_PR_TRACEABILITY=1 gh pr create ...`.

## Alternativas consideradas

- **Backend y frontend en repositorios separados**: se descarta porque introduce coordinación de versionado entre dos repositorios para un proyecto de tesis de un único desarrollador (asistido por IA), sin beneficio proporcional al costo de esa coordinación.
- **Backend con lógica de orquestación propia** (en lugar de fachada delgada): se descarta porque acopla la decisión de cuándo ejecutar ingesta/modelado/alertas al proceso HTTP, lo cual dificulta extraer esa lógica como proceso independiente si el proyecto escala, y duplica responsabilidades que ya corresponden a las capas 1-3 según ADR-0001.
- **Frontend en Streamlit u otra solución integrada backend+frontend**: se descarta en favor de FastAPI + React por decisión explícita del autor de separar ambas responsabilidades, aun a costa de mayor esfuerzo de configuración inicial que una solución integrada.
- **Validación de trazabilidad únicamente por convención documentada** (sin hook): se descarta porque, en ausencia de un revisor humano, una convención no verificada mecánicamente depende de que el propio agente que genera el código recuerde aplicarla en cada sesión, lo cual ya demostró fallar parcialmente según la auditoría de `docs/seguimiento-tareas.md`.
- **Validación de trazabilidad en cada commit local** (en lugar de solo al abrir el PR): se descarta por ahora porque introduce ruido durante el trabajo incremental previo a que un conjunto de commits constituya un PR completo; puede reevaluarse si se detectan PRs abiertos con historial de commits ya problemático.
- **Scaffolding inmediato de `backend/` y `frontend/` vacíos**: se descarta porque no hay todavía una historia de usuario que los requiera (HU5 en adelante); crear código sin una tarea que lo motive contradice el criterio de no anticipar abstracciones antes de que se necesiten.

## Consecuencias

- Antes de implementar HU5 (retroalimentación humana, primera HU que probablemente requiera exposición de alertas) debe crearse el scaffolding real de `backend/` y `frontend/`, momento en el cual el CI se extiende con los jobs correspondientes.
- El backend no debe, en ningún caso, incorporar lógica de decisión sobre modelos, anomalías o generación de datos sintéticos: esa lógica pertenece a `src/` y se invoca desde el backend, no se reimplementa en él. Revisar este límite en cada PR que toque `backend/`.
- Todo PR queda sujeto al hook de trazabilidad: un cambio que no referencie una HU o un *change* de OpenSpec no puede abrirse como pull request. Si en algún momento se requiere un PR fuera de ese esquema (por ejemplo, una corrección de emergencia sin HU asociada), el hook debe poder salvarse explícitamente, no eliminarse.
- El CI agrega `ruff` y `black` como dependencias de desarrollo (`[project.optional-dependencies].dev` en `pyproject.toml`), sin afectar las dependencias de ejecución del paquete.
- La ausencia de un revisor humano se compensa parcialmente con CI y el hook de trazabilidad, pero ninguno de los dos reemplaza una revisión de diseño o de calidad de código; ambos verifican forma y trazabilidad, no corrección conceptual.

## Referencias

- [ADR-0001: Arquitectura modular para la detección temprana de estrés hídrico](0001-arquitectura-modular-deteccion-estres-hidrico.md)
- [ADR-0002: Stack técnico del prototipo experimental](0002-stack-tecnico-poc.md)
- `docs/seguimiento-tareas.md` — auditoría que identifica el riesgo de trazabilidad que este ADR busca mitigar.
- `openspec/project.md`, sección "Convenciones para *changes*".
- Plan de proyecto del Trabajo Final — Maestría en Inteligencia Artificial, Esp. Lic. Gustavo Julián Rivas, FIUBA (v4.1, 2026-08-01), sección 12.1.
