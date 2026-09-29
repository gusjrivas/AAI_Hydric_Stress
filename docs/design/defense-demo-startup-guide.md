# Guía de arranque de la demo de defensa (Pergamino, Melchor Romero, Laboratorio)

Guion breve para iniciar y recorrer, desde un entorno limpio, los tres modos
usados en la defensa. Complementa (no reemplaza) la documentación técnica
existente:

- `docs/design/producer-ui-local-preview-2026-09-26.md` (arranque detallado
  del backend `producer_v2` compartido por Pergamino y Melchor Romero).
- `docs/design/ensemble-real-execution-report-2026-09-26.md` /
  `docs/design/ensemble-historical-walkthrough-report-2026-09-26.md`
  (procedencia real de los artefactos de Pergamino).
- `docs/seguimiento-tareas.md`, entradas "UI de defensa Pergamino..."
  (2026-09-27), "Melchor Romero como segundo sitio..." (2026-09-28) y
  "Corrección de procedencia..." (2026-09-29).

`scripts/start_defense_demo.ps1` es un envoltorio fino sobre los scripts ya
existentes y validados (`scripts/run_producer_preview_backend.py`,
`uvicorn backend.app.main:app`, `npm run dev`); no reemplaza su validación
de artefactos ni su lógica.

## 0. Qué demuestra cada modo (y qué no)

| Modo | Qué demuestra | Qué NO permite concluir |
| --- | --- | --- |
| **Pergamino** | Recorrido histórico real sobre un demo-runner de ensamble (`pergamino-ensemble-demo`) con emisiones ya preparadas y persistidas, con procedencia externa (ERA5-Land/NASA POWER) explícita. | No es la campaña científica cerrada `controlled_daily_v4_external_pergamino` (ADR-0011, `FAIL` de gobernanza, GD-38/GD-40) ni la reabre; no evalúa el holdout 2024-2025; no es evidencia de superioridad de ningún modelo. |
| **Melchor Romero** | El mismo recorrido, pero completamente reproducible desde el propio repositorio (dataset real ya versionado `data/melchor_romero_2024_consolidado.parquet`), incluida la distinción real/imputado/sin-observación corregida en PR #228. | No tiene evaluación agregada retrospectiva propia (a diferencia del panel 2023 de Pergamino, que a su vez es exploratorio, no confirmatorio). No reejecuta ni reinterpreta `controlled_daily_v3`. |
| **Laboratorio de sensores** | Escenarios sintéticos controlados (ruido, anomalías, sensor de prueba) contra el pipeline operativo real (ingesta, calidad, pronóstico, feedback), identificados inequívocamente como sintéticos. | Los scores del laboratorio no son evidencia científica ni probabilidades calibradas sobre datos reales; solo ilustran el comportamiento del pipeline. |

## 1. Requisitos previos

- Python con las dependencias del repo instaladas (`pip install -e .` o
  equivalente) y accesible en `PATH` como `python`.
- Node.js/npm instalados; `frontend/` con `npm install` ya corrido.
- Puertos libres (por defecto 8199 backend Pergamino/Melchor Romero, 8299
  backend Laboratorio, 5199 frontend — verificar con `Get-NetTCPConnection`
  antes de arrancar, puede haber otra sesión de verificación usando otros
  puertos en la misma máquina).
- Ningún artefacto se referencia por ruta personal (`C:\Users\...`,
  `D:\...`, `/home/...`) en código versionado: todas las ubicaciones se
  pasan por variable de entorno o parámetro de línea de comandos.

## 2. Preparación explícita de artefactos (por sitio)

### Melchor Romero — reproducible desde este repositorio

```powershell
python scripts/prepare_melchor_romero_historical_demo.py `
    --data-dir <directorio externo vacío, p. ej. $env:TEMP\melchor-data> `
    --bundle-root <directorio externo vacío, p. ej. $env:TEMP\melchor-bundles>
```

Ajusta y calibra las 3 familias del ensamble sobre el dataset real
versionado y prepara las 5 emisiones históricas reales
(`2024-10-20`..`2024-10-24`). No requiere ningún insumo externo al
repositorio ni credenciales.

### Pergamino — **disponible localmente y verificado; no incluido en un clon limpio**

