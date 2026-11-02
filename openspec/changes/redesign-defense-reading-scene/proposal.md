# Change: Lectura rápida del caso real en la pantalla de defensa

- HU6 (presentación) · `alerting-ui` · CRISP-DM Deployment. Sin impacto científico, de API ni de permisos.
- Problema: la pantalla del recorrido histórico de Pergamino y Melchor Romero presenta unas 330 palabras antes del primer dato, repite tres veces el carácter histórico y externo de los datos, expone cuatro cuadros con las mismas fechas y deja el resultado y la revisión al final de la página. Resulta difícil interpretar qué predijo el sistema y qué ocurrió después.
- Cambio (solo presentación, en `frontend/`, solo en modo defensa):
  - Título con la conclusión de la emisión («Según los modelos, sin alerta de humedad baja…»), derivado únicamente de los veredictos que devuelve el backend, y dos rótulos de origen.
  - Selector de las emisiones preparadas como grupo de botones y control deslizante para el reloj del recorrido, en lugar de la lista, el campo de fecha y los botones de día.
  - Escena única: gráfico de humedad del suelo con el umbral del protocolo y una franja con un veredicto por horizonte (+1, +2, +3), con ícono y palabra y con la votación de los modelos («2 de 3 modelos indican alerta»).
  - Panel de revisión (HITL) del horizonte elegido: confirmar o rechazar tanto una alerta como una ausencia de alerta, con el mismo flujo, la misma idempotencia y las mismas reglas de apertura que ya existen.
  - Calidad de datos en una línea; cómo leer, procedencia y límites, trazabilidad, observaciones y evidencia en pestañas.
- La pantalla no muestra probabilidades, porcentajes ni puntajes por modelo. El veredicto es el que entrega el backend; la votación de los modelos es una dimensión separada y no se presenta como la regla de decisión.
- La pantalla no calcula si un pronóstico «acertó»: muestra el dato real revelado con su procedencia (observado, imputado o no verificado) y la persona decide en la revisión.
- Non-goals: cambiar el backend, los modelos, los umbrales, los permisos de escritura o la revisión de otras pantallas. El modo no defensa de `HistoricalWalkthrough` y la pantalla «Mi cultivo» no cambian.
- Rollback: revertir el PR.
