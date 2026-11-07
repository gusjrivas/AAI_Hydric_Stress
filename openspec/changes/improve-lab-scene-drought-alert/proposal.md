# Change: Laboratorio como escena, con sequía y alerta

- HU6/HU7 (presentación) · `alerting-ui` · CRISP-DM Deployment. Sin impacto científico, de API ni de permisos.
- Problema: el laboratorio mostraba cuatro botones al final de una página de unos 3200 px, no tenía ningún gráfico y el generador de lecturas (paso aleatorio independiente por variable) no podía producir una condición de estrés hídrico. Por eso la demostración nunca mostraba una alerta y no se entendía qué aportaba cada paso.
- Cambio (solo presentación y generador del laboratorio, en `frontend/`):
  - Controles al inicio de la página y botón «Ver la demostración», que ejecuta los pasos pendientes con una pausa de 6 segundos entre cada uno.
  - Escena con dos gráficos (humedad del suelo con los pronósticos emitidos, y temperatura con el rango físico esperado), un subtítulo «Qué hizo el sistema» por paso e indicadores de calidad y de último pronóstico. Todo se deriva de lo que el backend ya devolvió.
  - Generador de balance hídrico: la lluvia recarga el suelo y la temperatura y la radiación lo secan, de modo que el clima y la humedad están relacionados.
  - Paso E «Simular una sequía»: 14 días secos y calurosos, sin lluvia, y un nuevo pronóstico real.
  - Los textos de explicación y la trazabilidad pasan a un bloque plegable, sin eliminarse.
- El resultado del paso E lo decide el predictor operativo. La escena muestra el veredicto del backend (alerta o sin alerta, con su probabilidad) y no dibuja ningún umbral, porque el backend no lo informa.
- Verificación contra el backend real (`labAlert.integration.test.ts`, solo con `LAB_BACKEND_URL`): con la semilla fija 42 los pronósticos de A, B y D no alertan y el de E alerta (probabilidad 0,60). En un barrido de 12 semillas, 7 cumplen ese contraste; una falla en el paso A por falta de ejemplos de ambas clases. La alerta tras una sequía es un comportamiento real del sistema, pero no ocurre con cualquier semilla: la semilla fija es un caso de demostración elegido y verificado.
- Los datos siguen rotulados como sintéticos y como no evidencia científica. La alerta de la demostración no es una medida de la precisión del modelo.
- Non-goals: cambiar el backend, los modelos, los umbrales o los experimentos. Rollback: revertir el PR.
