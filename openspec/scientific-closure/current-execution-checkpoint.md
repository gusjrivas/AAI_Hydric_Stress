# Checkpoint de ejecución actual

## Estado vigente — 2026-09-21, CAMPAÑA A → B → C EJECUTADA

Esta sección **reemplaza toda lectura de las secciones posteriores**, incluida la
de «2026-09-21, integración de `origin/main`», que se conserva íntegra como
registro histórico. Varias afirmaciones de esas secciones **eran ciertas hasta el
2026-09-21 y dejaron de serlo ese mismo día**; se identifican abajo una por una
para que nadie las lea como vigentes.

**Qué hizo esta sesión.** Resolvió el readiness por comprobación directa, creó el
respaldo científico externo con ensayo de recuperación, y **ejecutó la campaña
A → B → C completa** dentro de la imagen histórica aprobada. **El holdout
2024–2025 fue abierto**: evento único, autorizado nominalmente e **irreversible**.

**Afirmaciones anteriores que HOY SON FALSAS** (no reescribo las secciones
históricas; las corrijo aquí):

- «`evidence/` y `ledger/` de la raíz de runtime siguen vacíos» — **falso desde
  el 2026-09-21**: contienen la evidencia de A, B, C, la sensibilidad 7–28 cm,
  gobernanza, y dos ledgers SQLite.
- «A, B y C **no** se ejecutaron» — **falso**: las tres se ejecutaron con exit 0.
- «el holdout 2024–2025 permanece cerrado y ningún valor reservado fue leído» —
  **falso**: fue abierto el 2026-09-21T04:06:11Z, estado del ledger `CONFIRMADA`.
- «el ledger definitivo **no** está inicializado» — **falso**: inicializado como
  operación separada previa a C.
- **EXT-02 resuelto**: el daemon Docker responde desde esta distro y ejecuta la
  imagen aprobada. La afirmación de inalcanzabilidad es histórica.
- **EXT-03 resuelto**: `/mnt/scientific-backup` es el disco USB 1 (serie
  8986451183503575922), físicamente distinto del NVMe (disco 0) que respalda el
  `ext4.vhdx` de WSL. Verificado con `Get-Disk`/`Get-Partition`.

**Identidad de la campaña.**

| Concepto | Valor |
| --- | --- |
| SHA ejecutable | `214735e42ee04f018156cd630591e798aadd8bf3` (embebido en la imagen, `dirty=false`) |
| SHA documental | `37eed42716803baa9bdbed912356b981adac093a` |
| Imagen | `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af` |
| Entradas | ERA5 `318edffb…f485f`, NASA POWER `415b4f71…2202b` |
| Semillas | bootstrap 20250109, modelo 42 |

**Resolución de GD-25 / RK-09 (SC-GOV-009).** La sección histórica establecía que
«ninguna afirmación de identidad ejecutable puede apoyarse ya en `214735e`». Esa
regla se levanta **con evidencia, no por redacción**: `214735e` **sí** es ancestro
de `37eed42` (verificado con `git merge-base --is-ancestor`), y el delta de siete
archivos de `src/experiment_runner/controlled_daily_v4/` fue clasificado archivo
por archivo como **sin efecto sobre resultados numéricos** —sólo mensajes,
docstrings, `pd.Timedelta(days=3)` → `HORIZON_DAYS` (=3), un literal sustituido
por su constante homónima, una impresión a stderr, y un motivo adicional
(`bootstrap_not_executed`) que sólo aplica al caso monoclase de B, que no ocurrió.
Dos auditores independientes verificaron esa clasificación por su cuenta. Detalle
en `evidence/environment-identity.json`. La campaña declara `214735e` como
identidad ejecutable y `37eed42` como documental, que es exactamente la
distinción que AGENTS.md exige.

**Resultados (sin sobreinterpretación).**

- **A** — `SIN_GANADOR_ESTABLE`. Las cuatro familias dentro de δ=0.05 y todos los
  intervalos pareados contra la mejor incluyen el cero. **Ninguna demostró
  superioridad.** `logistic_regression` se congeló por **desempate predeclarado de
  simplicidad**, nunca por superioridad. Resultado negativo válido.
