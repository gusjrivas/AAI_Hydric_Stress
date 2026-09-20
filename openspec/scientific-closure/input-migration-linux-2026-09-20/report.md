# Traslado auditable de insumos Linux — 2026-09-20

Estado implementador: **INPUT_MIGRATION_PARTIAL**. Esta intervención remedia
partes verificables de LNX-01 y LNX-06, preserva evidencia de los bloqueos
LNX-02/LNX-04/LNX-05 y no cierra `sc-02-runtime-readiness`. No ejecutó A/B/C,
auxiliares ni inicializó ledger; no inspeccionó valores CSV ni holdouts.

## Identidad y alcance

Repositorio `/home/gus/work/AAI_Hydric_Stress_scientific_closure`, rama
`feat/scientific-closure`, HEAD de entrada y snapshot de trabajo previo al commit
`e669bf8d0034d0776464822d668c34208f0dd412`, upstream
`origin/feat/scientific-closure`. El orquestador hará los commits. La inspección
se limitó a las dos rutas fuente documentadas y a documentación/configuración de
los dos repositorios Windows autorizados. `expected-inventory.json` se escribió
antes de inspeccionar esas fuentes.

Perfil solicitado: `scientific_implementer`, `gpt-5.6-sol`, esfuerzo `medium`,
sandbox nominal `workspace-write`. El backend/modelo efectivo no es introspectable
ni queda acreditado. El hilo heredó `danger-full-access`; se respetó por conducta
el alcance de escritura asignado. Esto no resuelve LNX-03 ni SC-GOV-006.

## Fuente y traslado

`/mnt/c` es `9p` con opción `ro`; un intento con capacidad de escritura sobre la
ruta exacta registrada en `mount-check.json` fue rechazado con EROFS y no dejó
archivo. La operación podría haber escrito si el montaje no la hubiera rechazado;
no se la presenta como prueba inherentemente no destructiva. No se intentó remontar.

Los dos CSV esperados existen y coinciden con el manifiesto:

| Archivo | Bytes | SHA-256 origen/primary/backup |
| --- | ---: | --- |
| `pergamino_era5land_soil_hourly_2015_2025.csv` | 3.954.003 | `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f` |
| `pergamino_nasa_power_daily_2015_2025.csv` | 127.568 | `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b` |

La fecha de filesystem se registró en `source-inventory.json` y no se presentó
como fecha de adquisición. Ambos archivos sirven como entradas predeclaradas de
A/B/C; C permanece cerrado. Las copias están bajo
`/home/gus/scientific-closure-inputs/migration-20260920/AAI_Hydric_Stress_external_data/raw/`
y `/home/gus/scientific-closure-backup/migration-20260920/AAI_Hydric_Stress_external_data/raw/`.
`cmp` y SHA-256 acreditan igualdad byte a byte en 2/2 archivos.

La raíz runtime Windows existe. `evidence`, `ledger` y `backups` se observaron
sin entradas hasta profundidad cuatro; eso no demuestra que nunca hayan tenido
contenido ni resuelve custodia histórica. No se copiaron ni se inicializó ledger.
Se copiaron opacamente los cuatro archivos seguros de `validation` y su segunda
copia, conservando estructura y nombre:

| Archivo | Bytes | SHA-256 origen/primary/backup |
| --- | ---: | --- |
| `v4-tests.xml` | 73.874 | `0ee57b78da281d660b32d6f4032a8a16ab6a8e76278574d3be30270370eac196` |
| `image-acceptance-tests.xml` | 8.317 | `a67e2b465cde165b1dfd5fb37d61db05a65572accfbe8a66fbb82c6f0c07f34d` |
| `preexecution-environment.json` | 1.850 | `03aa0d2871d815b19496c4da5018a44ccdb0a72c6605de23f70a11713b88e6cd` |
| `pip-freeze.txt` | 426 | `d0f0b9129c8229ce0ea281e02cf0066bbb00d369e511737fc07547956a387667` |

Las rutas completas fuente/destino y los seis `cmp=0` están en
`transfer-manifest.json`. `command-recheck.json` conserva comandos, timestamps,
stdout y stderr completos de la revalidación read-only de hashes y comparaciones.

## Runtime, imagen y herramientas

`docker` resuelve a un wrapper bajo `/mnt/c/Program Files/...`, pero `docker
version`, `docker info` y `docker image inspect` fallan porque Docker Desktop no
tiene integración WSL; `/var/run/docker.sock` está ausente. La imagen aprobada
`sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`
no pudo inspeccionarse y no se reconstruyó. `runtime-image.json` especifica la
exportación necesaria: `inspect` JSON, `docker save` exacto, hash/tamaño/custodia
del tar y verificación del ID postimportación. No se usaron ejecutables Windows
para exportar.