Es importante distinguir dos cosas distintas que un lector podría
confundir: **disponibilidad local** (¿existen los artefactos, en esta
máquina, ya generados y verificables por hash?) y **distribución
reproducible** (¿puede cualquiera obtenerlos con un `git clone` de este
repositorio?). Para Pergamino, la primera es **sí** (verificado en esta
tarea, ver abajo); la segunda sigue siendo **no**, deliberadamente — los
artefactos son grandes, de procedencia externa (reanálisis ERA5-Land/NASA
POWER) y no corresponde versionarlos en git.

**Aclaración sobre un apartado previo potencialmente ambiguo**: un
inventario anterior de esta tarea mencionó `run_manifest.json` y luego, en
otra sección, "NO LOCALIZADO". Esa frase se refería exclusivamente a si
los dos CSV fuente (`pergamino_era5land_soil_hourly_2015_2025.csv`,
`pergamino_nasa_power_daily_2015_2025.csv`) aparecen en el historial de
algún commit de este repositorio (`git log --all` sobre esos nombres de
archivo) — no aparecen, por diseño, ya que son deliberadamente externos y
nunca se versionaron. **No significa que falte ningún artefacto en
disco.** Los tres conjuntos de artefactos de Pergamino (CSV fuente,
lecturas+emisión del recorrido histórico, 9 bundles del ensamble) están
presentes en esta máquina y fueron verificados por hash en esta tarea
(sección 7.1).

Artefactos localizados y verificados en esta máquina (rutas externas al
repositorio, `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\...` /
`C:\Repo\AAI_Hydric_Stress_external_data\...` — nunca `data/` del
repositorio):

