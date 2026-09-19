# Operación autónoma y auditoría independiente

## Ciclo de trabajo

1. Verificar worktree/rama/HEAD/árbol/upstream; registrar identidad y límites.
2. Leer OpenSpec, seleccionar un change aprobado con dependencias PASS y gates
   adicionales satisfechos. No confundir PLANNED con aprobado.
3. Asignar explorador de solo lectura; reunir hechos y faltantes antes de editar.
4. Asignar un implementador dueño exclusivo de rutas explícitas. Registrar
   sesión/rol/modelo, lista de archivos y versión de entrada. Máximo un escritor
   activo; no lectores auditando archivos mientras cambian.
5. Ejecutar comprobaciones y guardar comandos/salidas/hashes. Fixtures van en
   validation o tmpfs; evidencia científica en su raíz propia cuando autorizada.
6. Congelar snapshot (commit o manifiesto de hashes), liberar escritura y pedir
   evidence_checker. Su juicio es mecánico, nunca científico.
7. Crítico intenta refutar todos los criterios aplicables del snapshot. Hallazgos
   materiales vuelven al implementador; cambiar archivos invalida revisiones previas
   afectadas y obliga a repetir checker/crítico.
8. Solo sin hallazgos materiales abiertos, auditor nuevo de solo lectura verifica
   criterios y suficiencia por sí mismo. No puede implementar ni corregir.
9. PASS cierra el change; FAIL vuelve a corrección permitida; BLOCKED registra
   motivo/evidencia/responsable y suspende dependientes. Negativo científico no se
   corrige para mejorar resultados; puede cerrar el change y bloquear el gate.
10. Registrar checkpoint, estado y próxima acción. Detener al alcanzar el alcance
    autorizado; preparar sistema nunca autoriza A/B/C por sí mismo.

La independencia significa identidad de sesión distinta del implementador, acceso
al snapshot y fuentes, y comprobaciones propias; no solo repetir su resumen.
El auditor responde con objeto cuyo verdict es exclusivamente PASS, FAIL o BLOCKED,
acompañado de alcance, SHA, comprobaciones y hallazgos reproducibles. Si no puede
inspeccionar/comprobar por permisos/herramientas, BLOCKED, no PASS por confianza.
El padre conserva la respuesta exacta y su referencia; no inventa auditorías.

## Transiciones del registro

changes.json tiene un solo dueño: el orquestador. Puede actualizar exclusivamente
estado, aprobación, auditoría y eventos con fuente reproducible; ningún implementador
se autoaprueba. PLANNED → APPROVED requiere instrucción vigente con actor/fecha/
scope/source en approval. APPROVED → IN_PROGRESS requiere dependencias PASS,
extra_gate y permisos de la acción concreta. IN_PROGRESS → REVIEW congela snapshot.
REVIEW → PASS requiere auditoría independiente con verdict/snapshot/evidence;
REVIEW → FAIL vuelve a corrección permitida e IN_PROGRESS; cualquier estado puede
pasar a BLOCKED con causa y evidencia. BLOCKED solo vuelve a APPROVED si se
acredita la resolución, sin renovar derechos de intentos científicos.
NOT_APPLICABLE se reserva a complementos NOT_REQUIRED con decisión de suficiencia
auditada; nunca equivale a experimento ejecutado ni a evidencia positiva.

Cada transición agrega state_events (from, to, actor, timestamp_utc, reason,
evidence); no borrar eventos. approved_for_implementation y
scientific_execution_authorized son permisos distintos. approval registra el
alcance efectivo de los permisos activos y sus fuentes; los anteriores quedan
en eventos. Antes de cada comando se contrasta su etapa con ese scope.
El booleano científico nunca sustituye autorización A/B/ledger/C por separado.
En preparación todos parten sin autorización científica; el registro puede
evolucionar sin romper las pruebas documentales. No se exige permiso B/C para
calificar el mecanismo en sc-02; se exige al despachar su etapa.
Los gates de changes.json son predicados declarativos auditables, no un motor
de ejecución implementado: el orquestador verifica cada cláusula y registra
su evidencia antes de actuar. Un campo faltante o indeterminado bloquea.

## Cierre y estados

PASS del change certifica cumplimiento del contrato acotado. No significa resultado
predictivo positivo, permiso para holdout ni finalización de tesis.
FAIL exige evidencia de incumplimiento, no mera falta de mejora.
BLOCKED identifica lo necesario que falta; distingue autoridad, entorno, procedencia,
dependencia y soporte. No reintentar etapa científica para levantar un bloqueo.
READY_FOR_AUTONOMOUS_EXECUTION se limita al sistema de preparación revisado; cada
acción futura sigue su gate y autorización. NOT_READY indica preparación incompleta.
BLOCKED indica obstáculo que impide las verificaciones/acciones requeridas.

Cierre científico exige GF: evidencia íntegra y suficiente para las afirmaciones
aprobadas de todos los componentes pertinentes; terminal válido del protocolo;
comparaciones y soportes, límites explícitos y vínculos con capítulos 2/3.
Detención en A/B puede producir una conclusión científica válida; no demuestra
afirmaciones que requerían C, ni por sí sola suficiencia para toda la tesis.
La revisión sistemática HU1 u otros entregables fuera de esta sesión no se
declaran completos sin evidencia propia.

## Checkpoints y commits

Grupos de preparación: (1) configuración OpenSpec, (2) especificación,
(3) agentes Codex, (4) matriz e inventario, (5) planes/changes/gates,
(6) documentación operativa/validación. Commits de checkpoint pueden contener
trabajo todavía no aceptado; tasks permanece pendiente hasta PASS independiente.
Antes de cada commit: revisar diff, git diff --check, agregar rutas explícitas,
revisar staged y excluir todo archivo ajeno. No git add -A. Registrar SHA,
propósito, validaciones y estado de revisión. No push en esta sesión.
No cambiar branch/main ni hacer merge/rebase/tag/release/PR.

## Rollback y recuperación

Antes de ejecución, usar git revert del commit acotado tras revisar alcance;
no reset --hard ni checkout destructivo. Mantener registros de decisiones y
validaciones previas. Antes de A, guardar código/config/imagen y su manifiesto.
Después de cada etapa, parar escritores y respaldar evidence+ledger juntos en
destino nuevo; SQLite quiescente o API backup, hashes y segunda copia independiente.
Ensayar restauración con fixtures, nunca con el holdout cerrado.
B incompleta: custodiar, escalar análisis humano; no liberar reserva.
B completa: --recover-stage-b con motivo, verifica artefactos y agrega evento,
sin entrenar. C completa: recuperación idempotente íntegra del ledger original.
C incompleta/incierta: tratar como abierta y bloquear. Nunca restaurar un backup
viejo para obtener un nuevo intento. El conocimiento del holdout no tiene rollback.
No modificar artefactos históricos ni eliminar intentos fallidos.

## Inicio siguiente

Desde PowerShell:
```powershell
codex --cd C:\Repo\AAI_Hydric_Stress_scientific_closure --sandbox workspace-write --ask-for-approval on-request (Get-Content -Raw -Encoding UTF8 openspec/scientific-closure/next-session.txt)
```

Ejecutar desde el worktree indicado para resolver el archivo de prompt.
No agregar --worktree ni permisos de escritura de raw/ledger en preparación.
Si el sandbox sigue fallando, resolver el entorno y repetir comprobaciones; no
sustituir revisión independiente por aprobación propia.
