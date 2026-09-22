# Auditoría de preejecución científica — 18/09/2026

Veredicto: **READY_TO_RUN_A**, limitado a la clasificación retrospectiva P20
de v4. No equivale a READY del Trabajo Final ni autoriza ejecución.
A/B/C científicas no ejecutadas; holdout cerrado; ledger definitivo inexistente.
Los complementos están diseñados, no implementados ni ejecutados.

## A. Rama, commits, aislamiento y sincronización

Worktree exclusivo: C:\Repo\AAI_Hydric_Stress_scientific_closure.
Rama: feat/scientific-closure.
Base: b82d445e74dacbe0d6d7a746d5426fcff5ba8f50.

| Commit | Propósito |
| --- | --- |
| 496b5e175e7627568684826d8630f134ba4d605b | Diseño previo a implementación |
| e48bf370a7609c750b41343d661ba3bf9b8986b6 | Métricas, soporte, monoclase, episodios y fixtures |
| 86036d3b253e95311e96c288810f9887c82728f1 | Custodia B, preflight, build y aceptación |
| 214735e42ee04f018156cd630591e798aadd8bf3 | Protocolo, procedencia y guía vigente |

Este informe se incorpora después mediante un commit exclusivamente documental.
**Commit ejecutable verificado: 214735e42ee04f018156cd630591e798aadd8bf3.**
No cambia por incorporar este informe: la ejecución propuesta usa su imagen
inmutable, no el checkout ni un tag mutable.