- **CSV fuente** (`AAI_Hydric_Stress_external_data\raw\`): ambos
  verificados contra `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`.
- **Lecturas + emisión del recorrido** (`pergamino-walkthrough-2023-06-13_17\`):
  `sensor__pergamino-ensemble-demo.parquet` y
  `ui_metadata/operational_v2__pergamino-ensemble-demo.json`, verificados
  contra los hashes fijos en `scripts/prepare_defense_data.ps1`
  (`$expectedReadingSha256`/`$expectedEmissionSha256`). **Usar
  exclusivamente este directorio como `-SourceDataDir`** — nunca
  `session-2` (ver nota al final de esta sección).
- **9 bundles del ensamble** (3 familias × 3 horizontes) +
  `ensemble_manifest.json` por horizonte + `run_manifest.json`
  (`pergamino-ensemble-demo-2026-09-26T034114Z\`), verificados byte a byte
  contra los hashes que el propio `run_manifest.json` registró al
  generarlos (27/27 componentes, 0 discrepancias).

Por mandato de esta tarea, **no se reentrenó ni se regeneraron
emisiones** — se reutilizan exclusivamente los artefactos ya generados y
verificados arriba. Pasos para recorrer Pergamino:

1. Verificar los hashes de los artefactos localizados con
   `Get-FileHash -Algorithm SHA256` contra los valores de esta sección
   (y contra `scripts/prepare_defense_data.ps1` para lecturas/emisión).
2. Copiar a un directorio de demo aislado **nuevo** (nunca reusar uno
   existente) con:
   ```powershell
   ./scripts/prepare_defense_data.ps1 `
       -SourceDataDir "C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-walkthrough-2023-06-13_17" `
       -DemoDataDir ".demo-defense-data\<nombre-nuevo>"
   ```
   (el script rechaza destinos existentes y raíces fuera de
   `.demo-defense-data/`, y no modifica el origen).
3. Usar como `-BundleRoot` la **raíz** que contiene la carpeta
   `pergamino-ensemble-demo\` — **no** agregar `pergamino-ensemble-demo`
   al final del path:
   ```
   -BundleRoot "C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z"
   ```
   `_horizon_dir()` en `src/predictive_modeling/ensemble_bundle.py` ya
   construye `bundle_root / sensor_id / horizon_N` internamente —
   agregar el `sensor_id` a mano en `-BundleRoot` apunta a una ruta que
   no existe y el backend no puede resolver ningún horizonte.

**Nota sobre `session-2`** (directorio preexistente, no tocado por esta
tarea, fuera de este worktree): su `operational_v2__pergamino-ensemble-demo.json`
tiene un hash distinto al de `pergamino-walkthrough-2023-06-13_17`. Se
especuló en un informe previo que esto podría deberse a una revisión
histórica (`HistoricalReviewStore`) registrada durante esa sesión — **esa
atribución no está verificada** y no debe repetirse como si lo estuviera:
`HistoricalReviewStore` escribe en `historical_feedback/<sensor_id>.json`,
un archivo separado de `ui_metadata/operational_v2__*.json`, por lo que
una revisión histórica por sí sola no explica un hash distinto en ese
JSON. La causa real de la diferencia queda sin verificar. Esto no bloquea
nada: esta guía usa exclusivamente `pergamino-walkthrough-2023-06-13_17`
(cuyos hashes sí coinciden con los fijados en el script), nunca
`session-2`, que se deja intacta sin modificar ni borrar.

### Laboratorio de sensores — sin preparación previa

No requiere ningún artefacto externo. Los escenarios se generan en vivo
desde la UI contra el pipeline real.

## 3. Arranque

```powershell
# Laboratorio (sin artefactos externos):
./scripts/start_defense_demo.ps1 -Mode sensor-lab

# Melchor Romero (tras el paso de preparación de la sección 2):
./scripts/start_defense_demo.ps1 -Mode melchor-romero `
    -DataDir <mismo --data-dir usado arriba> -BundleRoot <mismo --bundle-root usado arriba>

# Pergamino (con el PRODUCER_DATA_DIR/PRODUCER_BUNDLE_ROOT reales, sección 2):
./scripts/start_defense_demo.ps1 -Mode pergamino -DataDir <...> -BundleRoot <...>

# Los tres a la vez (Pergamino y Melchor Romero pueden compartir el mismo
# -DataDir/-BundleRoot si ambos sitios fueron preparados ahí, ya que los
# archivos se nombran por sensor_id):
./scripts/start_defense_demo.ps1 -Mode all -DataDir <...> -BundleRoot <...>
```

Cada arranque valida los artefactos requeridos (delegado a
`run_producer_preview_backend.py`) y falla con un mensaje concreto si falta
algo — nunca sirve datos sintéticos en su lugar. El feedback generado
durante la demo queda aislado de las lecturas/predicciones originales:
`historical_feedback/<sensor_id>.json` dentro del `PRODUCER_DATA_DIR` para
Pergamino/Melchor Romero, y `data/feedback__lab-*.parquet` (prefijo
exclusivo, gitignored) para el Laboratorio.

## 4. URLs y recorrido sugerido

- Frontend: `http://127.0.0.1:5199` (o el puerto elegido con `-FrontendPort`).
- Pergamino: ruta `#/defensa-pergamino` — seleccionar una emisión archivada,
  revisar +1/+2/+3 y las explicaciones de indisponibilidad, avanzar el
  reloj, registrar feedback.
- Melchor Romero: ruta `#/defensa-melchor-romero` — mismo recorrido;
  verificar puntualmente que la emisión del 23/10 +3 y la del 24/10 +2
  muestren el 26/10 como imputado (no como observación real) y que el 27/10
  conserve su observación original; confirmar que las observaciones
  posteriores a la fecha del reloj no aparecen hasta avanzarlo.
- Laboratorio: ruta `#/laboratorio-sensores` — recorrer escenarios de ruido,
  anomalías y sensor de prueba, confirmando el rótulo de datos sintéticos y
  que los scores no se presentan como probabilidades calibradas.

## 5. Detener

```powershell
./scripts/start_defense_demo.ps1 -Stop
```

Detiene únicamente los procesos que el propio script arrancó (PIDs
registrados en `.defense-demo-run/`, gitignored), nunca procesos ajenos.

## 6. Problemas comunes

- **Puerto ocupado**: el script falla explícitamente antes de arrancar nada;
  usar `-ProducerPort`/`-LabPort`/`-FrontendPort` para elegir otros puertos.
  Puede haber otra sesión de verificación corriendo en la misma máquina.
  (El chequeo solo cuenta como "ocupado" un socket en estado `Listen`: un
  `TIME_WAIT` de una conexión ya cerrada no bloquea el reinicio.)
- **`'python' no se reconoce...` / Start-Process falla al arrancar el
  backend**: `python` no está en `PATH` en esta sesión de PowerShell. Pasar
  `-PythonExe "<ruta completa a tu intérprete>"`.
- **`falta la variable de entorno PRODUCER_DATA_DIR`/`PRODUCER_BUNDLE_ROOT`**:
  faltan `-DataDir`/`-BundleRoot` en modos `pergamino`/`melchor-romero`/`all`.
- **`batch_not_prepared` al pedir una fecha**: esa fecha no fue preparada en
  el `PRODUCER_DATA_DIR` usado; no es un error del arranque.
- **Frontend: "no se reconoce como un comando" / falla `npm`**: falta
  `frontend/node_modules` (correr `npm install` en `frontend/` una vez, en
  cualquier checkout nuevo) o falta `npm` en `PATH`.
- **Frontend inalcanzable en `http://127.0.0.1:<puerto>/` pero sí en
  `http://localhost:<puerto>/`**: en algunas máquinas Vite se bindea por
  defecto solo a IPv6 (`[::1]`). El script ya fuerza `--host 127.0.0.1`; si
  se arranca `npm run dev` manualmente, agregar ese flag.
- **`Failed to fetch` en el navegador con el backend corriendo**: casi
  siempre CORS. El script setea `CORS_EXTRA_ORIGINS` **antes** de arrancar
  cualquier backend (incluido el del Laboratorio, que no pasaba por ese
  origen en una versión anterior de este script) a partir de
  `-FrontendPort`; si se arrancan procesos por separado, setearlo a mano
  antes de levantar el backend. Si el navegador venía de una pestaña
  abierta contra un backend anterior en el mismo puerto de frontend, el
  módulo JS con la URL base puede quedar cacheado: cerrar la pestaña y
  abrir una nueva (no solo recargar) resuelve esto.
- **CORS**: si el frontend corre en un puerto distinto al configurado, el
  backend producer_v2 lo agrega automáticamente vía `CORS_EXTRA_ORIGINS`
  (seteado por el script a partir de `-FrontendPort`); si se arrancan por
  separado, setearlo manualmente (ver
  `docs/design/producer-ui-local-preview-2026-09-26.md`, sección 3).

## 7. Resultado del ensayo end-to-end (2026-09-29)

Ensayado en este worktree (no un checkout separado — ver limitación abajo),
con `frontend/node_modules` instalado ad hoc (no estaba presente) y
`python`/`npm` pasados por ruta completa (no estaban en `PATH` de la sesión
de arranque). Hallazgos y correcciones aplicadas al propio script durante
el ensayo (quedaron en el código, no son pendientes):

- El chequeo de puerto libre contaba `TIME_WAIT` como "ocupado" — corregido
  para exigir solo `Listen`.
- `Start-Process -FilePath npm` falla en Windows (`npm` es `.cmd`) —
  corregido invocando vía `cmd.exe /c`.
- `-Stop` solo mataba el PID rastreado (`cmd.exe`), dejando el proceso
  `node` de Vite huérfano — corregido con `Stop-ProcessTree` (recursivo).
- `CORS_EXTRA_ORIGINS` solo se seteaba en la rama del backend producer_v2:
  el modo `sensor-lab` con un `-FrontendPort` distinto de 5173 fallaba con
  `Failed to fetch` — corregido seteándola antes de arrancar cualquier
  backend.
- Se agregó `-PythonExe` (no existía) porque `python` no resuelve por
  `PATH` en esta máquina.
- Vite se bindeaba solo a IPv6 (`[::1]`) — se agregó `--host 127.0.0.1`.

Verificado real (backend real, sin mocks, sin datos fabricados):

- **Melchor Romero**: datos preparados desde cero en un directorio temporal
  con `prepare_melchor_romero_historical_demo.py` (dataset versionado,
  ningún insumo externo). `start_defense_demo.ps1 -Mode melchor-romero`
  arrancó backend+frontend reales; verificado por API y por navegador
  (`claude-in-chrome`, clicks reales, no solo JS): emisión 23/10, +3 →
  objetivo 26/10 muestra "Observación posterior: 36.3 % · Valor imputado
  (...). No es una observación independiente para contrastar con el
  pronóstico."; la tabla "Observaciones reveladas" confirma 25/10 = 36.3 %
  (Fuente real), 26/10 = 36.3 % (Fuente real · Imputado, sin dato propio
  este día), 27/10 = 33.0 % (Fuente real, valor propio, no sobrescrito por
  el forward-fill del 26/10) — coincide exactamente con los valores del
  mandato. Retrocediendo el reloj a 24/10 se confirmó que la tabla no
  revela 25/10, 26/10 ni 27/10 (sin fuga de observaciones futuras).
- **Laboratorio de sensores**: `start_defense_demo.ps1 -Mode sensor-lab`
  arrancado real; recorridos por click los cuatro escenarios en la UI real
  (no solo `curl`): A (120 lecturas sintéticas cargadas, confirmado por
  `GET /quality`), B (lectura de 85.0 °C marcada `out_of_range.temperature`
  por el backend real), C (4 días sin lecturas nuevas: no se re-pide
  pronóstico), D (recuperación a 125 filas, pronóstico real re-emitido). El
  rótulo "Datos sintéticos / sensor de prueba" es permanente en la pantalla
  y el texto de score confirma "Señal de 0 a 1; no es un porcentaje de
  certeza." (nunca presentado como probabilidad calibrada).
- **Aislamiento cruzado**: cada modo usó su propio `sensor_id`
  (`melchor-romero-demo` vs. `lab-<hex>`) y su propio backend/puerto en
  este ensayo; no se observó mezcla de datos entre sensores.
- **Pergamino**: ensayado real en la ronda siguiente (2026-09-29, segunda
  sesión) — ver sección 7.1.

Limitaciones del ensayo:

- Se hizo en este mismo worktree de desarrollo, no en un checkout
  completamente separado ("entorno limpio" en sentido estricto sigue
  pendiente); sí se partió de un estado sin `node_modules` y sin
  `.defense-demo-run/` previo, y `python`/`npm` se pasaron explícitamente
  por ruta para no depender de configuración de `PATH` de esta máquina.
- Verificación a 390 px de ancho: no realizada. La herramienta de
  redimensionar ventana (`resize_window`) del entorno de automatización de
  navegador rechazó los tamaños pedidos ("Bounds must be at least 50%
  within visible screen space") incluso en una pestaña nueva — limitación
  de la herramienta en este entorno, no un defecto de la aplicación; queda
  pendiente con un navegador redimensionado manualmente o DevTools.
- No se probaron los flujos de feedback/revisión (confirmar/rechazar
  resultado) ni la ingesta de observaciones tardías durante este ensayo
  puntual; quedan como pendiente de una pasada adicional.

## 7.1. Pergamino desbloqueado y ensayado (2026-09-29, segunda sesión)

Autorizado explícitamente a reutilizar exclusivamente artefactos ya
localizados en esta máquina (sin entrenar ni regenerar nada). Verificación
y ensayo realizados en esta sesión:

**Verificación de hashes — completa, no muestreo** (script ad hoc, no
versionado, ejecutado en esta tarea): los 27/27 archivos de componente
(`model.joblib`/`calibrator.joblib`/`contract.json` × 3 familias × 3
horizontes) verificados byte a byte contra los hashes que
`run_manifest.json` registró al generarlos — **0 discrepancias**. Los 3
`ensemble_manifest.json` (uno por horizonte) verificados: `policy_version`,
`families` (las 3 esperadas), `weights` (suman 1.0), `sensor_id` y
`horizon_days` coherentes con `run_manifest.json` — **0 discrepancias**.
Lecturas+emisión (`pergamino-walkthrough-2023-06-13_17`) y ambos CSV
fuente también verificados contra sus hashes fijos — **0 discrepancias**.
Total: 34/34 archivos verificados, 0 discrepancias.

**Corrección de `-BundleRoot`**: un inventario previo de esta tarea había
indicado agregar `\pergamino-ensemble-demo` al final del `-BundleRoot` —
incorrecto. Verificado leyendo `_horizon_dir()` en
`src/predictive_modeling/ensemble_bundle.py:79-80`
(`Path(bundle_root) / sensor_id / f"horizon_{horizon}"`): el backend ya
agrega el `sensor_id`. El valor correcto es la raíz sin ese sufijo (ver
sección 2). Con el valor corregido, los tres horizontes resolvieron
correctamente (confirmado por API, ver abajo).

**Copia aislada nueva**: `./scripts/prepare_defense_data.ps1
-SourceDataDir "...\pergamino-walkthrough-2023-06-13_17" -DemoDataDir
".demo-defense-data\pr229-rehearsal"` — destino nuevo (no existía),
`session-1`/`session-2` no tocados. Hashes del origen verificados
idénticos antes y después de la copia.

**Arranque real**: `start_defense_demo.ps1 -Mode pergamino -DataDir
.demo-defense-data\pr229-rehearsal -BundleRoot
"...\pergamino-ensemble-demo-2026-09-26T034114Z" -PythonExe
"<ruta completa>" -ProducerPort 8199 -FrontendPort 5273` — backend+frontend
reales arrancados sin bugs nuevos específicos de este modo (los 5 bugs de
la sección 7 ya cubrían el camino producer_v2 compartido).

**Verificado real** (API + navegador, `claude-in-chrome`, clicks reales):

- Las **5 emisiones archivadas** (13 al 17 de junio de 2023) resuelven,
  cada una con sus **3 horizontes** (+1/+2/+3), sin ninguna alerta
  positiva en ninguna combinación — resultado real, no forzado.
- **Avance del reloj**: seleccionada la emisión del 13/06, "Recorrido
  hasta" llevado a 16/06 → la tabla "Observaciones reveladas" muestra
  exactamente hasta el 16/06 (10 filas, 7 al 16 de junio).
- **Retroceso del reloj**: mismo recorrido llevado de vuelta a 14/06 → la
  tabla se contrae a 11 filas, última fila 14/06 — sin fuga de fechas
  posteriores.
- **Feedback histórico en la copia aislada**: confirmado el resultado del
  slot +1 (13/06 → objetivo 14/06) vía la UI real (checkbox + "Guardar
  opinión") → `POST .../reviews` real, `201`. Verificado por
  `GET .../historical/2023-06-13/forecasts?revealed_through=2023-06-14`:
  `review.status="confirmed"`, `revision=1`. El archivo
  `historical_feedback/pergamino-ensemble-demo.json` se creó en la copia
  aislada, **separado** de `ui_metadata/operational_v2__pergamino-ensemble-demo.json`.
- **Hashes antes/después**: los 34 archivos (27 de bundle + 3 manifiestos
  de ensamble + lecturas/emisión + 2 CSV fuente) se re-verificaron
  **después** de arrancar el backend, recorrer las 5 emisiones, avanzar y
  retroceder el reloj, y registrar una revisión — **0 discrepancias**,
  igual que antes de empezar. Los originales
  (`pergamino-walkthrough-2023-06-13_17`) también se re-verificaron
  intactos.
- **Sin alertas forzadas**: las 15 combinaciones emisión×horizonte
  (5 emisiones × 3 horizontes) devolvieron `alert=false`; se registran tal
  cual, sin modificar umbral, modelo ni pronóstico para producir una
  alerta positiva.

**Ensayo combinado (Pergamino + Melchor Romero, un solo backend
compartido)**: se copiaron los árboles ya preparados de ambos sitios (la
copia aislada de Pergamino de este ensayo + el directorio de Melchor
Romero preparado en la sesión anterior, **sin volver a entrenar sus
modelos**) a un `-DataDir`/`-BundleRoot` nuevos y compartidos, organizados
por `sensor_id` como ya lo hace la fachada `producer_v2`. Hashes
verificados antes y después de la copia (4 archivos de lecturas/emisión,
0 discrepancias; originales de ambos sitios re-verificados intactos).
`start_defense_demo.ps1 -Mode all` arrancó un único backend `producer_v2`
sirviendo ambos `sensor_id` simultáneamente: `GET /api/v2/sensors` listó
`pergamino-ensemble-demo` y `melchor-romero-demo`; cada uno resolvió sus
propias emisiones históricas reales por API y por navegador
(`#/defensa-pergamino` y `#/defensa-melchor-romero` en la misma sesión de
frontend); pedir Pergamino en una fecha exclusiva de Melchor Romero
devolvió `404 batch_not_prepared` (aislamiento estructural por
`sensor_id`, no por coincidencia) — sin mezcla de datos entre sensores.

**No verificado en esta ronda** (pendiente):

- 390 px de ancho: sigue bloqueado por la misma limitación de la
  herramienta `resize_window` en este entorno (sección 7).
- Checkout genuinamente separado (sigue ensayado en este worktree).
- Ingesta de observaciones tardías (llegada fuera de orden) en Pergamino
  específicamente — se verificó el mecanismo de reloj/revelado, pero no
  un caso de respuesta de feedback deliberadamente demorada.

## 8. Limitaciones conocidas de esta entrega

- Pergamino no puede recorrerse de punta a punta desde un **clon git
  limpio** sin acceso a los artefactos externos descritos en la sección 2
  — deliberado, por procedencia y tamaño de los datos, no un defecto del
  mecanismo de arranque. Distinto de "disponibilidad local": en esta
  máquina esos artefactos SÍ están presentes y fueron verificados por
  hash de punta a punta (sección 7.1); quien tenga acceso a ellos por el
  canal ya autorizado puede recorrer Pergamino igual que Melchor Romero y
  el Laboratorio.
- Esta guía no reemplaza `docs/research/protocolo-experimental-v3.md` (v3,
  congelado) ni el protocolo `controlled_daily_v4_external_pergamino`
  (ADR-0011); tampoco reinterpreta la retrospectiva exploratoria 2023
  (`docs/research/ensemble-retrospective-evaluation-protocol.md`), que
  permanece una evaluación exploratoria, no confirmatoria, sin resultado de
  superioridad atribuido.
