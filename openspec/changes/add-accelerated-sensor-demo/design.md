# Diseño de la demostración diaria acelerada

## 1. Organización

Nuevo paquete de herramientas `scripts/demo_simulation/`: configuración, generación
de payload, almacén de sesión, worker, CLI y adaptador HTTP. Reutiliza
`data_ingestion.mock_sensor.generate_next_reading`, nombres de sensor y contrato de
almacenamiento. No modifica generadores ni entrenamiento en `src/`.

La UI añade una entrada secundaria «Demostración» cuando está configurado el
controlador. Los hashes operativos y el funcionamiento sin demo se conservan.
Los detalles de preparación pertenecen al README/CLI, no al flujo del productor.

## 2. Preparación explícita

Comando propuesto:

```text
python -m scripts.demo_simulation prepare --start YYYY-MM-DD --days 10 --history-days 120 --seed 42
python -m scripts.demo_simulation serve
```

Los valores son ilustrativos, no parámetros científicos ni garantía de viabilidad.
`prepare` genera un identificador `demo-<id>` nuevo y valida fechas, historial,
cantidad de pasos, semilla y ausencia de recursos previos. No acepta `--force` ni un
sensor operativo arbitrario. Si falla la preparación, deja estado incompleto
diagnosticable; no inicia el worker ni reutiliza silenciosamente el directorio.

La historia termina en `start - 1 día`. Se guarda únicamente ese prefijo sintético;
no se prepublica la secuencia posterior en el dataset consumido por el modelo.
No se copian datos, feedback o modelos de `sensor-a` ni de otros sensores.

El período completo debe ser pasado: `end + horizonte < hoy UTC`, con horizonte
obtenido del contrato operativo mediante GET de predictor, sin asumir que siempre
será 3. Si el contrato no se puede consultar, no se prepara la sesión. Que la fecha
objetivo sea pasada no significa que esté presente en el dataset simulado.

Todos los registros llevan procedencia sintética. Se envían las columnas del mock,
incluida `et0`; no se omite esa variable como sucede en el cliente simple actual.
La generación usa semilla base y offset de día reproducibles, sin elegir semillas
para obtener determinadas alertas. No usa información del día siguiente.

## 3. Secuencia causal de un paso

1. Validar propiedad de sesión, consistencia del dataset y ausencia de modificaciones externas conocidas.
2. Generar el día `d` a partir del último día aceptado. Persistir el payload exacto, su hash y fase `ingesta_pendiente` antes del POST.
3. Enviar `POST /sensors/{sensor_id}/readings`. Verificar fecha y cantidad de filas; persistir `ingestado`.
4. Verificar que el dataset del backend no contiene días posteriores a `d` y que la fila coincide con el payload normalizado. El controlador local tiene acceso de lectura al mismo almacenamiento mediante el contrato, no mediante lectura Parquet ad hoc.
5. Persistir `pronostico_pendiente`; enviar `POST /forecast/{sensor_id}/run`.
6. Verificar fecha `d`, fecha objetivo y registro mediante `GET /feedback/{sensor_id}`. Conservar el veredicto original. Persistir `completado` para el paso y avanzar el cursor.
7. Esperar el intervalo antes de iniciar el siguiente día; nunca superponer solicitudes de pasos distintos.

No se llama directamente al modelo ni se fabrica un resultado cuando la API retorna
422 o no existe historial entrenable. El error queda visible y la sesión no avanza.
La ingesta puede quedar aplicada aunque falle el pronóstico: se muestra esa diferencia.

Intervalo configurable entre 1 y 60 segundos, 5 por defecto, medido **después** de
terminar el paso anterior. No se promete una predicción cada cinco segundos si el
entrenamiento tarda más. El avance representa días simulados completos, no lecturas
subdiarias reales ni una estimación de latencia productiva.

## 4. Estado persistido y exclusión

Estados de sesión: `prepared`, `running`, `pausing`, `paused`, `blocked`, `completed`.
Fases de paso: `pending`, `ingest_pending`, `ingested`, `forecast_pending`, `completed`.
Registrar identificador, sensor, fechas, semilla, versión del generador/código,
contrato, parámetros, cursor, revisión monotónica del estado, request de control,
payload/hash, hash del dataset aceptado, resultado confirmado y último error.

Guardar manifiesto por reemplazo atómico, sin secretos, fuera de artefactos HU7/HU8.
Un lock de sistema operativo por sesión impide dos workers; un registro exclusivo del
controlador impide dos sesiones activas simultáneas. No basta con un booleano React.

Pausar pasa a `pausing`: termina/reconcilia el paso actual y no inicia otro. No cancela
un POST en vuelo. Cerrar la pestaña no pausa el worker. Al reiniciar el controlador,
ninguna sesión continúa automáticamente: queda pausada o bloqueada según el diario.
Una sesión completada conserva todos sus resultados y no admite rebobinar.

## 5. Fallos y recuperación