Ruff `0.16.6`, Black `26.5.1` y dependencias están fijados en
`docker/experiment-v4/constraints.txt` (SHA-256
`aa05b7b17ee4677839e724af7a768f532ba669514fb06ffe23f525cddd1efd6b`).
No están instalados en el host y no se instaló nada globalmente.

El orquestador inspeccionó por separado solo metadatos técnicos migrados y lo
registró en `review-runtime-metadata.json`: allí constan declaraciones históricas
de imagen `55bc...`, commit `214735e...` y Python 3.11.16. También explica que el
hash histórico de constraints `d47c...` corresponde a la conversión LF→CRLF del
blob Linux `aa05...`, mientras el manifiesto histórico `c07a...` coincide con Git.
Esa revisión no verifica la disponibilidad actual de la imagen ni cambia el
carácter opaco de la copia hecha por el implementador.

## ADR-0011 y procedencia

Tras el `fetch` del orquestador, `origin/main` es
`9fcbfd9f4dd4860a07f7e99d5b16d849ac81c4af`. El commit ejecutable documentado
`214735e42ee04f018156cd630591e798aadd8bf3` no es ancestro (`exit 1`) y el
protocolo difiere. El protocolo de la rama actual tiene 42 adiciones y 2
eliminaciones respecto de `origin/main`. La condición 4 de ADR-0011 permanece
**BLOCKED**: necesita una decisión/integración metodológica, no una inferencia de
este traslado.

Los publicadores, fuentes, URLs preservadas, transformaciones y hashes están
documentados en `provenance-assessment.json`. Open-Meteo/ERA5-Land conserva
términos oficiales documentados, pero no prueba los términos históricos de la
transacción; su licencia queda `PARTIALLY_VERIFIED`. La licencia/términos
aplicables de NASA POWER quedan `BLOCKING_UNKNOWN`; su versión histórica queda
`UNKNOWN` y no se convierte en un gate independiente inventado. Las fechas de
adquisición de ambos archivos son `UNKNOWN`; la fecha informada por el
proyecto y los mtimes no se promovieron a evidencia. La búsqueda acotada en
archivos rastreados explícitos no identificó un recibo adicional. Comandos
`git ls-files`/`git grep`, rutas, timestamps y salidas están preservados en
`command-recheck.json`; no se afirma ausencia global en C:.

## Segunda copia y recuperación

Existe segunda copia lógica 6/6 con hash idéntico. Inputs, backup y ensayo están
en el mismo dispositivo `/dev/sdf`, filesystem ext4; no son almacenamiento
físicamente independiente. El ensayo restauró una copia de fixture
`pip-freeze.txt` bajo
`/home/gus/codex-runs/scientific-closure-20260919/migration-20260920/recovery-rehearsal/`:
426 bytes, SHA-256 `d0f0...7667`, `cmp=0`. LNX-06 queda parcialmente satisfecho;
faltan almacenamiento independiente y reconciliación de custodia histórica.

## Validación y estado de bloqueos

El checker formal del implementador pasa solo en modo estructural (`runtime no
verificado`) y sus 15 pruebas de gobernanza pasan. El `git diff --check` inicial
devolvió exit 0 pero no evaluó el directorio todavía untracked, por lo que no se
usa como prueba de formato. El orquestador conservó su recheck exacto de checker
33 y gobernanza 15 en `review-validation-recheck.json` y validará el snapshot
staged antes del commit. Las pruebas focales de
entorno/reproducibilidad/recuperación no importan en el host por ausencia de
NumPy/Pytest; Ruff y Black tampoco están disponibles. No se sustituyó el entorno
fijado ni se instalaron herramientas.

Ningún LNX queda cerrado integralmente. LNX-01 está parcialmente satisfecho:
datos originales y validation fueron trasladados con identidad, pero no existe
evidencia de custodia histórica en los directorios vacíos. LNX-06 está
parcialmente satisfecho por copia lógica y ensayo de fixture. LNX-02, LNX-04 y
LNX-05 siguen bloqueados. LNX-03 permanece fuera de este alcance y abierto.

AUD-READ01 y AUD-READ05 reciben remediación parcial. AUD-READ02, AUD-READ04,
AUD-READ06, AUD-READ07 y AUD-READ08 siguen bloqueados; AUD-READ03 no cambia.
`sc-02` permanece BLOCKED y no se autoaprueba ni se cierra. La siguiente
condición verificable es aportar/importar la imagen aprobada con digest exacto y
un destino de backup físicamente independiente; en paralelo se requiere la
decisión documentada de ADR-0011 condición 4 y la evidencia o decisión explícita
sobre licencia/términos históricos de NASA POWER.

INPUT_MIGRATION_PARTIAL
