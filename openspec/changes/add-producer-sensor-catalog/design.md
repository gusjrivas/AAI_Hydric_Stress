# Diseño

## Modelo y persistencia
Sector: sector_id inmutable, display_name, crop opcional, primary_sensor_id
nullable, revision, created_at UTC. Punto: sensor_id validado por el validador
existente, display_name, sector_id nullable, source_kind declarado
(real/synthetic/unknown), revision, created_at UTC. Texto no vacío tras trim;
nombres de 1 a 80 caracteres; crop hasta 80; IDs no son nombres visibles.

Un sector admite varios puntos pero solo uno seleccionado para el pronóstico.
No se combinan lecturas. Cambiar primary_sensor_id exige pertenencia al sector.
Cambiar nombre no mueve datos ni altera pronósticos. Reasignar de sector un punto
con lecturas o emisiones se rechaza con conflicto; no se cambia retroactivamente
la atribución. No hay eliminación en esta entrega.

Repositorio de metadatos bajo data/ui_metadata, separado de sensor__*, feedback
y datasets de investigación, usando acceso versionado y escritura atómica con
exclusión mutua también entre procesos. Restricción única sensor_id/sector_id y
control optimista de revision: no perder cambios concurrentes.
GET no crea ni migra recursos. Alta no crea lecturas ni registra modelo.

## Compatibilidad con series existentes
La ingesta legacy sigue admitiendo sensor_id válido sin catálogo.
Listado diferencia puntos registrados y series locales no catalogadas mediante
descubrimiento acotado exclusivamente a nombres sensor__ válidos. Adoptar una
serie existente registra metadatos, nunca copia, renombra o modifica su Parquet.
source_kind declarado no reemplaza origen por fila. Si hay mezcla, reportar mixed;
si no se sabe, unknown. Nunca inferir real por ausencia de etiqueta sintética.

## Historial y consistencia
Snapshot de bytes único, hash de contenido como snapshot_id. Ventana de días
calendario contigua, anclada a fecha explícita o última lectura, sin compactar
huecos. Historial ascendente devuelve solo filas almacenadas, nulos intactos,
lista missing_dates y completitud por variable sobre días esperados.
No interpolar, suavizar, ejecutar anomalías o entrenar por consultar.
last_reading_date es la última lectura global del sensor, independiente de la ventana.
Valores no finitos se normalizan a null con incidencia, no desaparecen sin aviso.

Las siete variables del contrato se pueden consultar con unidades explícitas.
Humedad conserva m3/m3 en API (UI convierte a %); humedad relativa %, radiación
MJ/m2/day, temperatura degC, precipitación y ET0 mm/day, viento m/s.
input_roles refleja el contrato del predictor seleccionado: no confundir
variables disponibles con variables efectivamente usadas. Si no hay predictor,
usar basis=configured, nunca basis=issued. Anomalías son diagnóstico separado del modelo.

Sin dataset para un punto registrado: conjunto vacío, fechas nulas y estado
no_readings. Dataset desconocido y sin catálogo: not_found. Error de lectura:
error tipado, nunca vacío. Calendario inválido: conflicto con motivo diagnóstico;
no compactar duplicados o fechas subdiarias para ocultar el problema.
