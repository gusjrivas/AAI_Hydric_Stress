# Diseño propuesto

## Identidad y persistencia
forecast_id identifica sensor, fecha de datos, horizonte y versión de contrato.
El registro inmutable conserva fecha objetivo, emisión, predicción, score, modelo,
snapshot y procedencia. Dos emisiones con igual target_date son distintas si difieren en as_of_date u horizonte; la misma clave lógica no admite reemisión exitosa.
La revisión es un evento append-only en almacenamiento v2 separado: review_id,
request_id, revision, forecast_id, action, observed_label, comment, reviewed_at.
La fecha de revisión la asigna el servidor. Escritura atómica y bloqueo entre
procesos; no depender de una variable global en FastAPI.

## Apertura y permanencia
review_open_at es target_date a las 00:00 UTC. La API incluye server_today y
calendar_timezone=UTC para explicar la fecha sin convertirla por navegador.
Antes de esa fecha se rechaza la escritura. Desde entonces no vence, aunque
haya nuevas emisiones o cambie el modelo. Los pendientes antiguos permanecen
consultables. No se altera esta regla usando un reloj enviado por el cliente.
Los sensores del espacio demo- permanecen reservados al flujo legacy en todos sus estados; la regla normativa está en el documento de dependencias enlazado abajo.

confirm registra observed_label igual a la alerta emitida; reject registra su
complemento binario. Ambos aceptan comentario opcional de hasta 2000 caracteres.
La UI debe explicar qué se confirma; una opinión no es verdad fisiológica medida.
Si el usuario no sabe, deja pendiente. No convertir falta de respuesta en rechazo.
Una revisión posterior corrige la opinión mediante otra revisión, sin borrar la
anterior. expected_revision evita pérdida por concurrencia; request_id hace
idempotente el reintento idéntico y rechaza reutilización con otro contenido.

## Captura no equivale a aprendizaje
Una opinión del mismo día queda registrada y cierra el pendiente de usuario.
Antes de finalizar el día objetivo: waiting_target_maturity. Después, si esa
opinión se capturó durante el día objetivo: requires_mature_revalidation.
NO adelantar o reescribir reviewed_at al llegar medianoche. Solo una nueva
revisión explícita posterior al día objetivo puede satisfacer la madurez legacy.
Esto preserva la regla temporal de HU5; el usuario no tiene obligación de volver
a revisar y su opinión original sigue visible.

Una opinión madura todavía puede ser ineligible por modelo fuente incompatible,
contrato/horizonte incompatible o datos insuficientes. Registrar opinión sobre
un modelo viejo sigue permitido: elegibilidad no limita el feedback de usuario.
Recalibración operacional v2 usa exclusivamente correcciones maduras compatibles
del mismo sensor, horizonte, umbral y contrato; conserva correcciones ya
aplicadas y avance monótono de trained_through. Confirmaciones se auditan pero
no se convierten en correcciones de entrenamiento. No reutilizar el selector
legacy sin particionarlo y probar causalidad. Guardar referencias a revisiones
exactas aplicadas: editar una opinión no implica que el modelo ya la incorporó.
Un bundle nuevo pierde cualquier calificación probabilística no reevaluada.

## Compatibilidad
Los endpoints legacy conservan claves y validación temporal existentes. Los
datos legacy son consultables por su API actual; no se migran silenciosamente
ni se habilitan revisiones v2 sobre ellos. El alcance sin vencimiento corresponde
a emisiones v2. Una migración futura requiere contrato explícito y auditoría.
No escribir simultáneamente la misma revisión en dos almacenes divergentes.
No afectar runner experimental ni simulador acelerado ya aprobado.

## Validación
Reloj controlado: instante anterior a apertura, apertura exacta, fin de día y
semanas después. Reinicio, peticiones concurrentes, retry, revisión de modelo
antiguo y dos horizontes con misma fecha objetivo. Probar por separado captura,
selección de entrenamiento y linaje; ninguna prueba necesita abrir holdouts.


## Dependencias resueltas el 2026-09-20
La identidad exacta, transacciones y reserva demo- se rigen por
[decisiones de emisiones y feedback](../../../docs/design/backend-producer-ui-emission-dependencies.md).
La reserva permanente reemplaza la comprobacion de demo activa para mutaciones v2.
