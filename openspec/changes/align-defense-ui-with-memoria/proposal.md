# Change: Coherencia de los textos de la presentación con la memoria técnica

- HU6 (presentación) · `alerting-ui` · CRISP-DM Deployment. Sin impacto científico, de API ni de permisos.
- Problema: el video de defensa muestra la interfaz mientras se expone la memoria V5.1. Varios textos de la interfaz usan términos o afirmaciones que la memoria no sostiene: «votación de los modelos» como si fuera la regla de decisión (la ecuación 3.1 define el promedio de las salidas con corte 0,5 y los votos como indicador de acuerdo), «umbral del protocolo» sin indicar que es un percentil 20 del entrenamiento, «Replay histórico» en lugar de «reproducción histórica», una lista de variables de entrada que la memoria no documenta, «datos reales» para productos de reanálisis, «ensamble por acuerdo» en lugar de ensamble por promedio, probabilidades en el laboratorio y nombres internos de configuración en los resultados.
- Cambio (solo textos, en `frontend/`):
  - «Acuerdo entre modelos» en lugar de «Votación de los modelos»; el texto de lectura menciona la información disponible hasta la fecha de emisión y no enumera variables.
  - La frase del umbral indica «umbral relativo: percentil 20 del entrenamiento».
  - Rótulos de los casos según el origen de datos de la tabla 3.6 y aclaración de que Melchor Romero no es la ejecución experimental.
  - «Reproducción histórica» como rótulo de modo.
  - Diagrama de despliegue: «ensamble · promedio» y paso 4 sin la palabra «riesgo».
  - Laboratorio: sin probabilidades; el veredicto se muestra como alerta o sin alerta.
  - Resultados: nombres de métodos y de configuraciones de la memoria, encabezado del experimento v3 como evaluación de Melchor Romero 2024 con 67 casos comunes, y descripción de la retroalimentación humana según la sección 4.6.
- Fuera de alcance, a decisión de la autoría: el estado de gobernanza «FAIL por ejecución duplicada» (la memoria no lo menciona), el voseo de la interfaz, el componente opcional `demo-control` y la separación visual entre servicio de aplicación y núcleo en el diagrama.
- Non-goals: cambiar el backend, los modelos, los umbrales o la evidencia congelada.
- Rollback: revertir el PR.
