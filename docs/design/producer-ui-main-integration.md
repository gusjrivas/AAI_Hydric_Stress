# Integración de UI y backend para productor — preparación del cierre

Fecha: 2026-09-21. Estado: **integración parcial validada; no lista para merge**.

## Base y trazabilidad

Rama `feat/hu6-productor-integracion-final`, worktree aislado
`C:/Repo/AAI_Hydric_Stress_integration`.

- Base: `origin/main` en `a657014` (PR #206, prerrequisitos científicos).
- Backend incorporado: `2e22c6f`, `feat/hu6-backend-soporte-ui`.
- UI incorporada: `a250a9e`, `feat/hu6-ui-productor-integracion`.
- Conflicto de seguimiento resuelto conservando ambas entradas.
- Los cambios locales de las ramas originales no se incluyeron ni modificaron.

HU2/HU4/HU5/HU6, capacidades `data-ingestion`, `predictive-modeling`,
`human-feedback`, `architecture-integration` y `alerting-ui`.
CRISP-DM: integración y verificación del despliegue. Esta entrega no cambia
configuración experimental, hipótesis ni arquitectura. No ejecuta entrenamientos,
abre holdouts ni modifica datasets o resultados históricos. El cierre científico
HU7/HU8 continúa siendo independiente. Aporte a memoria: capítulo 3, integración
verificada y límites funcionales; sin nuevos resultados para capítulo 2.

## Ajustes de integración

- La cabecera de Mi cultivo omite el selector legacy, que no controla esa vista.
  El selector de sector/punto v2 permanece como contexto visible. Al regresar a
  Resumen se conserva el sensor legacy previo, comprobado por una prueba de navegación.
- Compose transmite `PRODUCER_V2_ENABLED`, desactivado por defecto. `.env.example`
  documenta el opt-in. Verificados los valores true y false mediante `compose config`.
- Reparada la estructura canónica de `architecture-integration`: Purpose identifica
  la descripción existente, Limitaciones queda después de todos los requisitos y
  se añade el marcador equivalente MUST a DEBE. Sin cambios de comportamiento
  normativo. Tarea 1.12 cerrada tras validación estricta; no se archivaron changes.

## Verificación reproducible

Frontend, desde `frontend/`: `npm ci --no-audit --no-fund`, `npm test`,
`npm run lint`, `npm run build`: **132 tests / 20 archivos**, lint y build correctos.
La suite inicial tenía 131 tests; esta entrega agrega una prueba de navegación.
Los 135 reportados en otro worktree no se reproducen en este checkout publicado.

Backend: **94 passed, 11 warnings**, 248 segundos. Ejecutado en contenedor
`aai-hydric-full:dev`, Python 3.11, repositorio montado de solo lectura en `/repo`,
`PYTHONPATH=/repo/src:/repo/backend`, `PYTHONDONTWRITEBYTECODE=1`, directorio de
trabajo `/tmp`; comando `python -m pytest /repo/backend/tests/ -q --tb=short -p no:cacheprovider`.
La imagen requirió instalar `httpx2` en el contenedor efímero para su versión de
Starlette. El primer intento falló en colección por esa dependencia; el segundo
produjo 18 fallos al escribir MLflow en el montaje de solo lectura. El intento
final resolvió el entorno usando `/tmp`; no requirió alterar código backend.
Este entorno verifica contratos/regresiones HTTP, no acredita reproducibilidad
experimental del manifiesto, cuyo entorno fijado es distinto.

Los cuatro changes `add-producer-sensor-catalog`,
`add-daily-multihorizon-predictors`, `extend-dated-alert-feedback` y
`add-producer-forecast-api` pasan `openspec validate <change> --strict`.
La spec canónica `architecture-integration` pasa también validación estricta;
solo queda una sugerencia informativa por longitud de un requisito.

No se declara CI verde, suite completa de dominio ejecutada ni revisión visual
actual por estas pruebas. CI debe aportar su resultado independiente en el PR.

## Activación local

En el checkout de integración, establecer `PRODUCER_V2_ENABLED=true` en `.env`
(o en la sesión PowerShell antes de iniciar Compose) y reconstruir backend/frontend.
Abrir `http://localhost:5173/#productor`. La ruta inicial legacy sigue siendo
Resumen. No levantar otro stack con el mismo nombre/puertos mientras estén en uso.
Para desactivar la fachada v2, restablecer false y recrear backend; los archivos
persistidos no se borran. Registrar sensores no crea mediciones ni pronósticos.

## Condiciones pendientes para cerrar y mergear

1. Incorporar el orquestador y sus fixtures cuando la sesión que los implementa
   termine y publique. Sus archivos locales no forman parte de esta integración.
2. Completar el recorrido modelo → snapshot → emisión persistida +1/+2/+3 → API → UI,
   con identidades y decisiones de publicación verificadas. Actualmente la UI puede
   consultar/revisar registros, pero no generar esas emisiones reales.
3. Completar la evidencia operacional conforme al manifiesto congelado y exponer
   sus assessments. Un porcentaje ausente por evidencia insuficiente es válido;
   no suplirlo con scores crudos, porcentajes inventados ni repeticiones de t+3.
4. Cerrar la experiencia de productor: entrada y navegación coherentes, registro
   de sectores/puntos y recorrido de pronósticos, pendientes y correcciones.
   La versión integrada sigue siendo incremental, no el mock completo aprobado.
5. Resolver las tareas v2 aún abiertas de resumen/linaje y recalibración según
   los changes aceptados. No presentarlas como implementadas por conservar legacy.
6. Verificar en navegador contra esta misma integración: selección, historial,
   tres fechas objetivo, revisión desde el día objetivo sin vencimiento,
   corrección/conflicto, recarga y persistencia; escritorio, teclado y móvil real.
7. Reconciliar contratos/canónicas y tareas con esa evidencia, completar CI y
   revisión del PR. Solo entonces quitar el estado de borrador y mergear a main.

La ausencia actual de emisiones se mantiene explícita en pantalla. Una prueba
sembrada con fixtures valida transporte y feedback, no validez predictiva ni
calibración. Este documento no autoriza relajar el manifiesto para conseguir
porcentajes ni convierte una evaluación exploratoria en evidencia científica formal.
