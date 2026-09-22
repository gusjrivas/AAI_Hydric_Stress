# Informe terminal de preparación Linux — 2026-09-19

**SCIENTIFIC_CLOSURE_BLOCKED.** Auditor independiente: `sc-01` PASS y readiness
integral BLOCKED sobre snapshot limpio `a0d8bf7412bbb68448cf3bcec262097cd1571ab3`.
Dictámenes originales: [texto](audit-final.md) y [objeto](audit-final.json).
No se ejecutaron A/B/C ni complementos. No hay push ni recomendación de merge.

HU7/HU8; capacidad scientific-closure; CRISP-DM evaluación/documentación.
Sin cambios de hipótesis, alcance científico, arquitectura, v3 ni grillas.
Memoria: capítulos 2/3, trazabilidad de entorno y custodia. No es cierre de tesis.

## Autoridad vigente y alcance

El prompt del responsable de esta sesión autoriza completar preparación y ejecutar
A, B, inicialización de ledger y C **solo después** de readiness PASS y de los
gates específicos. No falta una confirmación del usuario. También autoriza
sustituir únicamente modelos incompatibles, commits pequeños y push solo tras
PASS final. Esa autorización reemplaza las prohibiciones históricas de ejecución
en prompts preparatorios; conserva la prioridad de OpenSpec y del protocolo
congelado. No permite eludir gates, inferir procedencia o inventar custodia.

## Evidencia inicial

Clon /home/gus/work/AAI_Hydric_Stress_scientific_closure, rama
feat/scientific-closure, HEAD inicial 329cb600deee0d75d48644b5cafa18e93999d134
y primer checkpoint de esta sesión 0fd15ea5341b5b3763c95e78cf508f3f66e26b15,
upstream origin/feat/scientific-closure. Único untracked inicial: probe conocido.
Commit 329cb60 contiene la remediación; las cifras históricas no sustituyen
la reejecución actual: 33/33 checker y 15/15 gobernanza, Python 3.14.4.
Checker formal: PASS de estructura, runtime no verificado. No es el Python
3.11.16 de la imagen científica. Registros: [observaciones](observations.json).

Se leyeron AGENTS.md, perfiles/config, todos los archivos iniciales de
openspec/scientific-closure, spec y diez changes sc-*, proyecto, ADR-0009/10/11,
protocolo v3 y protocolo v4, manifiesto y decisiones/runbook/auditoría previa.
Las referencias Windows se trataron como texto histórico; no se accedió a /mnt/c.

## Agentes y sustitución

El catálogo local de Codex (models_cache.json) y la herramienta de colaboración
ofrecen gpt-5.6-sol con medium/high/xhigh; no fue necesaria degradación de esfuerzo.
Se sustituyen los tres gpt-5.6 de los TOML por gpt-5.6-sol, conservando esfuerzos,
sandboxes declarados e instrucciones. Terra/medium y Luna/low se conservan.
El checker y sus expectativas se actualizan de forma mínima; la fixture de
sustitución conserva una divergencia real, exclusivamente sintética.

El rechazo de gpt-5.6 pertenece a la sesión histórica preservada en
checker-remediation-linux.json. No se atribuye un nuevo rechazo a esta sesión.
La herramienta actual ya anuncia roles especializados Sol. El implementador
fue invocado como default con rol scientific_implementer explícito y modelo/esfuerzo
Sol/medium; se documenta esta diferencia de mecanismo de carga.

Los TOML válidos y modelos declarados no certifican backend ni permisos efectivos.
Los agentes informan entorno heredado danger-full-access; no se acredita
read-only/workspace-write global. CRIT-SUB-01 y SC-GOV-006 siguen abiertos.
codex doctor exit 0 caracteriza su propia invocación y explícitamente no inspecciona
overrides del hilo activo. Una prueba acotada del CLI read-only sí rechazó abrir
el probe con O_WRONLY mediante EROFS; [registro exacto](sandbox-probe.json).
Eso no acredita que todos los canales de herramientas de los lectores estén aislados.
No se fabrica agent-capabilities.json con sandbox_status=enforced.

