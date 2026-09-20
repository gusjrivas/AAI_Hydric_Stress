# Guía de ejecución científica v4

**No autorizado todavía:** A, B, C, inicialización del ledger definitivo.
Los comandos siguientes son propuestas futuras; no se ejecutaron.
HU7/HU8, experiment-runner, CRISP-DM modelado/evaluación. No cambia v3,
hipótesis, arquitectura, UI ni contratos públicos.
Ver [diseños congelados](scientific-closure-decisions.md).

**Corrección de invocación — 2026-09-20 (hecho verificado).** Las etapas A, B, C
y la inicialización del ledger invocaban `python -m experiment_runner.controlled_daily_v4`.
Esa forma no es ejecutable: el paquete no define `__main__.py` y `pyproject.toml`
no declara console scripts. El error exacto observado es
`No module named experiment_runner.controlled_daily_v4.__main__; 'experiment_runner.controlled_daily_v4' is a package and cannot be directly executed`.
El módulo realmente invocable es `experiment_runner.controlled_daily_v4.cli`,
comprobado con `--help` (parser completo) en el entorno reconstruido Linux.
Se corrigieron las cuatro invocaciones sin alterar ningún otro argumento,
ruta, semilla ni bandera. El preflight ya usaba la forma correcta
`python -m experiment_runner.controlled_daily_v4.preflight`, también verificada
como invocable. Corrección documental: no ejecuta ni autoriza A, B, C, la
inicialización del ledger ni la apertura del holdout.

## Rutas y preparación

Checkout: C:\Repo\AAI_Hydric_Stress_scientific_closure.
Datos originales: C:\Repo\AAI_Hydric_Stress_external_data\raw, solo lectura.
Runtime externo: C:\Repo\AAI_Hydric_Stress_scientific_runtime.
Subdirectorios disjuntos: evidence (A/B/C), ledger (SQLite B/C),
backups (snapshots) y validation (logs sintéticos; no evidencia científica).
No colocar resultados dentro del checkout. Todos los procesos deben compartir
los mismos registros persistentes. Suplantar, borrar o restaurar registros
antiguos queda prohibido: SQLite no protege contra un administrador del host.

Congelar checkout limpio, SHA e imagen antes de A. No modificar checkout durante
build. Conservar el mismo SHA ejecutable e ID de imagen durante A→B→C; nunca
resolver nuevamente un tag mutable entre etapas.

```powershell
git branch --show-current
git status --porcelain --untracked-files=all
git rev-parse HEAD
.\docker\experiment-v4\build.ps1 -ImageTag experiment-v4-scientific-closure
$ImageId = docker image inspect --format '{{.Id}}' experiment-v4-scientific-closure
$RuntimeRoot = 'C:\Repo\AAI_Hydric_Stress_scientific_runtime'
$RawRoot = 'C:\Repo\AAI_Hydric_Stress_external_data\raw'
$DockerCommon = @('run','--rm','--network','none','--read-only','--tmpfs','/tmp',
  '-e','PYTHONDONTWRITEBYTECODE=1','-e','OMP_NUM_THREADS=1',
  '-e','OPENBLAS_NUM_THREADS=1','-e','MKL_NUM_THREADS=1',
  '--mount',"type=bind,source=$RawRoot,target=/raw,readonly",
  '--mount',"type=bind,source=$RuntimeRoot,target=/runtime")
docker @DockerCommon $ImageId python -m pip check
$PreflightOutput = docker @DockerCommon $ImageId python -m experiment_runner.controlled_daily_v4.preflight --checkout /workspace --raw /raw --evidence /runtime/evidence --ledger /runtime/ledger --backups /runtime/backups --image-id $ImageId
if ($LASTEXITCODE -ne 0) { throw 'Preflight falló: detener' }
[IO.File]::WriteAllText("$RuntimeRoot\evidence\preflight.json", ($PreflightOutput -join [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
```

Preflight consulta rutas, tamaños y referencias versionadas. No lee valores,
no verifica aún hashes de entradas, no inicializa SQLite.
PREPARED_NOT_AUTHORIZED no es permiso de ejecución.
Conservar docker image inspect, pip freeze --all, SHA de código, constraints,
configuraciones, protocolo y fuentes. El ID de imagen registrado es una
declaración contrastable con docker inspect; el proceso no inspecciona el daemon.

## A, solo tras nueva autorización