- **B** — `CANDIDATE_VALIDATED` (MCC 0.7014 > 0; límite inferior −0.0146 ≥ −0.05).
  **Es una compuerta de NO INFERIORIDAD:** el intervalo [−0.0146, +0.2092]
  **incluye el cero**, así que **no** se demuestra superioridad frente a
  persistencia.
- **C** — holdout 2024–2025. MCC candidato 0.6648 frente a persistencia 0.5734;
  ΔMCC [+0.0227, +0.1784], que **excluye el cero**. El protocolo **no define
  criterio de aceptación para C**: se reporta tal cual. **No** confirma la
  hipótesis general del Trabajo Final, **no** es validación agronómica y **no**
  revierte retroactivamente el empate de A.
- **Sensibilidad 7–28 cm** — también `SIN_GANADOR_ESTABLE`; su MCC más alto
  refleja mayor suavidad y autocorrelación del reanálisis a más profundidad, no un
  mejor modelo. No interviene en ninguna selección.

**Limitaciones detectadas por la auditoría final y ahora declaradas.**

- **Calibración degradada en el holdout**: bin 0.9–1.0 predice 0.9643 y observa
  0.6627 (n=83). El Brier y el ROC-AUC no lo revelan. Sólo la decisión binaria al
  umbral 0.5 está sostenida; las probabilidades **no** son riesgo calibrado.
- **Deriva de prevalencia**: 33.3 % (A) → 26.5 % (B) → 17.6 % (C). El MCC no es
  invariante a la prevalencia, así que los tres valores **no** son directamente
  comparables entre sí.
- **Costo operativo**: en C, 75 días de aviso falso en 26 rachas sobre 728 días,
  precisión 0.6032, 2 episodios no detectados.
- Un solo sitio (Pergamino), datos de **reanálisis**, sin mediciones de campo.

**Estados de requisitos.** `sc-01` a `sc-05` quedan en `PASS` en `changes.json`.
`sc-06` a `sc-10` siguen **BLOCKED**: el complemento **H (HITL) está declarado
`REQUIRED` en `claims.md` y no tiene runner implementado ni evidencia**, de modo
que el **gate GF no es alcanzable hoy** y el cierre científico global permanece
abierto. Esto **no** es un defecto de la campaña: es alcance no ejecutado.

**Lo que la próxima sesión NO debe hacer.** No repetir A, B ni C: están
consumidas. El holdout **no** puede volver a cerrarse; ninguna evaluación futura
sobre 2024–2025 será ciega para este protocolo.


## Estado vigente — 2026-09-21, integración de `origin/main`

Esta sección **reemplaza toda lectura de las secciones posteriores**, incluida
la de 2026-09-20 inmediatamente siguiente, que se conserva íntegra como
registro histórico.

