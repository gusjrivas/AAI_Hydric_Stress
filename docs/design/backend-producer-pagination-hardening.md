# Correcciones de paginación operacional — HU5/HU6

Base main 2079d03. Rama fix/hu6-backend-paginacion-robusta, worktree independiente.
Capacidades human-feedback / architecture-integration, CRISP-DM integración.
Sin cambios a arquitectura, hipótesis, modelos, configuración experimental,
manifiestos, datasets ni resultados históricos HU7/HU8. Aporte: capítulo 3.

## Problema y corrección

La paginación buscaba el registro ancla dentro del conjunto ya filtrado por
estado. Si una revisión lo quitaba de pendientes, la búsqueda volvía al inicio,
repitiendo resultados. La continuación ahora compara la clave estable de orden
(target DESC, emisión DESC, ID ASC), sin necesitar que siga presente el ancla.

Además se liga el cursor al sensor y se rechazan rangos de fechas invertidos.
Los contadores actuales se conservan y todas las consultas siguen sin escritura.
No cambia el contrato de revisión, idempotencia, fecha UTC o persistencia.

## Compatibilidad y despliegue

Cursores de una página abierta antes de desplegar este cambio reciben
invalid_cursor: usar Reintentar para reiniciar el listado. No hay migración de
archivos ni cambios de identificadores; rollback de código conserva los datos.
Las opiniones siguen siendo actuales, no un snapshot congelado por el cursor.

## Validación

Pruebas nuevas reproducidas antes de corregir: 4 fallos / 1 éxito. Después:
38 pruebas del archivo de pronósticos correctas, incluyendo concurrencia real,
idempotencia y revisiones. Pruebas de paginación con páginas de 1/2/3 resultados,
empates de fecha, contadores y preservación byte a byte durante los GET.
Regresión completa backend: 106 passed, 12 warnings preexistentes, 117.75 s.
Ejecutada desde backend/ en copia temporal escribible con la imagen de preview y
una copia del fixture histórico requerido por legacy; ningún dataset original
se escribió. Black, Ruff, OpenSpec estricto y git diff --check correctos.
CI remoto pendiente al publicar; no se declara verde por estos resultados locales.

## Continuación

Esta primera entrega corrige fallos funcionales reproducidos. Diagnóstico de salud,
logs correlacionados y medición de crecimiento/contención del almacenamiento
quedan para la siguiente entrega. No se cambia a otro motor de persistencia sin
medirlo y preservar los contratos transaccionales. El frontend queda sin cambios.