Referencia de formato consultada con OpenAI Docs:
[documentación oficial de subagentes](https://developers.openai.com/es-419/docs/agent-configuration/subagents).
La disponibilidad concreta se contrastó localmente; la documentación no prueba
acceso de cuenta ni aislamiento en esta sesión.

## Pendientes e insumos necesarios

| ID | Evidencia / estado | Insumo para resolver |
| --- | --- | --- |
| LNX-01 | No raíces raw/runtime originales encontradas bajo /home/gus por explorador; tampoco existen las rutas hermanas previstas bajo /home/gus/work. | CSV originales con hashes verificables y traslado documentado del runtime/custodia original a Linux. No alcanza una descarga nueva ni directorios vacíos. |
| LNX-02 | Docker y /var/run/docker.sock ausentes; Ruff/Black en imagen fijada fallan antes de iniciar (exit 127). No hay npx para OpenSpec CLI 1.13.1 (exit 127). | Entorno Linux reproducible operativo e imagen accesible/verificada; herramientas de validación. |
| LNX-03 | Sandbox efectivo de cinco roles no acreditado; prueba CLI parcial no resuelve CRIT-SUB-01. | Runtime que imponga permisos por rol y entregue evidencia verificable vinculada a cada sesión. |
| LNX-04 | origin/main local=f7c4ef72ebee9f745bd80deadcd8ad69d9183274; 214735e no es ancestro; diff del protocolo vigente frente a esa referencia no vacío. main local no existe. | Resolver formalmente condición 4 de ADR-0011 sin que este agente haga merge o modifique main. No se presume excepción ni se afirma conocer el remoto actualizado. |
| LNX-05 | Manifiesto: acquisition_date=null y licencia NASA PENDING_CONFIRMATION. Fuentes oficiales históricamente referenciadas no prueban adquisición efectiva. | Evidencia documental aplicable o decisión explícita de admisibilidad/descarte conforme ADR-0011 y SC-GOV-017. No se inventan fechas/URLs/licencias. |
| LNX-06 | Segunda copia independiente y ensayo de recuperación no acreditados; runtime original ausente. | Destino independiente verificable y ensayo con fixtures, más reconciliación de custodia original. |
| LNX-07 | RESUELTO: `CRIT-PREP-01`, assessment CL-01..10 y decisiones R/H/N/S auditados con PASS acotado sc-01. La evidencia científica futura permanece `PENDING`. | Ningún insumo pendiente para este cierre documental; no implica readiness ni ejecución. |

LNX-01 es información externa imprescindible: no se puede reconstruir historia
de custodia desde este checkout ni certificarse primer intento creando otra raíz.
Las ausencias de metadatos históricos se clasifican UNKNOWN/PENDING; por sí sola
una fecha desconocida podría ser una limitación si hubiera decisión admisible.
Aquí no existe esa decisión para la licencia pendiente: SC-GOV-017 bloquea G1.
No se sostiene que todo faltante histórico sea intrínsecamente bloqueante.

No se adoptó la imagen histórica como imagen actual: ID referido
sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af,
ejecutable referido 214735e42ee04f018156cd630591e798aadd8bf3.
Su existencia/integridad local no se verificó. No hay nueva identidad ejecutable
de campaña. Los commits de esta sesión son preparación.

## Probe y preservación

El legacy no versionado se trasladó, sin cambiar bytes ni modo, desde
`validation-read-only-probe.tmp` a la ruta versionable
`readiness-linux-2026-09-19/read-only-probe.txt`: 131 bytes, modo 755, SHA-256
5f32a4bf1e4462d70cd8d17d805e297d88629a9745c2a6459d32e5ed9b548976.
El permiso ejecutable se registra; no se ejecutó el archivo. El registro de
cadena de custodia está en [probe-archive.json](probe-archive.json), y las
observaciones original y repetida permanecen diferenciadas en
[sandbox-probe.json](sandbox-probe.json). No es evidencia científica, PASS de
readiness ni acreditación integral de aislamiento.

## Resultado científico y pendientes

A/B/C y complementos: no ejecutados en esta sesión. No se abrió ni analizó
ningún holdout; no se inicializó ledger definitivo. El responsable informa
holdouts cerrados al inicio; la ausencia del runtime impide revalidación
independiente de historia/custodia. No se habilita B/C ante esa incertidumbre.
Configuraciones y semillas utilizadas: ninguna. El protocolo conserva modelo 42,
bootstrap 20250109, 5000 réplicas; no se presentan como parámetros ejecutados.
No existen métricas, intervalos, predicciones ni resultados negativos nuevos.
La ausencia de resultados es bloqueo de preparación, no un resultado científico negativo.

`CRIT-PREP-01` y `CRIT-PREP-02` fueron corregidos y superaron la crítica
independiente sin hallazgos materiales abiertos en el primer ciclo. No fue
necesario un segundo ciclo. El auditor concedió PASS documental a `sc-01`:
SC-GOV-001/003/004/005 satisfechos dentro de ese alcance. El probe y sus límites
se verificaron; no constituyen acreditación de permisos de todos los canales.

CRIT-CHK-01..04 no se cierran sin crítica y auditoría PASS del alcance completo,
incluido lint/formato solicitado. Los tests verdes no satisfacen esa condición.
`sc-01` se registra PASS con referencia al dictamen y snapshot; `sc-02` queda
BLOCKED y `sc-03..10` suspendidos como BLOCKED. Los complementos R/N/S no se
ejecutaron: su decisión NOT_REQUIRED auditada no se presenta como resultado.
H sigue REQUIRED y pendiente. No se cerró el Trabajo Final ni se verificó
el contenido de los resultados históricos v3; se preservó su referencia.

## Crítica, auditoría y reproducción

Secuencia: explorador → implementador → checker → crítico → auditor independiente.
Los cinco roles fueron invocados y sus límites efectivos están documentados.
[Archivo de revisiones](review-archive.json) conserva respuestas exactas,
identidades, hashes, separación de alcances y degradaciones.
[Crítica final](critique-final-message.md): sin hallazgos materiales abiertos.
[Auditoría](audit-final.json): PASS sc-01; BLOCKED readiness, AUD-READ01..08.
No hay PASS del cierre completo del checker, de sc-02 ni de la ciencia.

Se reprodujeron 48/48 pruebas y checker estructural desde un clon Linux limpio
sin hardlinks del commit auditado, con árbol limpio antes y después:
[salidas exactas](clean-checkout-reproduction.json). Python 3.14.4 del host;
reproducibilidad científica pendiente de imagen, datos, custodia y entorno.
Ruff/Black y OpenSpec estricto no ejecutados por herramientas ausentes; no se
instalaron paquetes globalmente. No se sustituyó el entorno fijado.

Al registrar sc-01 PASS, una fixture negativa heredó la auditoría real y falló
(47/48). La corrección autorizada establece `audit=None` en ese caso; selectiva
1/1 y suite 48/48 pasan. No cambia validadores ni criterios científicos.
El fallo y la implementación están preservados en [registration-fixture.json](registration-fixture.json).

El [manifiesto del snapshot](../../changes/sc-01-evidence-scope/verification-final.json)
contiene 33 archivos verificados por checker, crítico y auditor. Su autoridad
es el commit `a0d8bf7`: comprobar sus hashes mediante `git show a0d8bf7:ruta`
si un registro documental posterior cambió. Registrar el dictamen no cambia
retroactivamente el objeto auditado. Inventario y preservación:
[inventory.json](../../changes/sc-01-evidence-scope/inventory.json),
[preservation.json](../../changes/sc-01-evidence-scope/preservation.json).
No existen ledger ni manifiesto ejecutable nuevos.

## Commits y estado Git

| Commit | Propósito |
| --- | --- |
| `0fd15ea5341b5b3763c95e78cf508f3f66e26b15` | Sustitución mínima de perfiles incompatibles y expectativas del checker. |
| `c63fc713bce0158296d23022a7aeeb8db2cfba93` | Evidencia Linux, limitaciones y archivo del probe sin alterar sus bytes. |
| `a70022d3dd84495421c35186ec91abf765828e6c` | Autorización y selección acotada de sc-01. |
| `a0d8bf7412bbb68448cf3bcec262097cd1571ab3` | Inventario/suficiencia, corrección mínima de fixture y validación; snapshot auditado. |

El commit que incorpora este informe y los dictámenes es un registro posterior
de cierre/bloqueo; su SHA se obtiene con `git log -1 --format=%H --` sobre este
archivo. No es identidad ejecutable ni amplía el PASS de `a0d8bf7`.
No hubo push, merge, rebase, PR, tag, release, modificación de main/UI/v3 ni
acceso a `/mnt/c`. Recomendación: no merge hasta resolver los bloqueos y
obtener las auditorías requeridas. Los commits preservan trabajo revisable.

## Condición para retomar

El insumo externo indispensable es el traslado documentado de los datos y
runtime originales a Linux, con hashes e historia de custodia conciliables.
También requieren resolución los insumos LNX-02..06 y AUD-READ01..08: entorno
reproducible, enforcement por rol, procedencia admisible, segunda copia y
recuperación, y condición 4 de ADR-0011. No faltan confirmaciones del usuario;
su autorización condicional permanece registrada, pero no satisface estos gates.
No crear otra custodia, inventar licencias ni restaurar un estado anterior
para aparentar primer intento. Revalidar identidad y auditoría de readiness
solo cuando los insumos reales permitan verificarlas.