No hay transacción distribuida ni idempotency-key en las APIs actuales. El requisito
es no duplicar registros ni avanzar sin confirmación; **no** garantizar una única
ejecución interna del modelo o un único run ante una pérdida de respuesta.

- Respuesta de ingesta perdida: comparar la fila persistida con el payload pendiente; si coincide y el request ya terminó, marcar ingesta confirmada. No reenviar otra lectura aleatoria para esa fecha.
- Pronóstico con respuesta perdida: GET del registro para `d`; si existe completo y no hay request activo, reutilizarlo y continuar sin volver a pronosticar.
- Si no puede comprobarse que el request original terminó (incluido reinicio del worker con el backend aún trabajando), bloquear. No considerar un timeout como confirmación de cancelación ni reintentar POST automáticamente.
- Una fase sin efectos verificables solo se reintenta mediante orden explícita, después de comprobar que no hay operación anterior en vuelo. Si no puede probarse, conservar la sesión bloqueada; no avanzar.
- Cambios de datos o contrato ajenos a la sesión: bloquear con motivo. No sobrescribir ni borrar recursos para “reparar” la demo.
- Reinicio después de guardar el resultado y antes de avanzar cursor: reconciliar por fecha, recuperar ese resultado y continuar al día siguiente.

## 6. Contrato del controlador local

Base propuesta `http://127.0.0.1:8010`, configurable por entorno al iniciar. El backend
de destino se fija en configuración local; no se permite elegir URLs desde HTTP.

| Operación | Contrato |
|---|---|
| `GET /demo/session` | Devuelve sesión preparada/activa o 404 si no hay; no crea recursos ni avanza. |
| `POST /demo/session/start` | Inicia `prepared`, con `session_id`, `expected_revision` y `request_id`. |
| `POST /demo/session/pause` | Solicita pausa; responde con el estado real, incluso `pausing`. |
| `POST /demo/session/resume` | Continúa `paused`; `blocked` exige reconciliación satisfactoria, nunca salta comprobaciones. |

Las órdenes contienen el mismo sobre de sesión/revisión/request. Repetir un request
devuelve su resultado registrado; revisión obsoleta, sesión diferente o transición
inválida retornan 409. Persistir aceptación antes de despertar el worker. GET devuelve
estado, fase, cursor, fecha simulada, días totales/completados, última fecha ingerida,
última fecha pronosticada, intervalo, revisión y error legible, sin rutas locales.

Perfil Docker `demo` separado, servicio local opcional; reutilizar entorno Python
del proyecto y conectar al backend por red Compose. El controlador necesita el
almacenamiento del backend de solo lectura durante ejecución y su directorio de
sesiones escribible. La preparación CLI usa acceso de escritura explícito al crear
el nuevo sensor. No editar el `docker-compose.override.yml` local del usuario.

## 7. Interfaz y actualización

Mostrar «Demostración con datos simulados», «Día simulado», «Días recorridos» y
controles «Iniciar», «Pausar», «Continuar». Sensor y fechas vienen del controlador;
no etiquetar estos valores como datos de campo actuales. Mostrar preparación pendiente
con instrucciones breves para quien configura la demo; no inventar una sesión.

Consultar estado cada 2 segundos solo al observar la sesión, sin requests GET
superpuestos. Al cambiar la revisión/fecha confirmada, actualizar calidad e historial
del sensor demo con GET. Al volver a la pestaña, consultar estado inmediatamente.
Un error de consulta no equivale a pausa: mostrar «No se pudo consultar el estado;
la demostración podría seguir en marcha». Conservar contadores confirmados.

Durante la ejecución/pausa/bloqueo, la UI no permite pronóstico manual, validaciones
ni ajustes para ese sensor. Puede consultar otros sensores sin cambiar el objetivo
del worker; se mantiene acceso para volver al sensor demo. Los clientes externos
siguen fuera de la exclusión de UI: el sensor demo debe reservarse a esta sesión.

Al completar, habilitar revisión humana solo para filas cuya fecha objetivo esté
dentro del período ingerido y haya terminado en UTC. Esto es una restricción de UI
adicional; nunca sustituye la autoridad del backend. Las últimas filas pueden no
tener observación futura disponible y deben indicarlo. No producir feedback humano
automático ni mover el reloj real para eludir 409. Una recalibración posterior usa
las reglas actuales; no se reanuda ni rebobina la sesión completada.

## 8. Verificación y límites

Tests de API con directorios temporales y registro de modelos aislado o doble de
prueba declarado. Nunca usar recursos reales del usuario para QA. Integración real
solo sobre sensor nuevo de demo, documentando los recursos creados y conservándolos
sin limpieza destructiva automática. Datos, predicciones y validaciones de esta demo
no sustentan conclusiones HU7/HU8.

El generador actual no es un modelo físico de cultivo: no garantiza estacionalidad,
balance hídrico o plausibilidad conjunta. Esta primera entrega demuestra el circuito;
el realismo y los escenarios de secado/lluvia requieren un change posterior.
