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

### Pergamino — **no reproducible únicamente desde este repositorio**

Verificado contra `origin/main` en esta tarea: `scripts/prepare_defense_data.ps1`
exige un `-SourceDataDir` que ya contenga
`sensor__pergamino-ensemble-demo.parquet` y
`ui_metadata/operational_v2__pergamino-ensemble-demo.json` con hashes
SHA-256 fijos (`F6F9E19A...`/`FCD7AC52...`, ver el script), y los 9 bundles
reales del ensamble (`PRODUCER_BUNDLE_ROOT`). Esos tres artefactos se
generaron en una corrida real única, autorizada explícitamente el
2026-09-26 sobre CSVs externos de ERA5-Land/NASA POWER que **no están
versionados en este repositorio** (`docs/design/ensemble-real-execution-report-2026-09-26.md`).

Por mandato de esta tarea, **no se reentrenó ni se regeneraron emisiones**
para suplir esta ausencia. Para recorrer Pergamino:

1. Obtener (fuera de este repositorio, por canal ya autorizado) el
   `PRODUCER_DATA_DIR`/`PRODUCER_BUNDLE_ROOT` reales ya preparados, o
   reproducir la corrida documentada en
   `docs/design/ensemble-real-execution-report-2026-09-26.md` con permiso
   explícito del responsable (requiere los dos CSV externos con sus hashes
   verificados).
2. Verificar los hashes con `Get-FileHash -Algorithm SHA256` contra los
   valores fijados en `scripts/prepare_defense_data.ps1` antes de usarlos.
3. Copiar a un directorio de demo aislado con
   `./scripts/prepare_defense_data.ps1 -SourceDataDir <...> -DemoDataDir .demo-defense-data\session-N`
   (rechaza destinos existentes y raíces fuera de `.demo-defense-data/`).

**Este es el hallazgo central de la Etapa 1 de esta tarea**: el arranque de
Pergamino queda documentado y con validación de artefactos, pero su
reproducción de punta a punta desde un checkout limpio permanece
condicionada a un artefacto externo no versionado, por diseño (evita
versionar datos de terceros/reanálisis de gran tamaño y procedencia
externa). No es un defecto a corregir en esta entrega.

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
- **Pergamino**: no ensayado — bloqueado por el artefacto externo descrito
  en la sección 2, tal como se documentó en el hallazgo de Etapa 1.

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

## 8. Limitaciones conocidas de esta entrega

- Pergamino no puede recorrerse de punta a punta desde un checkout
  completamente limpio sin el artefacto externo descrito en la sección 2 —
  esto es una restricción de procedencia de datos, no un defecto del
  mecanismo de arranque.
- Esta guía no reemplaza `docs/research/protocolo-experimental-v3.md` (v3,
  congelado) ni el protocolo `controlled_daily_v4_external_pergamino`
  (ADR-0011); tampoco reinterpreta la retrospectiva exploratoria 2023
  (`docs/research/ensemble-retrospective-evaluation-protocol.md`), que
  permanece una evaluación exploratoria, no confirmatoria, sin resultado de
  superioridad atribuido.