origin/main observado: f7c4ef72ebee9f745bd80deadcd8ad69d9183274.
Base común confirmada: b82d445e74dacbe0d6d7a746d5426fcff5ba8f50.
Antes del commit del informe: 4 commits propios y 2 exclusivos de origin/main.
Los dos nuevos commits de main pertenecen a UI (#204); no se integraron.
origin/feat/scientific-closure sigue en la base, sin push de esta intervención.
El árbol estaba limpio al construir; se verifica limpio al cerrar.
Ningún diff afecta frontend, backend, API pública, v3 o evidencia histórica.

## B. Hallazgos resueltos y pendientes

Los identificadores SC siguientes organizan esta entrega, no renumeran auditorías históricas.

| ID | Hallazgo y severidad | Estado / criterio comprobado o pendiente |
| --- | --- | --- |
| SC01 | Contrato v3/v4 confundido — alta | Resuelto documentalmente; ocho features efectivas serializadas en A/B/C |
| SC02 | Monoclase descartaba predicciones B/C — alta | Resuelto; train válido conserva predicciones, matriz, Brier/log loss y razones |
| SC03 | Selección sin soporte — alta | Resuelto; mínimo 2 folds definidos y bootstrap ≥80%; estado sin candidato |
| SC04 | episode_recall usado como anticipación — alta | Resuelto en definición e implementación de onset; sin afirmación empírica |
| SC05 | Repetición de B / candidato no custodiado — crítica | Reserva única persistente, candidato/imagen/commit/hashes; recuperación explícita |
| SC06 | Evidencia dentro de checkout / identidad incompleta — alta | Rutas externas, preflight, build limpio e identidad capturada; backup operacional pendiente |
| SC07 | Documentación B/C desactualizada — media | Nota de vigencia, manifiesto y spec actualizados; historial conservado |
| SC08 | MAE/RMSE ausentes — alta para cierre final | Diseño R completo; runner/evaluación/evidencia pendientes, separado de clasificación |
| SC09 | HITL sin evaluación prospectiva — alta | Diseño H de tres brazos; runner, ejecución y evidencia pendientes |
| SC10 | Anomalías evaluadas sin reserva independiente — alta | Diseño N separado; demostración previa queda limitada; runner/evidencia pendientes |
| SC11 | Escasez de etiquetas confundida con sensores — alta | Diseño S distingue etiquetas, mediciones y ruido; runner/evidencia pendientes |
| SC12 | Procedencia incompleta — media | Fuentes y convenciones verificadas; adquisición real, versión histórica y licencia NASA específica pendientes |
| SC13 | Eficacia científica v4 no demostrada — alta | Pendiente por autorización; ningún test se presenta como resultado experimental |

Implementación faltante: runners auxiliares R/H/N/S.
Ejecución faltante: toda A/B/C científica y complementos.
Evidencia faltante: predicciones/métricas/intervalos reales v4, beneficios HITL,
detección de anomalías y robustez complementaria.
Inconsistencias corregidas: contrato, monoclase, soporte y estado B/C.
Documentación pendiente: procedencia que no puede verificarse y conclusiones
que requieren resultados futuros.

## C. Decisiones metodológicas documentadas

Fuente detallada: [scientific-closure-decisions.md](scientific-closure-decisions.md).

- v3 tiene 15 features temporales, include_current=false; v4 tiene ocho,
  valores actuales y transformaciones temporales solo de humedad.
  No es réplica directa: diferencias no atribuibles exclusivamente a sitio,
  período o familia. Todos los candidatos internos v4 comparten contrato.
- MCC primaria; MAE/RMSE pertenecen al auxiliar continuo.
- Tuning/congelamiento y selección global requieren dos folds definidos.
  Bootstrap requiere 4000/5000 válidas; registra descartes y proporción.
  Fallo de soporte impide seleccionar y conserva evidencia completada.
- MCC con verdad o predicción constante se informa indefinido; se documentó
  la corrección matemática preejecución del 18/09, sin observar datos reales.
  JSON null con estado, razón y soporte; no NaN ni sustitución silenciosa por cero.
- Inicio: fecha objetivo = emisión+3; episodios positivos contiguos, segmentos
  y gaps separados, inicios censurados excluidos. Anticipación >0 días, mismo día,
  tardía y omisión; días de anticipación, falsos avisos y soporte.
  Es descriptivo y no selecciona candidatos ni demuestra operación en campo.
- B se reserva antes de leer valores; no cambia candidato tras abrir B.
  Una evaluación monoclase no valida B y no autoriza reabrir C.
- Mismo commit ejecutable e imagen durante A→B→C; resultados fuera del checkout.
- ERA5 día civil UTC-3 y POWER LST se alinean por fecha como aproximación.
  La disponibilidad real de los productos puede superar el horizonte nominal.

## D. Diff por archivo

Rutas de código relativas a src/experiment_runner/controlled_daily_v4/.
Ningún archivo listado contiene resultados científicos reales.

| Archivo | Cambio |
| --- | --- |
| admissibility.py | C rechaza soporte bootstrap inferior a 80 % |
| artifacts.py | Contrato efectivo y métricas onset globales/por fold |
| bootstrap.py | Mínimo de réplicas válidas, proporción descartada, diagnósticos |
| cli.py | Custodia B, recuperación y registro de image_id |
| features.py | Descriptor del contrato efectivo de ocho features |
| metrics.py | Monoclase explícita, MCC degenerado, razones y onset |
| selection.py | Soporte mínimo por outer fold, sin selección insuficiente |
| tuning.py | Train monoclase no ajustable; mínimo dos folds; diagnósticos |
| stage_a_runner.py | Estado sin candidato y preservación de evidencia parcial |
| stage_b_runner.py | Predicciones/métricas monoclase, onset y advertencia |
| stage_c_runner.py | Mismo tratamiento, sin alterar reapertura del ledger |
| stage_b_custody.py (nuevo) | Reserva SQLite, hashes, concurrencia y recuperación |
| preflight.py (nuevo) | Validación metadata-only, rutas disjuntas y manifiesto |
| docker/experiment-v4/build.ps1 (nuevo) | Build Windows con SHA conocido y árbol limpio |

| Tests | Cambio |
| --- | --- |
| controlled_daily_v4_fixtures.py | Fixture periódico seleccionable, sin alterar fixtures por defecto |
| test_controlled_daily_v4_bootstrap.py | Descartes y ausencia de intervalo cuando no hay soporte |
| test_controlled_daily_v4_metrics.py | Expectativas monoclase e indefiniciones |
| test_controlled_daily_v4_reproducibility_artifacts.py | Configuración efectiva de fixture reducido, boundaries e identidad |
| test_controlled_daily_v4_runner_artifacts.py | Serialización con fixture seleccionable y grilla pequeña |
| test_controlled_daily_v4_stage_a_integration.py | Integración temporal con soporte suficiente |
| test_controlled_daily_v4_stage_b_integration.py | Predicciones persistidas para evaluación monoclase |
| test_controlled_daily_v4_stage_b_runner.py | Conservación de métricas definibles y soporte |
| test_controlled_daily_v4_stage_c_runner.py | Conservación monoclase sin cambiar custodia |
| test_controlled_daily_v4_scientific_closure.py (nuevo) | Onset, selección, bootstrap, custodia, concurrencia y preflight |

| Documentación | Cambio |
| --- | --- |
| docs/research/scientific-closure-decisions.md | Diseño predeclarado principal y R/H/N/S |
| docs/research/controlled-daily-v4-external-pergamino-protocol.md | Contrato y reglas vigentes; historial fechado preservado |
| docs/research/controlled-daily-v4-external-pergamino-manifest.yaml | Estado B/C, fuentes oficiales, incertidumbres y alineación |
| docs/research/README.md (nuevo) | Índice y distinción entre implementación/prueba/evidencia |
| docs/research/scientific-closure-runbook.md (nuevo) | Comandos futuros, identidad, backup y recuperación |
| docs/research/scientific-closure-execution.template.json (nuevo) | Plantilla explícitamente no autorizada/no ejecutada |
| openspec/specs/experiment-runner/spec.md | Trazabilidad HU7/HU8 y requisitos de cierre |
| Este informe | Auditoría técnica final de esta intervención |

## E. Validación ejecutada

| Control | Resultado exacto |
| --- | --- |
| Suite v4 completa con fixtures | 483 passed, 3 skipped, 0 failed; 500,38 s |
| Aceptación en imagen inmutable (últimos ajustes A/C + cierre) | 53 passed; 25,92 s |
| ruff check --no-cache, alcance v4 | All checks passed |
| black --check, alcance v4 | 62 archivos sin cambios necesarios |
| python -m pip check, imagen construida | No broken requirements found |
| git diff --check | Sin errores |
| Build limpio con dependencias cacheadas | 5,9290215 s |
| Identidad de imagen | SHA esperado, dirty=false, entorno fijado validado |
| Directorios evidence y ledger | Vacíos; ningún registro científico inicializado |

Tres omisiones: tests de identidad que requieren git dentro del contenedor.
La imagen intencionalmente usa build_metadata_file; esa ruta sí se verificó,
junto con captura de SHA/limpieza mediante git en el host.
No se declara probada en esta imagen la ruta alternativa de subprocess git.

Hubo corridas intermedias fallidas; se corrigieron antes de estos resultados.
Una corrida anterior con fixtures reemplazados se detuvo para evitar continuar
un bootstrap innecesario. No se oculta como ejecución aprobada ni evidencia científica.

Artefactos técnicos, fuera de checkout:
C:\Repo\AAI_Hydric_Stress_scientific_runtime\validation\
- v4-tests.xml: 486 casos, 483 aprobados y 3 omitidos.
- image-acceptance-tests.xml: 53 casos aprobados.
- preexecution-environment.json: SHA, imagen, dependencias, contrato y hashes.
- pip-freeze.txt: inventario completo instalado.

Comandos de validación (PowerShell, variables locales):

```powershell
$ImageId = 'sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af'
$ValidationRoot = 'C:\Repo\AAI_Hydric_Stress_scientific_runtime\validation'
docker run --rm --network none --read-only --tmpfs /tmp --mount "type=bind,source=$ValidationRoot,target=/validation" -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1 $ImageId pytest -q -p no:cacheprovider tests/test_controlled_daily_v4_reproducibility_artifacts.py tests/test_controlled_daily_v4_stage_a_integration.py tests/test_controlled_daily_v4_stage_c_runner.py tests/test_controlled_daily_v4_scientific_closure.py --tb=short --junitxml=/validation/image-acceptance-tests.xml
docker run --rm --network none --read-only --tmpfs /tmp -e PYTHONDONTWRITEBYTECODE=1 $ImageId sh -c 'python -m pip check && ruff check --no-cache src/experiment_runner/controlled_daily_v4 tests/test_controlled_daily_v4_*.py tests/controlled_daily_v4_fixtures.py && BLACK_CACHE_DIR=/tmp/black black --check src/experiment_runner/controlled_daily_v4 tests/test_controlled_daily_v4_*.py tests/controlled_daily_v4_fixtures.py'
```

La suite completa usó el mismo entorno fijado con checkout montado read-only
y pytest tests/test_controlled_daily_v4_*.py. Los últimos cambios de preservación
parcial A y advertencia C se verificaron después en la imagen inmutable.

## F. Evaluaciones complementarias

Todos los diseños usan solo desarrollo 2015–2022; no 2023–2025 ni Balcarce.
Runners nuevos pendientes, sin comandos de ejecución reales inventados.

| ID | Diseño predefinido | Métricas e interpretación |
| --- | --- | --- |
| R | Humedad 0–7cm t+3 en m3/m3; ocho features; train hasta 2020, diagnóstico 2021, evaluación 2022; Ridge y RF fijos; persistencia/media train | MAE/RMSE, deltas pareados, soporte; no equivalente a P20 |
| H | Train 2015–2020; feedback 2021 madurado; evaluación posterior 2022; congelado/refit sin correcciones/refit con correcciones; 20 eventos por seed, correcciones simuladas explícitas | MCC/AP/Brier/F1, FP/FN y episodios; no prueba de beneficio humano real |
| N | IsolationForest solo fit 2015–2020; anomalías inyectadas solo en reserva 2022; limpio, spikes 5 % ±3σ y stuck de 3 días hasta 5 % | Detección, falsas alarmas, precisión, recall y soporte; no validación de anomalías reales |
| S | RF fijo, train 2015–2020 y evaluación 2022; base, etiquetas 50 %, sensores enmascarados 10 % en bloques de 3 días, ruido 0,3σ train | MCC/AP/Brier/F1, FP/FN/episodios y deltas; cuatro condiciones × cinco seeds |

Semillas 0–4; bootstrap seed 20250109, bloques de 30 días, 5000 réplicas
cuando corresponde. Entradas imputadas causalmente, nunca objetivos.
Los diseños detallan fecha de emisión, maduración, exclusiones y límites.
No ajustar decisiones mirando evaluaciones ni elegir semillas favorables.

## G. Custodia y ausencia de apertura

No se ejecutaron A/B/C científicas ni auxiliares reales. Sí se ejecutaron
runners con fixtures como pruebas unitarias/de integración autorizadas.
Ningún contenedor de tests o captura del entorno montó raw de Pergamino.
No se invocó validate-inputs-only contra datasets reales.
No se inspeccionaron valores ni métricas reservadas de B/C.
No se inicializó ledger científico: su directorio está vacío.
Los SQLite de tests vivieron en tmpfs y se eliminaron con sus contenedores.
La procedencia histórica del YAML se conservó sin repetir análisis de valores.
No se crearon tags de Git, merge, PR, push ni modificaciones del frontend.

Esta evidencia de no apertura corresponde al alcance de esta intervención,
no certifica actividades históricas o de otros operadores.

## H. Comandos propuestos para ejecución real

Procedimiento completo con compuertas, B, C, inicialización separada y recuperación:
[scientific-closure-runbook.md](scientific-closure-runbook.md).
**No ejecutar todavía.** Usar el ID inmutable de esta auditoría; no reconstruir
la imagen ni cambiar commit entre etapas.

Preparación de variables y A, únicamente si se recibe autorización explícita:

```powershell
$ImageId = 'sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af'
$RuntimeRoot = 'C:\Repo\AAI_Hydric_Stress_scientific_runtime'
$RawRoot = 'C:\Repo\AAI_Hydric_Stress_external_data\raw'
$DockerCommon = @('run','--rm','--network','none','--read-only','--tmpfs','/tmp',
  '-e','PYTHONDONTWRITEBYTECODE=1','-e','OMP_NUM_THREADS=1',
  '-e','OPENBLAS_NUM_THREADS=1','-e','MKL_NUM_THREADS=1',
  '--mount',"type=bind,source=$RawRoot,target=/raw,readonly",
  '--mount',"type=bind,source=$RuntimeRoot,target=/runtime")
$Inputs = @('--era5-csv','/raw/pergamino_era5land_soil_hourly_2015_2025.csv',
  '--nasa-power-csv','/raw/pergamino_nasa_power_daily_2015_2025.csv',
  '--input-mode','scientific','--depth','primary','--seed','20250109',
  '--bootstrap-replicas','5000','--image-id',$ImageId)
docker @DockerCommon $ImageId python -m experiment_runner.controlled_daily_v4 --stage A @Inputs --output-dir /runtime/evidence/A
if ($LASTEXITCODE -ne 0) { throw 'Detener y auditar; no avanzar a B' }
```

El preflight metadata-only de la guía debe completarse antes de A. La lectura
estructural y hash de CSV completos del runner no se usa para analizar valores
fuera de la ventana autorizada. Los tests verifican el recorte previo a agregación.
No iniciar B automáticamente aunque A produzca candidato.
No iniciar C aunque B valide sin su autorización adicional.

## I. Tiempo y costo

Medido: suite completa 8 min 20,38 s; aceptación de imagen 25,92 s;
build cacheado 5,93 s. No es una medición de rendimiento científico.
A real, B, C y complementos: duración y coste no determinados.
A implica nested CV de grillas fijadas y bootstrap 5000; no extrapolar linealmente
desde fixtures pequeños. Medir pared/CPU/memoria durante ejecución autorizada.

## J. Riesgos residuales

- Validez interna: autocorrelación y soporte pequeño; controles temporales y
  mínimos reducen riesgos, no garantizan potencia estadística.
- Validez externa: un sitio, reanálisis y datos satelitales agregados; sin validación
  fisiológica/campo ni replicación geográfica. v3/v4 no constituyen réplica directa.
- Constructo: P20 aproxima humedad baja, no estrés vegetal clínicamente verificado.
  Onset se mide dentro de la ventana observable, no promete alerta operativa.
- Disponibilidad: POWER tiene latencias y usa LST; alineación por fecha con
  UTC-3 es aproximada. No demostrar detección temprana desplegable a partir de
  estos resultados retrospectivos.
- Reproducibilidad: falta git en imagen para tres tests alternativos; ruta de
  build identity verificada. Custodia depende de conservar registro único,
  copias íntegras y montajes correctos; no resiste manipulación administrativa.
- Procedencia: adquisición real, versión histórica de servicio y licencia
  específica aplicable a NASA siguen desconocidas/pendientes; no inventadas.
- Operación: backup independiente y ensayo completo de restauración del entorno
  quedan como tareas del responsable antes de una campaña; se probó recuperación
  e integridad de artefactos con fixtures, no un desastre real.
- Complementos: diseño no implica implementación, ejecución ni evidencia.

Fuentes oficiales verificadas para el manifiesto:
[Open-Meteo términos](https://open-meteo.com/en/terms),
[catálogo ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=overview),
[POWER API diaria](https://power.larc.nasa.gov/docs/services/api/temporal/daily/),
[POWER convenciones temporales](https://power.larc.nasa.gov/docs/faqs/other/),
[POWER resolución](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/),
[POWER latencia](https://power.larc.nasa.gov/docs/faqs/data/),
[POWER atribución](https://power.larc.nasa.gov/docs/referencing/).
No se atribuyó una licencia histórica no verificada.

## K. Matriz de preparación

| Etapa | Diseño | Implementación / integración | Tests | Ejecución científica | Condición siguiente |
| --- | --- | --- | --- | --- | --- |
| A principal | Congelado | Preparada | Aprobados con fixtures | No ejecutada | Nueva autorización y preflight real de metadatos |
| B | Congelado | Preparada, custodia única | Aprobados con fixtures | No ejecutada | A seleccionable, respaldo/custodia y autorización |
| C | Congelado | Preparada, ledger existente en código | Aprobados con fixtures | Cerrada | B validada + autorización + inicialización separada |
| R continua | Diseñado | Runner pendiente | Pendientes | No ejecutada | Implementar y verificar contra diseño |
| H HITL | Diseñado | Runner pendiente | Pendientes | No ejecutada | Implementar separación prospectiva y fixtures |
| N anomalías | Diseñado | Runner pendiente | Pendientes | No ejecutada | Implementar fit/reserva/inyección y fixtures |
| S robustez | Diseñado | Runner pendiente | Pendientes | No ejecutada | Implementar matriz acotada y fixtures |

## L. Veredicto y condiciones de cierre posterior

**READY_TO_RUN_A**, condicionado a autorización explícita y al alcance
retrospectivo definido. B/C siguen cerradas a ejecución.
El Trabajo Final todavía no está científicamente cerrado.

Para READY final hacen falta ejecución autorizada reproducible, evidencia
consolidada con hashes y soporte, complementos implementados/evaluados conforme
al diseño, límites y procedencia explicitados, correspondencia con memoria
técnica y auditoría final. Una compuerta fallida no se arregla repitiendo su test:
debe concluirse conforme al protocolo y declararse el alcance que pudo evaluarse.

No es necesario “corregir” resultados negativos, ausencia de ganador estable,
peor desempeño de sintéticos o HITL, falta de mejora general ni superioridad de
persistencia. Son resultados científicos admisibles si tienen trazabilidad,
soporte e interpretación honesta. Tampoco se exige Deep Learning.

La intervención se detiene aquí. No ejecutar A/B/C, abrir holdouts, crear tags
ni publicar baseline sin una nueva autorización.