```powershell
$Inputs = @('--era5-csv','/raw/pergamino_era5land_soil_hourly_2015_2025.csv',
  '--nasa-power-csv','/raw/pergamino_nasa_power_daily_2015_2025.csv',
  '--input-mode','scientific','--depth','primary','--seed','20250109',
  '--bootstrap-replicas','5000','--image-id',$ImageId)
docker @DockerCommon $ImageId python -m experiment_runner.controlled_daily_v4.cli --stage A @Inputs --output-dir /runtime/evidence/A
if ($LASTEXITCODE -ne 0) { throw 'A falló: no continuar' }
```

Inspeccionar soporte, advertencias y candidato congelado. NO_VALID_SELECTION
es un resultado admisible y bloquea B; no modificar decisiones mirando B/C.
Sensibilidad de profundidad requiere salida distinta y no alimenta B.

## B, solo tras autorización y A admisible

```powershell
docker @DockerCommon --mount "type=bind,source=$RuntimeRoot\evidence\A,target=/runtime/evidence/A,readonly" $ImageId python -m experiment_runner.controlled_daily_v4.cli --stage B @Inputs --producer-dir /runtime/evidence/A --output-dir /runtime/evidence/B --stage-b-registry-path /runtime/ledger/stage_b.sqlite
if ($LASTEXITCODE -ne 0) { throw 'B falló: custodiar intento, no repetir' }
```

B reserva candidato, commit, imagen, configuración, datasets/hashes e instante
antes de leer valores. Finaliza autenticando artefactos por hash.
Monoclase conserva predicciones y métricas definibles, pero no valida candidato.
Un resultado negativo no autoriza escoger otro candidato ni repetir B.

## C, autorización adicional y B validada

Inicialización separada y aún no autorizada:

```powershell
docker @DockerCommon $ImageId python -m experiment_runner.controlled_daily_v4.cli --init-holdout-ledger --input-mode scientific --holdout-ledger-path /runtime/ledger/holdout.sqlite
if ($LASTEXITCODE -ne 0) { throw 'Ledger no inicializado: detener' }
$Authorizer = 'REEMPLAZAR_POR_RESPONSABLE_QUE_AUTORIZA'
docker @DockerCommon --mount "type=bind,source=$RuntimeRoot\evidence\A,target=/runtime/evidence/A,readonly" --mount "type=bind,source=$RuntimeRoot\evidence\B,target=/runtime/evidence/B,readonly" $ImageId python -m experiment_runner.controlled_daily_v4.cli --stage C @Inputs --producer-dir /runtime/evidence/A --stage-b-dir /runtime/evidence/B --output-dir /runtime/evidence/C --holdout-ledger-path /runtime/ledger/holdout.sqlite --authorized-by $Authorizer
if ($LASTEXITCODE -ne 0) { throw 'C falló: no liberar ni reinicializar ledger' }
```

El placeholder no constituye autorización. No ejecutar automáticamente A→B→C.
La carga física/verificación de CSV no equivale a analizar sus valores:
agregados/features se restringen al período autorizado según contrato existente.
En esta preparación no se montan CSV reales ni se ejecuta validate-inputs-only
sobre ellos.

## Backup y recuperación

Antes de A: guardar imagen (docker save), configuración, código y metadatos.
Después de cada etapa: detener procesos y copiar evidence+ledger juntos a un
backup nuevo, registrar hashes, fecha y responsable. Mantener una segunda copia
en almacenamiento independiente. No copiar SQLite activo: usar su API backup
si no puede garantizarse quiescencia. Ensayar restauración solo con fixtures.

B completa: repetir el comando B añadiendo --recover-stage-b y
--recovery-reason 'motivo técnico específico'. Verifica archivos y agrega evento
de recuperación; no ajusta ni predice. B incompleta: bloqueo y revisión manual,
sin comando de liberación. C: recuperación idempotente del ledger original
únicamente si el resultado completado es íntegro; apertura incompleta se audita,
no se reinicializa. Desconocer si un período fue abierto obliga a tratarlo como
abierto. Restaurar solamente el último estado íntegro reconciliado; jamás una
copia anterior para obtener un nuevo intento.

## Controles y tiempos

Sin montaje de datos reales:

```powershell
docker run --rm --network none --tmpfs /tmp -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 $ImageId sh -c 'pytest -q -p no:cacheprovider tests/test_controlled_daily_v4_*.py'
docker run --rm --network none $ImageId python -m pip check
docker run --rm --network none $ImageId ruff check --no-cache src/experiment_runner/controlled_daily_v4 tests/test_controlled_daily_v4_scientific_closure.py
docker run --rm --network none $ImageId black --check src/experiment_runner/controlled_daily_v4 tests/test_controlled_daily_v4_scientific_closure.py
```

