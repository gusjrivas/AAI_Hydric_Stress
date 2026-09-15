# Decisiones abiertas — Etapas B y C de controlled_daily_v4_external_pergamino

Estado: **cuatro propuestas de implementación, de las cuales las Decisiones 1, 2 y 3
fueron adoptadas como decisiones OPERATIVAS de sendos encargos de implementación
(2026-09-14 para la Decisión 1; 2026-09-15 para las Decisiones 2 y 3), nunca
como una aprobación académica externa.** La Decisión 4 permanece con su
pregunta de ubicación exacta sin resolver (ver sección correspondiente). Este
documento no modifica ni reinterpreta `docs/research/controlled-daily-v4-external-pergamino-protocol.md`,
`ADR-0011` ni `ADR-0010`; para cada punto, separa (a) el requisito ya
establecido por el protocolo, de (b) la propuesta técnica de implementación,
de (c) lo que efectivamente permanece como decisión pendiente — las tres
categorías no se mezclan.

**Adopción de las Decisiones 2 y 3 (2026-09-15, encargo "Etapa C y ledger de
protección del holdout"):** se adopta, como decisión operativa de ese
encargo, la propuesta técnica completa ya descrita en la Decisión 2 de este
documento -- ledger transaccional SQLite (biblioteca estándar), ubicación
explícita fuera de `--output-dir`, identidad del holdout independiente de
commit/candidato/directorio/intento, secuencia de apertura exacta (verificar
→ reservar → confirmar con `fsync` → acceder → finalizar), tres estados
(`AUSENTE`/`CONFIRMADA`/`INDETERMINADA`), inicialización explícita separada
de la ejecución, y ledgers sintético/científico separados -- implementada en
`src/experiment_runner/controlled_daily_v4/holdout_ledger.py`. Y de la
Decisión 3: `--overwrite` queda prohibido incondicionalmente para `--stage C`
(`cli.py`), como defensa en profundidad sobre el ledger. Ninguna de las dos
adopciones se atribuye a una aprobación académica externa: son decisiones de
implementación de ese encargo, registradas aquí exactamente como tal, con el
mismo criterio ya usado para la Decisión 1 (ver la nota de adopción original,
más abajo, y `openspec/changes/implement-controlled-daily-v4-stage-b-c/tasks.md`).
Una diferencia respecto de la propuesta técnica original de la Decisión 2: se
elige explícitamente SQLite en vez de un archivo YAML versionado en Git para
el registro persistente -- ambas opciones seguían abiertas en la propuesta
original ("si el ledger debe vivir en un archivo versionado en Git ... o en
un mecanismo distinto"); esta adopción resuelve esa pregunta a favor de
SQLite, por ser transaccional nativamente (sin necesitar reimplementar
control de concurrencia sobre un archivo de texto) y no requerir un commit
de Git por cada intento de apertura del holdout.

Preparado como parte del diagnóstico de cierre de `controlled_daily_v4` (sesión del 2026-09-13, sobre `653dc0d1b15af87cfe2008c5b5ea5583512c1324`). Revisión de una segunda ronda (2026-09-13, posterior al paquete `controlled-daily-v4-docs-close-out-review.zip`, SHA-256 `8073FA9308593C23D4385F28B5BEBE1E6CD466A9B0B2828AD9E16BE6F237935F`) que corrige: (1) el momento y la secuencia de apertura de la Etapa C, que antes permitía repetir el acceso al holdout si la escritura de resultados fallaba después de haberlo consultado; (2) la confusión entre la identidad del holdout protegido y la identidad de cada intento de ejecución, que antes se renovaba incorrectamente al cambiar de commit, candidato o directorio de salida; (3) una exigencia genérica de que la huella del conjunto de A coincidiera con la del entrenamiento de C, que contradice al propio protocolo (C incorpora 2023 y recalcula `P20_train`); y (4) la severidad del rechazo de `depth_role`, antes presentada como abierta entre "error duro" y "advertencia", cuando una advertencia no satisface la separación exigida por el protocolo. Una tercera revisión (2026-09-13, previa a la apertura del PR) corrige además: (5) el commit del productor A y el de la ejecución consumidora pueden coincidir o diferir — ninguna de las dos relaciones se exige ni certifica nada por sí sola (Decisión 2, y las correcciones equivalentes en `proposal.md`/`specs/experiment-runner/spec.md`/`tasks.md`); (6) un registro de apertura de la Etapa C existente, incompleto o incierto (estado `INDETERMINADA`) debe bloquear el acceso automático igual que uno confirmado, sin borrarse ni reinicializarse solo, distinto de un fallo previo a cualquier reserva (estado `AUSENTE`); y (7) el reemplazo atómico de un archivo (`os.replace` en `artifacts.py`) no garantiza durabilidad ante una caída del sistema por sí solo — el registro de apertura exige además `fsync` explícito, una garantía que el código actual de la Etapa A no provee y que esta propuesta no le atribuye. Referenciado desde `openspec/changes/implement-controlled-daily-v4-stage-b-c/proposal.md`.

## Decisión 1 — Segmentación del moving block bootstrap de la Etapa B

### Requisito ya establecido por el protocolo

- Protocolo, sección 10: `ΔMCC_B = MCC_candidato_2023 − MCC_persistencia_2023`; `CANDIDATE_VALIDATED` sii `MCC_candidato_2023 > 0` y el límite inferior del intervalo pareado bootstrap de `ΔMCC_B` es `≥ −0.05`, "moving block bootstrap: bloques de 30 días, 5.000 réplicas, semilla `20250109`, calculado exclusivamente sobre las predicciones de 2023".
- Protocolo, sección 8 ("Implementación del moving block bootstrap: variante no circular"): define el algoritmo segment-aware en términos de "segmentos" de remuestreo independientes, sin cruzar bloques entre segmentos distintos. En la Etapa A esos segmentos son los tres `outer_val` del nested CV.
- La Etapa B, a diferencia de A, no tiene nested CV ni outer folds: es una única evaluación de un candidato ya congelado sobre un único período continuo (2023). El protocolo nunca dice, en ninguna sección, cuántos "segmentos" de remuestreo debe tener esa serie en la Etapa B.

### Propuesta técnica (no codificada todavía)

Tratar las predicciones evaluables de 2023 como **un único segmento continuo** (`segment_id` constante para todas las filas) al invocar `bootstrap.paired_bootstrap_delta` (`src/experiment_runner/controlled_daily_v4/bootstrap.py:166`), sin ninguna subdivisión adicional (ni mensual, ni por fold, ni de ningún otro tipo). La función ya es genérica respecto del número de segmentos (`build_segment_plans`, `bootstrap.py`); usar un único segmento es el caso trivial (`n` segmentos = 1) del mismo algoritmo ya normativo e implementado para la Etapa A — no se propone ninguna partición nueva no mencionada por el protocolo. El período evaluable de B tiene del orden de 360 filas (`target_timestamp ∈ [2023-01-04, 2023-12-31]`, protocolo sección 5), muy por encima de `L=30`, por lo que `SegmentTooShortForBlockError` (`bootstrap.py`) no se activaría.

### Qué permanece pendiente de decisión

Que "un único segmento" sea la lectura correcta de "calculado exclusivamente sobre las predicciones de 2023" (protocolo, sección 10), dado que el protocolo nunca usa la palabra "segmento" al describir la Etapa B. Es una inferencia razonable — B no tiene folds, por lo que no hay ninguna frontera interna que justifique más de un segmento — pero es una inferencia, no una cita textual, y por eso se registra aquí en vez de asumirse en el código.

## Decisión 2 — Identidad del holdout, secuencia de apertura y prevención de repetición de la Etapa C

### Requisito ya establecido por el protocolo

Protocolo, sección 11: evaluación única sobre `[2024-01-04, 2025-12-31]`, "prohibido cualquier ajuste, recalibración o repetición motivada por el resultado, incluso si es negativo"; apertura del holdout como "evento único e irreversible, que requiere registro explícito de fecha y autorización (nombre/rol de quien autoriza)".

### Limitación honesta de partida

Ningún mecanismo de software puede impedir que una persona con acceso de escritura al repositorio edite manualmente un archivo de estado, borre un directorio de salida, o vuelva a calcular la evaluación fuera de la CLI. Lo que sigue es un control **operativo**, que impide la repetición **accidental** a través del flujo normal de la herramienta — no una garantía criptográfica ni a prueba de manipulación deliberada.

### Defecto encontrado en la propuesta anterior (corregido en esta revisión)

La versión anterior de esta propuesta marcaba la evaluación como "consumida" recién **después** de serializar el resultado completo, afirmando además que "todos los artefactos [quedan] escritos atómicamente, igual que en A". Ambas cosas eran incorrectas:

- **Momento equivocado.** Si el holdout ya se consultó (se cargaron valores de 2024–2025 para evaluar) y la escritura de resultados fallaba después, la regla anterior no marcaba nada como consumido — permitiendo un segundo intento que vuelve a acceder al holdout. Eso es exactamente la repetición que el protocolo prohíbe, incluso si nunca llegó a producirse un resultado.
- **Garantía de atomicidad inexistente para el conjunto de artefactos.** Contrastado contra `src/experiment_runner/controlled_daily_v4/artifacts.py`: cada archivo individual sí se escribe de forma atómica (`_atomic_write_text`/`_write_json`, vía `tempfile.mkstemp` + `os.replace`, líneas 112-141) — pero los ~19 artefactos de una corrida se escriben uno por uno, en llamadas `_write_json` sucesivas, **sin ninguna transacción que cubra el conjunto completo**. Un crash entre el archivo 10 y el 11 deja un directorio con un subconjunto parcial de artefactos válidos, no un "todo o nada". Esta entrega no atribuye al código una garantía transaccional que no provee.

### Identidad del holdout ≠ identidad de la ejecución (corrección de esta revisión)

La propuesta anterior derivaba "la identidad de la ejecución" del candidato congelado más el commit de código, y usaba esa combinación como la clave que impedía repetir la apertura. Eso es incorrecto: esa clave se renueva con solo cambiar de commit, de candidato congelado, o de `--output-dir` — exactamente lo que un reintento (accidental o no) haría. El holdout de 2024–2025 es un recurso único y fijo del protocolo; su identidad no puede depender de qué intento particular lo está consultando. Se distinguen ahora dos conceptos separados:

- **Identidad del holdout protegido** (estable, una sola vez para siempre en este protocolo): `protocol_id` + sitio + profundidad + período reservado — por ejemplo, la tupla `(controlled_daily_v4_external_pergamino, Pergamino, soil_moisture_0_to_7cm, 2024-01-04..2025-12-31)`. Es la clave sobre la que se aplica la exclusión: solo puede existir **una** apertura registrada para esta clave, sin importar qué commit, candidato o directorio de salida la solicitó.
- **Registro del intento** (uno por cada invocación que llega a solicitar la apertura): candidato congelado consumido (vía el contrato de transferencia), commit de la ejecución consumidora, identidad del conjunto de datos usado, quién autoriza y cuándo, y el resultado de ese intento. Puede haber, en principio, más de un registro de intento asociado a la misma apertura del holdout (por ejemplo, si el primer intento falló antes de reservar la apertura, ver más abajo) — pero nunca más de una apertura exitosa.

### Secuencia de apertura propuesta (corrige el orden y el momento de consumo)

1. **Verificación previa, sin tocar el holdout.** Antes de acceder a cualquier valor de 2024–2025: verificar el veredicto `CANDIDATE_VALIDATED` persistido de la Etapa B, la autorización (`--authorized-by "<nombre/rol>"`, sin valor por defecto), y las precondiciones de entorno (`environment.validate_environment()`), exactamente igual que en A/B.
2. **Reserva atómica de la apertura, todavía sin tocar el holdout.** Solo si el paso 1 es exitoso: se consulta primero el estado actual del registro persistente para la identidad de este holdout (ver más abajo, "Los tres estados posibles del registro"). Solo si ese estado es `AUSENTE` se intenta la operación de reserva exclusiva (p. ej. creación exclusiva de un registro con la identidad del holdout como clave — semántica equivalente a `O_EXCL`, o un compare-and-swap sobre ese registro). Si el estado es `CONFIRMADA` o `INDETERMINADA`, la ejecución se rechaza inmediatamente, sin haber accedido a ningún dato de 2024–2025 — ver la distinción entre ambos casos más abajo. Esta es también la operación que impide aperturas concurrentes: dos procesos que intenten reservar al mismo tiempo, uno gana y el otro ve el registro ya existente (o en curso).
3. **Registro durable de la apertura, todavía antes del acceso.** Una vez que la reserva exclusiva se confirma, se escribe la marca de apertura (identidad del holdout, timestamp, autorización, e identidad del intento) con una garantía de durabilidad explícita: el contenido debe forzarse a almacenamiento persistente (`fsync` del archivo y, cuando el mecanismo lo permita, del directorio que lo contiene) antes de considerar la apertura confirmada — no basta con que la escritura "regrese sin error" en el proceso. **Esta garantía no está satisfecha hoy por el mecanismo de escritura atómica de `artifacts.py`** (`_atomic_write_text`/`_write_json`, `tempfile.mkstemp` + `os.replace`, líneas 112-141): ese mecanismo evita que un archivo quede a medio escribir o con contenido mezclado (atomicidad del reemplazo), pero no llama a `fsync` en ningún punto, por lo que un corte de energía o una caída del sistema justo después de que `os.replace` retorna, y antes de que el sistema operativo descargue esa escritura a disco, podría perder el archivo o su directorio pese a que la aplicación ya lo dio por escrito. La propuesta para el registro de apertura de la Etapa C **exige explícitamente** el paso adicional de `fsync` que `artifacts.py` no tiene hoy — no se le atribuye esa garantía al código existente; es un requisito nuevo para este mecanismo específico, justificado por que aquí sí importa sobrevivir a una caída exactamente en ese instante. **Recién después de que este registro se confirmó de forma durable** el runner tiene permiso para cargar y evaluar valores de 2024–2025.
4. **Evaluación y serialización de resultados**, exactamente igual que en A/B en cuanto a mecánica de escritura (atómica por archivo, sin transacción de conjunto — ver limitación de arriba); esta fase no requiere la misma garantía de `fsync` inmediato del paso 3, porque para este momento el holdout ya está marcado como abierto de forma durable y su irreversibilidad no depende de que los resultados se terminen de escribir.
5. **Marca de finalización**, escrita al final, una vez que todos los artefactos de resultado quedaron serializados. Es un registro adicional y separado del de apertura (paso 3): indica que existe un resultado completo y dónde encontrarlo. Su ausencia no significa que el holdout siga cerrado — el paso 3 ya lo abrió — significa que no hay un resultado recuperable todavía.

### Los tres estados posibles del registro (no solo dos)

Antes de esta revisión, la propuesta solo distinguía "ya hay una apertura" de "no hay ninguna". Eso omite un tercer estado que debe tratarse de forma distinta a ambos:

- **`AUSENTE`**: no existe ningún registro (ni completo ni parcial) para esta identidad de holdout. Es el único estado en el que el paso 2 puede proceder a intentar una reserva. Corresponde a un fallo *previo a cualquier intento de reserva* (el paso 1 no pasó, o el proceso nunca llegó a invocar el paso 2) — en este caso el holdout no fue tocado y un reintento completo es legítimo.
- **`CONFIRMADA`**: existe un registro de apertura completo, durable y válido (paso 3 ya completado en algún intento anterior). El holdout está abierto de forma permanente; se aplican las reglas de recuperación/no-reintento descritas abajo.
- **`INDETERMINADA`** (nueva distinción de esta revisión): existe *algo* para esta identidad de holdout, pero no se puede establecer con certeza si la apertura llegó a confirmarse — por ejemplo, el proceso se interrumpió durante el propio paso 2 o 3 (mientras se escribía o se hacía `fsync` de la reserva/apertura), o el registro existe pero no pasa su propia validación de forma. **Este estado debe bloquear cualquier acceso automático nuevo al holdout, exactamente igual que `CONFIRMADA`** — nunca se trata como equivalente a `AUSENTE` solo porque no se pudo confirmar que la apertura se completó: en ausencia de certeza, se asume el caso más conservador (que el holdout pudo haber sido accedido). El registro en este estado **no se borra ni se reinicializa silenciosamente** bajo ninguna circunstancia automática; su resolución (confirmar que en efecto nunca hubo acceso real y limpiar el registro, o tratarlo como una apertura ya ocurrida) requiere intervención humana explícita, documentada y fuera del flujo normal de la CLI.

### Consecuencias de esta secuencia frente a los requisitos pedidos

- **Fallos previos a cualquier reserva** (estado `AUSENTE`: durante el paso 1, o si el proceso nunca llegó a intentar el paso 2): el holdout permanece intacto; un reintento completo es legítimo y no está bloqueado.
- **Fallos posteriores a la apertura confirmada** (estado `CONFIRMADA`, durante los pasos 4 o 5): el holdout queda marcado como abierto de forma permanente, exista o no un resultado serializado. No hay reintento automático de la evaluación en ningún caso posterior a la apertura — ni exitoso ni fallido.
- **Reservas incompletas o inciertas** (estado `INDETERMINADA`, ver arriba): bloquean todo acceso automático nuevo igual que `CONFIRMADA`, pero no permiten (todavía) aplicar las reglas de recuperación de `CONFIRMADA` porque no hay certeza de que exista o no un resultado — es un estado excepcional propio, distinto de los otros dos, que requiere la misma intervención humana explícita que el caso de "apertura confirmada sin marca de finalización" (ver el punto siguiente), pero detectado más temprano en la secuencia.
- **Recuperar un resultado ya calculado ≠ volver a evaluar.** Si el estado es `CONFIRMADA` y existe la marca de finalización del paso 5, una invocación posterior con la misma identidad de holdout debe **leer y reportar** el resultado ya serializado, nunca recomputarlo. Si el estado es `CONFIRMADA` pero la marca de finalización (paso 5) no existe, o si el estado es `INDETERMINADA`, no hay ningún resultado que recuperar automáticamente y tampoco está permitido evaluar de nuevo — son estados terminales excepcionales que requieren intervención humana explícita y documentada fuera de la CLI (por ejemplo, para decidir si el intento se declara perdido y se deja constancia de las circunstancias); esta propuesta no automatiza esa decisión ni promete resolverla por software.
- Esto es un control operativo del flujo normal de la herramienta, no una garantía contra la manipulación manual deliberada del registro persistente (ver "Limitación honesta de partida", arriba).

### Registro persistente, aislamiento sintético/científico e inicialización explícita

- **Estado persistente entre procesos y contenedores**, fuera del `--output-dir` efímero (que cambia en cada invocación y por lo tanto no puede ser la ubicación de la exclusión) — en una ubicación fija y versionada, por ejemplo `docs/research/controlled-daily-v4-external-pergamino-stage-c-holdout-ledger.yaml`, bajo control de Git, con la identidad del holdout como clave.
- **Inicialización explícita del registro científico.** El archivo del ledger científico debe existir desde su creación con un estado inicial explícito (`AUSENTE` para la identidad del holdout, es decir "nunca abierto"), versionado en Git igual que el manifiesto de provenance — nunca inferido de su ausencia. Si el runner no puede leer ese archivo (no existe cuando debería, está corrupto, es ilegible, o la entrada de esta identidad de holdout no valida contra su forma esperada), el estado se trata como `INDETERMINADA`, no como `AUSENTE`: debe fallar explícitamente y bloquear el acceso, nunca asumir "nunca abierto" ni reinicializar el archivo automáticamente. La ausencia inesperada o el deterioro del registro no equivalen a que el holdout esté cerrado; equivalen a un estado que requiere revisión humana antes de continuar.
- **Registros sintéticos aislados.** Las pruebas de integración sintética (incluida la del flujo A→B→C completo) usan un ledger completamente separado (otra ruta de archivo, o un espacio de claves distinto, provisto explícitamente por el test) que nunca lee ni escribe el ledger científico real. Esto permite probar toda la secuencia de apertura (incluida la reserva exclusiva, el rechazo de una segunda apertura, y los tres estados del registro) sin ningún riesgo de interferir con el estado científico real, y sin necesitar datos reales para hacerlo.

### Qué permanece pendiente de decisión

- Si el registro de intento debe incluir, además del candidato congelado y el commit de la ejecución consumidora, la identidad del propio conjunto de datos de C (en principio fija, dado que 2024–2025 es un período cerrado, pero podría variar si cambiara la fuente).
- Si el ledger debe vivir en un archivo versionado en Git (visible, auditable, pero requiere un commit para registrar cada intento) o en un mecanismo distinto — la elección concreta también determina qué mecanismo de `fsync`/durabilidad y qué forma de validación de "registro completo vs. `INDETERMINADA`" son aplicables (un archivo de texto versionado en Git y un mecanismo de otro tipo no comparten la misma implementación de esas garantías, aunque sí el mismo requisito).
- Si corresponde una autorización adicional específicamente para el *primer* intento (apertura del holdout en sí, protocolo sección 11) distinta de la autorización de cada intento individual.
- Cuál es el procedimiento exacto (manual, fuera de la CLI) para resolver un registro en estado `INDETERMINADA`: quién puede declararlo resuelto, qué evidencia debe registrar esa resolución, y si queda un rastro auditable de que ocurrió.

**Resuelto (2026-09-15, encargo "Etapa C y ledger de protección del
holdout"):** el mecanismo de persistencia es SQLite (biblioteca estándar), no
un archivo versionado en Git -- ver la nota de adopción al comienzo de esta
sección. El registro de intento (`holdout_registry`, `reserved_by_attempt_id`)
incluye un identificador de intento arbitrario (UUID por invocación), pero
deliberadamente NO incluye la identidad del conjunto de datos de C como
condición de exclusión (la exclusión es exclusivamente por `holdout_key`,
independiente del intento) -- la identidad de fuente de C sí se verifica por
separado, después de la apertura confirmada, como condición de admisibilidad
de esa evaluación concreta (ver `cli.py::_run_stage_c`), no como parte de la
clave del ledger. La autorización (`--authorized-by`) se exige en cada
invocación científica de `--stage C`, sin distinguir "primer intento" de
intentos posteriores -- una vez `CONFIRMADA`, no hay intento posterior
posible para la misma identidad de holdout, por lo que esa distinción no
tiene efecto práctico bajo este diseño. El procedimiento para resolver un
registro `INDETERMINADA` sigue siendo manual y fuera de la CLI: no se
implementó (ni se propone) ningún comando automático de la CLI para
inspeccionar, resetear o liberar una fila del ledger -- una intervención
directa sobre el archivo SQLite (por ejemplo, con la herramienta `sqlite3`)
queda fuera del alcance de este paquete, documentada aquí como límite
explícito, no como automatización pendiente.

## Decisión 3 — Política de `--overwrite` para la Etapa C

### Requisito a preservar

El mismo de la Decisión 2: irreversibilidad de la evaluación de la Etapa C.

### Por qué se separa de la Decisión 2

Es una pregunta de política de CLI, no de mecanismo de identidad/ledger: `--overwrite` ya existe hoy, de forma genérica, para las etapas ya implementadas (permite reejecutar sobre un directorio no vacío). Con el ledger de la Decisión 2 ya keyado por la identidad del holdout (no por `--output-dir`), `--overwrite` ya no puede evadir la exclusión cambiando de directorio — pero puede seguir preguntándose si conviene prohibirlo igual, como capa adicional.

### Propuesta técnica (no codificada todavía)

Que, específicamente para `--stage C`, la CLI rechace incondicionalmente el flag `--overwrite`, como capa adicional de defensa en profundidad sobre el ledger de la Decisión 2 — no porque `--overwrite` pudiera evadir el ledger (ya no puede, tras la corrección de esta revisión), sino para no depender de un único mecanismo.

### Qué permanece pendiente de decisión

Si esta prohibición incondicional es necesaria además del ledger (defensa en profundidad) o redundante (y por lo tanto innecesaria) una vez que el ledger de la Decisión 2 esté aprobado e implementado.

**Resuelto (2026-09-15, encargo "Etapa C y ledger de protección del
holdout"):** se adopta la prohibición incondicional como defensa en
profundidad, no porque el ledger de la Decisión 2 pudiera evadirse sin ella
(no puede: la exclusión es por `holdout_key`, no por `--output-dir`), sino
para no depender de un único mecanismo -- `cli.py` rechaza `--overwrite` con
`--stage C` antes de cualquier otra verificación, incondicionalmente.

## Decisión 4 — Ubicación de `depth_role` en los artefactos

### Requisito ya establecido por el protocolo

Protocolo, sección 2: la profundidad de sensibilidad (7–28 cm) "corre en paralelo, no interviene en la selección del análisis principal, se reporta por separado".

### Lo que ya está resuelto y NO es una decisión abierta

- **Que exista un campo que distinga corrida principal de corrida de sensibilidad** no es una decisión abierta: es la aplicación directa del requisito de arriba.
- **Que esa restricción se verifique en el punto de consumo de la Etapa B** (no en la escritura de la Etapa A, ni en un lector genérico desacoplado del contexto de uso) tampoco es una decisión abierta: se sigue de que la restricción del protocolo es sobre el *uso* del resultado de sensibilidad, no sobre su existencia.
- **La severidad del rechazo tampoco es ya una decisión abierta.** La revisión anterior de este documento la presentaba como abierta entre "error duro" y "advertencia registrada que no bloquea". Se corrige: una advertencia que permita, aunque sea con una nota registrada, sustituir al candidato principal por uno de sensibilidad en el flujo que alimenta la Etapa B **no satisface** la separación que el protocolo exige — el protocolo no dice "advertir", dice "no interviene". Por lo tanto el rechazo en el punto de consumo de la Etapa B es **siempre un error duro** (aborta la operación de admisibilidad), sin excepción y sin modo de advertencia. Esto no impide la lectura **estructural** de un artefacto de sensibilidad (que sigue funcionando igual para cualquier `depth_role`, ver el requirement de lectura estructural del *change*), ni crea un experimento nuevo o una ruta paralela para la profundidad de sensibilidad — únicamente bloquea que ese artefacto se use para congelar un candidato de la Etapa B.

### Propuesta técnica (no codificada todavía)

`depth_role` (`primary_selection` | `sensitivity_only_no_selection_effect`) se registra **únicamente en `frozen_config.json`** — el artefacto que efectivamente consume la Etapa B — derivado automáticamente de `--depth`, sin representación mínima adicional duplicada en otros artefactos.

### Qué permanece pendiente de decisión

Si, pese a la propuesta de arriba, conviene además duplicar `depth_role` en `selection_decision.json` con una verificación cruzada de consistencia entre ambos — por ejemplo, para poder auditar la profundidad de una corrida sin necesidad de leer `frozen_config.json`. La propuesta por defecto de esta revisión es **no duplicarlo** (un único lugar de verdad, más simple de mantener consistente), pero la decisión final queda abierta.

No se altera la metodología del protocolo en ninguna de las cuatro decisiones: cada una describe un mecanismo de control de acceso/trazabilidad para hacer cumplir un requisito ya normativo, no introduce un requisito científico nuevo. Ninguna fue aprobada en esta sesión ni en ninguna anterior.
