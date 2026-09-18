# Diseño de integración

La fuente normativa de campos y rutas es [api-contract.md](api-contract.md).
Los otros changes son dueños de semántica de datos, modelado y feedback.
FastAPI valida y delega a servicios de src; no entrena ni decide elegibilidad
dentro de routers. Reutilizar adaptadores existentes sin cambiar su comportamiento.

## Consistencia
La emisión captura un snapshot inmutable común para los tres horizontes.
Se guardan filas de entrada y fingerprint, contratos y bundles usados. Cada
slot exitoso es inmutable. Un fallo parcial no se sustituye por alerta negativa.
Retries con igual clave devuelven igual respuesta. Otra clave puede completar
slots fallidos del mismo snapshot, nunca reemplazar éxitos; la tanda incrementa
revision. Si cambió el contenido del día ya emitido, retornar conflicto explícito,
conservando la tanda original. Una política de reemisión de éxitos queda fuera.
Las lecturas GET no disparan entrenamiento, generación de datos ni registro.

## Alcance de experiencia
Resumen seleccionado por sensor o por primary_sensor_id del sector. Un sector
sin primario exige selección; nunca promediar sensores implícitamente.
La UI obtiene nombres, vigencia, históricos y estado diario del servidor.
La fecha de datos puede ser antigua: +1/+2/+3 se anclan a esa fecha, no a hoy.
No presentar una tanda histórica como pronóstico actual. El historial muestra
mediciones observadas; no rellenar huecos con la línea de predicción.
No exponer arquitectura como navegación del productor. El linaje queda
disponible en detalle, con traducción comprensible en la futura UI.

## Compatibilidad y despliegue
Rutas v2 y almacenamiento separados; los endpoints vigentes y la demo acelerada
mantienen contratos. No ampliar el controlador demo en este change. Durante
demo activa, las mutaciones manuales que interfieren con su sensor retornan
demo_write_locked; consultas siguen permitidas. Registrar metadatos no cambia
series existentes. No hay migración destructiva ni reescritura de parquet formal.
Configurar activación explícita de v2; desactivarla conserva todos sus registros.
No ejecutar train desde inicio del servidor o GET. Preparar rollback de facade
sin borrar datos. La autenticación existente se conserva; no introducir usuarios
ficticios ni atribuir identidad humana no autenticada.

## Cierre
Tests de contrato con fixtures disponibles/parciales/vacíos/errores, aislamiento
de sensores y catálogo, consistencia tras reinicio, causalidad y regresión legacy.
Verificar OpenAPI contra ejemplos y pruebas de consumo frontend independientes.
No declarar CI verde ni tareas completas hasta ejecutarlas en implementación.