A usa 8+24+32 configuraciones, nested CV 3×3, congelamiento y bootstrap 5000.
B/C refit del candidato y bootstrap. No se midieron ejecuciones reales:
tiempos sintéticos no permiten una estimación fiable del costo de A.
Registrar tiempo de pared, CPU y memoria en cada ejecución autorizada.

R/H/N/S: diseños separados congelados; nuevos runners pendientes. No existe aún
un comando real válido para estos complementos. Implementar y contrastar sus
fixtures antes de ejecutarlos. Ninguno abre B/C.

## Variante Linux (2026-09-20)

Esta sección **no reemplaza** la variante Windows/Docker anterior, que se
conserva como procedimiento de referencia. Describe únicamente las rutas y el
entorno verificados en Linux (WSL2) el 2026-09-20. Nada de lo registrado aquí
constituye ejecución científica.

**Advertencia de bloqueo (vigente).** Mientras la condición 4 de ADR-0011 no
esté satisfecha, **ninguna etapa A, B o C puede ejecutarse**, ni puede
inicializarse el ledger definitivo ni abrirse el holdout. Hecho verificado:
`origin/main` es `9fcbfd9f4dd4860a07f7e99d5b16d849ac81c4af`; el ADR está
mergeado byte a byte, pero el protocolo detallado presente en `origin/main` es
una versión anterior (le falta la sección 16 de condiciones de interpretación y
soporte) y el código del runner en `main` diverge (~780 inserciones / ~160
eliminaciones). El commit ejecutable declarado
`214735e42ee04f018156cd630591e798aadd8bf3` no es ancestro de `origin/main`.
Resolver esa divergencia exige una decisión de integración que esta preparación
no puede inferir ni ejecutar.

**Rutas verificadas (hechos).**

| Elemento | Ruta Linux | Estado verificado 2026-09-20 |
| --- | --- | --- |
| Entradas primarias | `/home/gus/scientific-closure-inputs/migration-20260920/AAI_Hydric_Stress_external_data/raw/` | Presentes; hashes recalculados |
| Copia lógica | `/home/gus/scientific-closure-backup/migration-20260920/AAI_Hydric_Stress_external_data/raw/` | Presentes; hashes idénticos a la primaria |
| Raíz runtime | `/home/gus/scientific-closure-runtime/` | Creada con `env/`, `evidence/`, `ledger/`, `backups/`, `logs/`; **vacíos de evidencia científica** |
| Entorno reconstruido | `/home/gus/scientific-closure-runtime/env/venv-v4` | Python 3.11.16; 23 paquetes idénticos al pip-freeze histórico |

SHA-256 verificados de las entradas:

- `pergamino_era5land_soil_hourly_2015_2025.csv`:
  `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f`
  (3.954.003 bytes).
- `pergamino_nasa_power_daily_2015_2025.csv`:
  `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b`
  (127.568 bytes).

Ambos coinciden con el manifiesto versionado y la validación de procedencia del
runner (`--validate-inputs-only`) terminó con exit 0 y `Provenance OK`. Esa
comprobación verifica identidad y procedencia; **no** analiza valores, no
calcula features ni abre ningún período reservado.

**El entorno reconstruido NO es la imagen histórica.** La imagen aprobada
`sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af` no fue
inspeccionada, exportada, importada ni reconstruida: el daemon Docker no es
alcanzable desde esta distro (integración WSL deshabilitada; los sockets de
Docker Desktop deniegan `connect()` a uid 1000; `sudo` exige autenticación
interactiva). No se afirma equivalencia alguna entre `venv-v4` y la imagen
aprobada. Cualquier ejecución autorizada debe realizarse sobre la imagen
aprobada verificada por digest, no sobre este entorno.

**Limitaciones adicionales registradas** (no resueltas aquí): la copia de
respaldo no tiene independencia física — primaria, copia y ensayo comparten el
dispositivo 2128 (`/dev/sdf`, ext4) y montar `/dev/sdd` requiere root; el ledger
definitivo **no** está inicializado; A, B y C **no** se ejecutaron; el holdout
2024–2025 permanece cerrado y ningún valor reservado fue leído.

**Forma de invocación en Linux.** Cuando exista autorización y los gates estén
satisfechos, los comandos son los de las secciones A/B/C anteriores sustituyendo
el prefijo `docker @DockerCommon $ImageId` por la invocación equivalente dentro
de la imagen aprobada. El nombre de módulo correcto es, en cualquier caso,
`experiment_runner.controlled_daily_v4.cli` para etapas y ledger, y
`experiment_runner.controlled_daily_v4.preflight` para el preflight.
Ejecutar `python -m experiment_runner.controlled_daily_v4` sin sufijo falla.
Esta nota documenta la forma del comando; **no** autoriza ejecutarlo.
