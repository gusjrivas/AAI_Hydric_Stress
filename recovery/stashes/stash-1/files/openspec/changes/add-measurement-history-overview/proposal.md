# Change: Historial visible y fecha del pronóstico en el inicio

## Why

El resumen no permite ver cómo cambió la humedad del suelo. Además, una alerta
registrada puede interpretarse como una predicción actual o como una proyección
para todos los próximos días. El inicio debe explicar ambos conceptos a personas
sin conocimientos de la arquitectura.

## What Changes

- Mediciones históricas de humedad en un gráfico, con ventanas de 7, 30 y 90 días
  calendario terminadas en la última medición disponible; tabla accesible de detalle.
- Últimos valores de humedad, temperatura y lluvia, con fecha, unidades y procedencia.
- Pronóstico separado, fecha objetivo y distancia respecto de los datos usados.
  Los objetivos pasados se identifican como históricos.
- Consulta GET de solo lectura `/sensors/{sensor_id}/history?days=30`, aislada por
  sensor. No imputa valores, genera datos ni ejecuta modelos.

## Trazabilidad y límites

- HU6; capacidad `alerting-ui`; capa de presentación y fachada HTTP (ADR-0003).
- CRISP-DM: comprensión de datos y despliegue e integración experimental.
- HU2/HU4: se presentan valores y resultados existentes, sin cambiar sus contratos.
- Configuraciones base/+sintéticos/+anomalías/completa: sin impacto.
- HU7/HU8, `controlled_daily_v3`, hipótesis, alcance y arquitectura: sin cambios.
- Memoria: capítulo 3, presentación de mediciones y estimaciones; se preserva la
  causalidad temporal explicada en capítulo 2 y ADR-0009.
- El modelo operativo conserva t+3. No existe una proyección diaria completa ni a
  siete días. Incorporar t+7 requiere otro change de HU4 con evaluación temporal;
  no se puede implementar extrapolando resultados en la UI.
- No se presenta la salida del modelo como probabilidad calibrada ni se automatiza riego.

## Validación

96 tests frontend, lint y build aprobados. 13 tests backend de historial e ingesta
aprobados en contenedor descartable con repositorio de solo lectura. La imagen de
pruebas requirió instalar `httpx2` para su versión de Starlette; no se modificaron
dependencias del proyecto. Revisión visual de escritorio, móvil y teclado pendiente:
el navegador de esta sesión no está conectado.