**Qué hizo esta sesión.** Integró `origin/main`
(`a65701477b19ecad172fa613aea8b8dbf94bab9c`, PR #206) en
`feat/scientific-closure` mediante un merge sin reescritura de historia,
resolviendo cada conflicto por comparación semántica (decisión GD-24). No
ejecutó ninguna campaña, no abrió el holdout 2024-2025 y no inicializó el
ledger definitivo. Verificado el 2026-09-21: `evidence/` y `ledger/` de la raíz
de runtime siguen vacíos.

**Cambio de estado de los tres bloqueos externos.**

- **EXT-01 — condición 4 de ADR-0011: ya no es un bloqueo.** El PR #206 se
  mergeó en `main`, que ya contiene el protocolo detallado vigente con la
  sección «Condiciones de interpretación y soporte previas a ejecución», el
  contrato de features verdadero, `scientific-closure-decisions.md` y
  `scientific-closure-runbook.md`. `docs/adr/0011-…md` registra la condición 4
  como cumplida. **Precisión imprescindible:** la condición 4 es un
  prerrequisito de integración, **no** una autorización. **No** habilita
  ejecutar A, B ni C, que siguen exigiendo autorización explícita del
  responsable y el cumplimiento de sus propias compuertas. Las condiciones 1
  (parcial), 2 (parcial) y 3 de ADR-0011 no cambian.
- **EXT-02 — sin cambio: sigue bloqueando A, B y C.** El runtime de
  contenedores sigue inalcanzable desde esta distro WSL y el runbook invoca
  cada etapa a través de `docker`.
- **EXT-03 — sin cambio: sigue sin respaldo físicamente independiente.**

**Bloqueo nuevo introducido por la integración.** La identidad ejecutable debe
redeclararse: `src/` **deja** de ser byte-idéntico al commit ejecutable
declarado `214735e42ee04f018156cd630591e798aadd8bf3` (siete archivos de
`controlled_daily_v4`, que son las correcciones auditadas del PR #206; `src/`
pasa a ser byte-idéntico a `origin/main`). `docker/` y `pyproject.toml` siguen
idénticos. Ninguna afirmación de identidad ejecutable puede apoyarse ya en
`214735e…`; ver decisión GD-25 y riesgo RK-09 actualizado.

**Estados de requisitos: sin cambios.** Esta sesión no movió ningún requisito
de `traceability.md` a un estado más favorable. `SC-GOV-002` sigue `BLOCKED`,
`SC-GOV-009` sigue `BLOCKED` y `SC-GOV-019` sigue `BLOCKED`.

## Estado vigente — 2026-09-20, sesión de verificación de cierre

Esta sección fue la vigente hasta el 2026-09-21 y **queda supersedida por la
anterior** en todo lo que aquella corrige; el resto sigue siendo la lectura que
reemplaza a las secciones posteriores, que son registro histórico y se
conservan íntegras como historia de recuperación.

**Qué hizo esta sesión.** Reverificó, sin confiar en los registros previos, el
estado técnico del snapshot publicado; sometió ese snapshot a un verificador de
evidencia y a un crítico adversarial independientes, en contextos separados; y
corrigió los estados y documentos que la crítica demostró falsos o excedidos.
No ejecutó ninguna campaña.

**Resultado en una línea:** la preparación está resuelta hasta el límite de lo
alcanzable localmente; la ejecución científica sigue **suspendida** por tres
bloqueos externos, y el registro documental quedó corregido tras diez hallazgos
materiales de crítica independiente.

**Hechos negativos explícitos, reverificados mecánicamente en esta sesión:** el
ledger definitivo **no** está inicializado (`/home/gus/scientific-closure-runtime/ledger/`
verificado vacío); A, B y C **no** se ejecutaron y no existe ningún artefacto de
etapa en ninguna raíz alcanzable; el holdout 2024–2025 permanece cerrado y
ningún valor reservado fue leído; no existe métrica, predicción ni modelo
producido. Los únicos SQLite existentes son fixtures de ensayo cuyo contenido se
autodeclara sintético.

**Verificaciones técnicas reproducidas (evidencia técnica, no científica):**
545 pruebas pasan sobre el snapshot publicado; checker formal exit 0; `ruff` y
`black` exit 0 sobre los archivos propios de la rama; OpenSpec `--strict` 11/11;
enforcement de solo lectura reejecutado PASS; validación de procedencia del
runner exit 0 sin entrenar; pruebas negativas del checker sobre una copia del
árbol, que rechazan un `PASS` y un `NOT_APPLICABLE` forjados. Detalle en
[`closure-verification-2026-09-20/independent-verification.json`](closure-verification-2026-09-20/independent-verification.json).

**Los tres bloqueos externos vigentes** —ninguno resoluble desde este entorno,
los tres resolubles por el responsable:

- **EXT-01 — condición 4 de ADR-0011, `NOT_SATISFIED`.** El ADR está mergeado
  byte a byte en `origin/main`, pero el protocolo detallado allí es una versión
  anterior: le falta la sección «Condiciones de interpretación y soporte previas
  a ejecución» y su sección 4 afirma un contrato de features falso frente al
  código. `scientific-closure-decisions.md` y `scientific-closure-runbook.md`,
  normativos para la rama, no existen en `main`. Resolverlo exige un merge a
  `main`, fuera de la autorización de esta sesión. **Bloquea A, B y C.**
- **EXT-02 — runtime de contenedores inalcanzable desde esta distro WSL.** La
  imagen aprobada `sha256:55bc923e…b297af` existe y fue ejecutada el 2026-09-19
  desde el host Windows; lo que falta es acceso desde aquí. Además el runbook
  invoca cada comando A/B/C a través de `docker`, de modo que esto impide
  ejecutar la campaña, no sólo inspeccionar la imagen.
- **EXT-03 — sin respaldo físicamente independiente.** Las cuatro raíces
  comparten el dispositivo 2128, y el sistema de archivos raíz está respaldado
  por un `ext4.vhdx` dentro del volumen C:, de modo que montar otro dispositivo
  WSL no está demostrado que logre independencia.

**Incumplimiento registrado, no subsanado (RK-14, GD-19).** El reflog demuestra
dos `git push` durante la preparación del 2026-09-20, contra la cláusula «no
push en preparación» del criterio de aceptación de SC-GOV-019 y contra
`AGENTS.md`. Dos informes de auditoría de aquella sesión afirman lo contrario;
se conservan sin alterar y la corrección se registra aparte. SC-GOV-019 quedó
degradado a `BLOCKED`.

**Auditoría final independiente.** Se realizó sobre el snapshot publicado, en
contexto separado y después de una crítica satisfactoria, como exige
`operations.md`. **Veredicto: `BLOCKED`, suspensivo**, acotado a la preparación
y su registro; no es veredicto sobre ninguna campaña, porque no existe.
Confirmó de forma independiente los tres bloqueos externos, la custodia limpia,
la identidad ejecutable byte a byte, 25/25 hashes, la preservación sin editar de
todos los informes de lectores anteriores, y que 22 de los 24 hallazgos previos
quedaron cerrados. Levantó dos hallazgos materiales **contra el trabajo de esta
misma sesión** —AUD-F-01, una fila que acreditaba un artefacto inexistente y
prejuzgaba al auditor; AUD-F-02, una atribución falsa a un lector— y ambos
fueron corregidos y sometidos a reauditoría. Sobre **suficiencia científica** su
veredicto es negativo y no depende de aquellos dos: seis de diez afirmaciones
aprobadas carecen de evidencia y de limitación aceptada que las sustituya.
Rechazó expresamente `PASS_WITH_LIMITATIONS` como veredicto de sesión. Informe
exacto en
[`closure-verification-2026-09-20/review-audit.md`](closure-verification-2026-09-20/review-audit.md);
artefacto de SC-GOV-025 en
[`scientific-closure-audit.json`](closure-verification-2026-09-20/scientific-closure-audit.json).

**Reauditoría independiente sobre el snapshot corregido.** Declaró **cerrados
los seis** hallazgos anteriores, reconfirmó de forma independiente los tres
bloqueos externos, la custodia limpia, la identidad ejecutable, 29/29 hashes y
la preservación sin editar de todos los informes de lectores, y **confirmó el
veredicto de sesión** `SCIENTIFIC_CLOSURE_BLOCKED` suspensivo, rechazando de
nuevo `PASS_WITH_LIMITATIONS`. Volvió a emitir `BLOCKED` sobre el **registro de
preparación** por un hallazgo material nuevo, **RA-01**: tres registros decían
que tres entradas del manifiesto anterior habían quedado superadas cuando eran
**seis**. Era cierto al escribirse y falso al publicarse, porque después se
editaron tres archivos más: exactamente el modo de falla que esta sesión venía
corrigiendo, cometido por tercera vez por el orquestador y detectado por tercera
vez por un lector independiente. Se corrigió el recuento en las tres
ubicaciones y, sobre todo, se **eliminó el modo de falla**: la anotación ahora
instruye recomputar los hashes en lugar de confiar en un número. RA-02 a RA-05
también quedaron aplicados. Informe exacto en
[`review-audit-2.md`](closure-verification-2026-09-20/review-audit-2.md).

**Tercer ciclo de auditoría independiente y decisión de detenerse.** Declaró
cerrados los cinco hallazgos del ciclo anterior, reconfirmó todos los
invariantes y el veredicto de sesión, y encontró una **cuarta instancia de la
misma clase de defecto**, ya sin severidad material: tres registros decían
«tres lectores» cuando eran cuatro, y la cifra la había falsado el propio commit
auditado al agregar el cuarto informe. El auditor caracterizó el mecanismo como
**estructural y no descuidado** —cada ciclo agrega un lector y un conjunto de
hallazgos, lo que falsa cualquier cardinalidad que el ciclo anterior escribió
sobre esos mismos conjuntos— y **recomendó expresamente detener la iteración**:
un cuarto ciclo agregaría un quinto lector y produciría una quinta instancia.
Se siguió esa recomendación, que además coincide con la regla de no perseguir
indefinidamente una causa que persiste tras tres ciclos. El remedio se
generalizó —sustituir recuentos por instrucciones de recomputación o acotarlos a
un snapshot nombrado— y la clase quedó registrada como **KL-01**. Informe exacto
en [`review-audit-3.md`](closure-verification-2026-09-20/review-audit-3.md).

**Lo que ningún ciclo de corrección cambió:** los tres insumos externos, la
ausencia de campaña, el ledger sin inicializar y el holdout cerrado. Tres
rondas de revisión independiente mejoraron el **registro**; ninguna produjo ni
podía producir evidencia científica.

**Estado por requisito:** `PASS` 0; `PASS_WITH_LIMITATIONS` 8; `BLOCKED` 17;
`NOT_APPLICABLE` 0. Cinco filas empeoraron tras la crítica independiente y una
mejoró con artefacto nuevo. Ver [matriz de trazabilidad](traceability.md).
`BLOCKED` **no** es terminal: significa irresuelto y suspendido.

**Pendiente inmediato — insumos externos exactos:** (a) integrar en `main` el
protocolo detallado vigente y, sensatamente, la implementación de A/B/C; (b)
habilitar un runtime de contenedores en esta distro, o decidir y registrar
formalmente que la campaña fija una identidad ejecutable nueva; (c) proveer
almacenamiento no respaldado por el mismo volumen del host. Ninguno de los tres
se resuelve con más trabajo documental, y los tres fueron intentados y agotados
en esta sesión.

## Registro histórico del 2026-09-19 (superado)

Estado actual: `CHECKER_REMEDIATION_BLOCKED` para cierre auditado; corrección
técnica validada. El registro original `CHECKPOINT_DIRTY_RECOVERABLE` se conserva
debajo como historia de recuperación y sus pendientes quedan actualizados por
esta sección.

## Recuperación Linux — 2026-09-19

- Autorización: instrucción explícita de sesión para recuperar el checkpoint,
  corregir únicamente `UnboundLocalError`, validar y crear commit si pasan los
  tests. Autoriza esta delegación acotada y reemplaza las restricciones históricas
  de ruta/delegación; no autoriza ninguna campaña ni cierra `sc-02`.
- Worktree vigente: `/home/gus/work/AAI_Hydric_Stress_scientific_closure`.
  Rama `feat/scientific-closure`, upstream `origin/feat/scientific-closure`.
  HEAD inicial `59612ab2d1822e7bef6f22255985866de73b6cda`; el SHA Windows
  registrado más abajo es exclusivamente histórico.
- Preflight conforme: exactamente los tres archivos pendientes conocidos.
  SHA-256 y tamaños coinciden con los tres archivos del respaldo
  `/mnt/c/Repo/AAI_Hydric_Stress_scientific_closure` antes de editar.
- HU7/HU8, `scientific-closure`, CRISP-DM evaluación/documentación.
  Sin impacto en configuraciones experimentales, hipótesis, alcance ni
  arquitectura. Trazabilidad técnica pertinente a capítulos 2/3.
- Causa reproducida: `audit` se asignaba dentro de la rama terminal, pero el
  `elif` la consultaba para estados no terminales. Test mínimo: 1 ERROR,
  exit 1, traceback conservado. Arreglo: mover la asignación inmediatamente
  antes del `if`, sin cambiar condiciones, errores ni códigos de salida.
- Un ciclo de corrección. Los tests existentes ya cubren estado normal y audit
  mal tipado; permanecen idénticos al respaldo, sin duplicar pruebas.
- Validación ordenada: mínimo 1/1 OK; afectado 1/1 OK (7 subtests); suite
  completa 33/33 OK, 0 errores/fallos; checker formal exit 0,
  `PASS (estructura; runtime no verificado)`; Ruff y Black no disponibles
  (exit 1: módulos ausentes); `git diff --check` exit 0.
  No se atribuye PASS a lint/formato. Python disponible: 3.14.4 mediante
  `python3`; no existe alias `python` ni `pip`.
- Comprobación adicional: CLI con audit mal tipado conserva exit 1 y mensaje
  AUDIT sin traceback; ocho casos terminales con audit ausente/inválido
  rechazados. La cifra histórica de 48 tests no coincide con los 33 métodos
  presentes en el archivo cuyo hash fue acreditado; no se eliminaron tests.
- Snapshot congelado: checker SHA-256
  `a68a47f1e7df128d2ba227a810a183531f013cbd9653091934b49d30c74a2ebf`;
  tests `ee40b2ddc0be3ad798500818d5ef0bcdaa5ec74a4f161725eabc700b68d74940`.
  El evidence_checker confirmó mecánicamente hashes, diferencia de una
  asignación movida, tests intactos, sintaxis y diff sin problemas.
- Explorador y evidence_checker completaron lectura. Implementador, crítico
  y auditor nominales fueron rechazados antes de ejecutar: `gpt-5.6` no
  compatible con la cuenta. El orquestador aplicó la corrección mínima;
  no se alteraron perfiles, modelos ni permisos. No existe crítica ni
  auditoría PASS sobre este snapshot; la solicitud al auditor registró
  explícitamente la falta del prerrequisito de crítica.
- `CRIT-CHK-01`, `CRIT-CHK-02`, `CRIT-CHK-03` y `CRIT-CHK-04`: pruebas verdes,
  cierre pendiente de revisión independiente. Ningún change se marca PASS.
- Probe temporal: preservado sin modificaciones y fuera del commit. Aunque
  su contenido no es científico, el checkpoint lo conserva como evidencia
  de preparación y no se acredita que borrarlo preserve su trazabilidad.
- Commit solicitado: `fix(science): complete formal checker remediation`.
  No creado: `git add --` de las cuatro rutas autorizadas terminó con exit 128,
  `Unable to create .../.git/index.lock: Read-only file system`.
  El sandbox monta `.git` de solo lectura; no se elude con otro índice ni se
  amplían permisos. Alternativa compatible: preservar implementación, tests
  y trazabilidad en el árbol de trabajo para un futuro commit autorizado.
  HEAD final permanece `59612ab2d1822e7bef6f22255985866de73b6cda`;
  árbol dirty con checker, tests y checkpoint modificados, registro JSON
  nuevo y probe preservado. No hay identidad ejecutable nueva ni push.
- Pendientes separados: CRIT-SUB-01; modelos nominales incompatibles;
  permisos efectivos; aislamiento read-only; ADR-0011; identidad ejecutable;
  backup y recuperación; procedencia y licencias. Ninguno se resolvió aquí.
- Próximo paso: lint/formato y revisión independiente del snapshot con
  herramientas/perfiles disponibles en una ejecución autorizada; no A/B/C.

Comandos, códigos de salida, traceback, resultados y respuestas exactas de
lectores se conservan en [registro de remediación](checker-remediation-linux.json).

## Registro histórico del checkpoint interrumpido

Este registro es exclusivamente de recuperación. No autoriza ejecución
científica, no cambia el estado de ningún `sc-*` y no acredita readiness.
Timestamp de observación: `2026-09-19T06:47:05Z`.

## Fase y tarea interrumpida

- Fase: preparación estructural de HU7/HU8, capacidad OpenSpec
  `scientific-closure`, CRISP-DM evaluación/documentación.
- Tarea exacta: remediación del checker formal posterior a la crítica adversarial
  de evidencia de runtime y gobernanza.
- Objeto de trabajo: `scripts/check_scientific_closure.py` y
  `tests/test_scientific_closure_checker.py`.
- La remediación fue interrumpida deliberadamente para recuperar un estado
  verificable. No se deben iniciar nuevas implementaciones desde este checkpoint.

## Identidad Git observada

- Worktree: `C:\Repo\AAI_Hydric_Stress_scientific_closure`.
- Rama: `feat/scientific-closure`.
- HEAD: `ddb50f24a6c8305c682e68ddea5bfb717b7dfaee`.
- Upstream: `origin/feat/scientific-closure`.
- Distancia: 11 commits ahead.
- Commits producidos durante esta sesión antes de este registro: ninguno.
- No hubo push, merge, rebase, tag, release ni PR.

## Agentes

No quedan subagentes activos. No se permiten nuevas delegaciones desde este
checkpoint.

| Agente | Estado | Evidencia directa |
| --- | --- | --- |
| `runtime_checker_critic` | ERRORED | `gpt-5.6` rechazado por cuenta ChatGPT antes de ejecutar |
| `runtime_checker_critic_sol` | COMPLETED | crítica RO sustituta; cuatro hallazgos materiales |
| `runtime_checker_evidence` | COMPLETED | verificación mecánica RO del snapshot anterior; 44/44 tests OK |
| `runtime_checker_findings_fix` | INTERRUPTED | remediación parcial; no terminó ni validó el snapshot actual |
| `runtime_evidence_checker` | ERRORED | `gpt-5.6` rechazado antes de ejecutar |
| `runtime_evidence_checker_sol` | COMPLETED | primera implementación sustituta, posteriormente superada por remediación parcial |
| `agent_setup_gap` | COMPLETED | inspección RO de brechas |

## Árbol y archivos pendientes

Estado observado antes de crear este archivo:

```text
## feat/scientific-closure...origin/feat/scientific-closure [ahead 11]
 M scripts/check_scientific_closure.py
 M tests/test_scientific_closure_checker.py
?? openspec/scientific-closure/validation-read-only-probe.tmp
```

| Archivo | Estado | Tamaño | SHA-256 actual | Evaluación |
| --- | --- | ---: | --- | --- |
| `scripts/check_scientific_closure.py` | modificado | 36610 | `BF39FFF51CA464D7CB4AB1B9CF110065A4FBEB8505D98172EE5CE2094328EF85` | incompleto/no validado |
| `tests/test_scientific_closure_checker.py` | modificado | 18531 | `EE40B2DDC0BE3AD798500818D5EF0BCDAA5EC74A4F161725EABC700B68D74940` | incompleto/no validado |
| `openspec/scientific-closure/validation-read-only-probe.tmp` | sin seguimiento | 131 | `5F32A4BF1E4462D70CD8D17D805E297D88629A9745C2A6459D32E5ED9B548976` | evidencia/probe preservado; no borrar ni inferir aceptación |

El presente archivo es el único archivo nuevo requerido por el checkpoint.

## Evidencia de pruebas

- Snapshot anterior a la crítica: checker mecánico independiente ejecutó 44
  tests en Docker inmutable, sin red y con checkout read-only; 44 OK. Ese
  resultado no valida los bytes actuales porque luego hubo modificaciones.
- Snapshot actual: una suite de 48 tests se ejecutó antes de solicitar este
  checkpoint y terminó con 41 errores. La causa repetida observada fue
  `UnboundLocalError` para la variable local `audit` en
  `scripts/check_scientific_closure.py:396`; la asignación permanece dentro del
  branch de `PASS/NOT_APPLICABLE` en la línea 392.
- No se repitió la suite extensa después de solicitar el checkpoint.
- Prueba breve de checkpoint: `git diff --check`, exit code 0; solo advertencias
  informativas LF→CRLF.
- Un comando combinado de parseo/hashes fue abortado por el usuario y no se usa
  como evidencia.

## Estado de remediaciones

### COMPLETED

- Inventario estático de cinco perfiles TOML y configuración de concurrencia.
- Inspección exploratoria RO de las brechas del runtime.
- Primera implementación opt-in de evidencia runtime y primera verificación
  mecánica sobre un snapshot anterior, conservadas en el diff/historial de la
  sesión; no equivalen a aceptación del snapshot actual.
- Crítica adversarial que identificó `CRIT-CHK-01..04`.

### IN_PROGRESS

- `CRIT-CHK-01`: tipado de eventos/aprobación/auditoría y restricciones de
  autorización científica; parcial. El bug `audit` impide validar el resultado.
- `CRIT-CHK-02`: contraste de título/norma/check contra la spec; implementado en
  el diff pero no validado en el snapshot actual.
- `CRIT-CHK-03`: endurecimiento frente a JSON mal tipado; parcial/no validado.
- `CRIT-CHK-04`: binding a digest de configuración y sidecars con hash; parcial/no
  validado.
- Extensión de pruebas del checker; escrita parcialmente, suite actual no pasa.

### NOT_STARTED

- Corrección posterior al checkpoint del `UnboundLocalError`.
- Reejecución focalizada de tests sobre los bytes actuales.
- Nuevo `evidence_checker`, nueva crítica y auditoría independiente del snapshot
  corregido.
- Generación de evidencia real `agent-capabilities.json` fuera de este checkout.
- Commit de los dos archivos de implementación; no deben commitearse en su estado
  actual.

### BLOCKED

- Readiness/autonomía operativa por sandbox nativo de Windows: `codex doctor`
  informó `helper_unknown_error` en provisioning elevado.
- Perfiles nominales `gpt-5.6` de implementador, crítico y auditor no son
  compatibles con la cuenta ChatGPT observada; las sustituciones Sol no reparan
  por sí solas SC-GOV-006.
- Auditoría final: checker actual fallido, crítica material abierta y permisos
  efectivos no acreditados.

## Estado de prerrequisitos específicos

| Elemento | Estado verificable |
| --- | --- |
| Checker formal | `IN_PROGRESS`; snapshot actual falla con `UnboundLocalError`; no PASS |
| `CRIT-SUB-01` | `OPEN/BLOCKED`; carga, aislamiento y permisos efectivos de los cinco perfiles no acreditados |
| Carga efectiva de agentes | parcial; algunos roles corrieron, pero no hay evidencia completa y homogénea de los cinco |
| Modelos efectivos | Terra/Luna y sustituciones Sol fueron informados; implementer/critic/auditor nominales `gpt-5.6` rechazados; introspección independiente incompleta |
| Permisos efectivos | no acreditados |
| Aislamiento read-only | no acreditado para agentes; Docker read-only solo prueba el entorno de tests |
| ADR-0011 | pendiente respecto de `main`; no resuelto por este trabajo |
| Identidad ejecutable | pendiente; worktree sucio, sin commit ni imagen congelada para campaña |
| Backup y recuperación | pendiente; no existe segunda copia/ensayo acreditado en esta sesión |
| Procedencia y licencias | pendientes: URLs/licencias exactas de Pergamino/NASA/Open-Meteo/ERA5-Land no acreditadas aquí |

## Límites respetados

No se ejecutaron A/B/C ni estudios complementarios; no se abrieron holdouts; no
se inicializó ledger científico; no se borraron archivos/evidencia; no se hizo
push, merge, rebase, tag, release ni PR.

## Reanudación recomendada

1. Confirmar este mismo worktree/rama/HEAD y hashes antes de escribir.
2. Corregir únicamente el alcance ya abierto, empezando por el
   `UnboundLocalError` de `audit`.
3. Ejecutar primero los tests focalizados del checker; solo si pasan, repetir
   gobernanza, checker mecánico, crítica y auditoría sobre un snapshot congelado.
4. No tratar un PASS estructural como readiness ni autorizar campañas mientras
   `CRIT-SUB-01` y los prerrequisitos externos sigan abiertos.
