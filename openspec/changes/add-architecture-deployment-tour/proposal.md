# Change: Diagrama de despliegue y recorrido ilustrativo en Arquitectura

- HU6/HU7 (presentación) · `alerting-ui` · CRISP-DM Deployment. Sin impacto científico, de API ni de permisos.
- Problema: la vista `#arquitectura` describe las siete etapas del pipeline de IA, pero no muestra los componentes técnicos de la aplicación ni cómo se conectan, que es lo que un jurado necesita para entender la implementación (Capítulo 3).
- Cambio (solo presentación): se agrega a `ArchitectureFlow` un diagrama de despliegue con los componentes de Docker Compose (frontend, backend, núcleo Python, modelos, volumen `data/`, MLflow, PostgreSQL, MinIO y `demo-control` opcional) y sus conexiones, con fichas por componente, alternativa textual en tabla y un recorrido ilustrativo animado de nueve pasos.
- Las siete etapas existentes, sus enlaces y la tabla de componentes se conservan sin cambios.
- El recorrido es un guion fijo: resalta componentes y conexiones y muestra un subtítulo. No consulta servicios, no muestra datos, métricas, estados ni tiempos, y se rotula como ilustrativo. MLflow aparece únicamente en los pasos de recalibración, porque el pronóstico no lo utiliza.
- Cada componente cita rutas del repositorio y puertos declarados en `docker-compose.yml`; una prueba verifica ambas cosas.
- Accesibilidad: controles de reproducción, pausa, anterior, siguiente y salida; subtítulo en región `aria-live`; con `prefers-reduced-motion` no hay avance automático ni animación.
- Non-goals: telemetría real, estado de salud de los servicios, enlaces al repositorio remoto, cambios de datos, modelos o experimentos. Rollback: revertir el PR.
