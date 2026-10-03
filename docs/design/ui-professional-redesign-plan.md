# Plan de rediseño profesional de la interfaz

## 1. Objetivo y base

Presentar una propuesta visual única, navegable y coherente de la interfaz, basada
en las capacidades reales del repositorio. Esta etapa es solo de diseño y
prototipado: no integra nada en las pantallas operativas.

- Rama: `design/ui-professional-prototype`
- Worktree: `C:\Repo\AAI_Hydric_Stress_ui_design`
- SHA base (`origin/main`): `b56b97a267045147648c507d68e3ce976f20d946`
- Trazabilidad: HU6 (integración/UI), capacidad OpenSpec `alerting-ui`; fase CRISP-DM
  de despliegue/comunicación. Sin impacto sobre configuración experimental,
  hipótesis, alcance ni arquitectura. Sin impacto sobre HU7/HU8.

## 2. Alcance del prototipo

Ubicación: `design/prototypes/ui-professional/` (HTML, CSS y JS sin dependencias ni
recursos remotos). No toca `frontend/`, el backend ni los artefactos de evidencia.

| Vista | Contenido |
| --- | --- |
| A. Pergamino | Procedencia y período, selección de emisión, reloj histórico, horizontes +1/+2/+3, acuerdo entre modelos, observaciones posteriores, gráfico de humedad, calidad de datos, revisión humana simulada, acceso a evidencia. |
| B. Melchor Romero | Mismo sistema visual con procedencia y período propios, observado/imputado diferenciados y ausencia explícita de evaluación agregada equivalente. |
| C. Laboratorio | Recorrido guiado A–D (normal, anomalía, interrupción, recuperación), sesión, estado, siguiente acción, resultado del paso, línea de tiempo y banda permanente «Simulación · Datos sintéticos · Sin sensor físico». |
| D. Evidencia | Cinco niveles: resumen, comparación por horizonte y métrica, soporte y tabla, detalle técnico, metodología y limitaciones. Pestañas: Pergamino 2023, experimento controlado v3 y Melchor Romero (sin evaluación). |
| Herramientas técnicas | Acceso secundario a las capacidades existentes y catálogo de los diez estados requeridos. |

## 3. Decisiones principales

- **Estructura**: cuatro entradas estables (Seguimiento histórico, Laboratorio, Evidencia,
  Herramientas técnicas). Pergamino y Melchor Romero son una conmutación dentro de
  Seguimiento, con el mismo orden de secciones. En móvil la navegación pasa a una barra
  inferior. No se elimina ninguna capacidad: las existentes quedan en Herramientas.
- **Lectura principal**: franja de contexto (datos, emisión, fechas de aplicación, reloj),
  luego controles, modelos, observaciones, calidad y límites.
- **Paleta**: fondo blanco, azul de marca `#1443b6` (tipo Docker, profundo) para estructura y acción, navy `#081a3d` para texto y datos observados, y cian agua `#00b4d8` como único acento secundario en detalles decorativos. Sin verdes. Contraste de texto AAA (≥ 7:1).
- **Tres lenguajes de estado, sin compartir color**: señal del pronóstico (bermellón / pizarra,
  sin verde porque «sin alerta» no es «sin estrés»), calidad del dato (navy, ámbar y gris
  con trama) y estado de revisión (índigo, contorno o candado). Cada estado lleva ícono y texto.
- **Tokens**: se reutilizan los de `frontend/src/index.css` (fondo, tinta, borde, acción) y la
  tipografía del sistema.
- **Honestidad de los datos**: el acuerdo se muestra como acuerdo, los puntajes no se convierten
  en porcentajes, el promedio se mantiene como política, no se proponen umbrales y no se
  revelan valores posteriores al reloj. Los huecos no se unen en el gráfico.

## 4. Fuentes de los datos de ejemplo

| Dato | Origen | Verificación |
| --- | --- | --- |
| Humedad de Melchor Romero, 14–28 oct 2024; imputación del 26 oct | `data/melchor_romero_2024_consolidado.parquet` (`soil_moisture`) | Valores leídos con pandas y comparados con `backend/tests/test_melchor_romero_readings_provenance.py`. |
| Umbral de Pergamino 0,3131 m³/m³ y puntaje combinado 0,01657 (emisión 15 jun, +1) | `docs/design/ensemble-real-execution-report-2026-09-26.md` | Citados textualmente. |
| Fechas de emisión de ambos sitios, etiquetas de acuerdo y reglas de revisión | `docs/design/ensemble-historical-walkthrough-report-2026-09-26.md` y código de `frontend/src/features/producer/` | Lectura de código. |
| Métricas de Pergamino 2023 | `frontend/public/retrospective-2023.json` | `evidence-data.js` se generó del JSON; incluye su SHA-256 (`6a6a31d3…` para `metrics.json` en el origen). |
| F1 del experimento controlado v3 y sus limitaciones | `frontend/src/features/evidence/formalEvidence.ts` | Comparados valor a valor. |
| **Serie de humedad de Pergamino** | **No existe versionada.** Serie ilustrativa, rotulada así en pantalla. | Solo el umbral es real. |
| **Pronósticos de Melchor Romero y estados con alerta** | No versionados. Tarjetas «Ejemplo de interfaz». | No se atribuyen resultados a Melchor. |

Puntajes por modelo y pronósticos de Melchor Romero no están en el repositorio; el prototipo no los inventa
como resultados: los ejemplos están marcados.

## 5. Apertura

```powershell
python design/prototypes/ui-professional/serve.py
```

URL: <http://127.0.0.1:5290/> (puerto opcional como argumento). También abre con `index.html`
directamente. Las vistas se enlazan por hash: `#/pergamino`, `#/melchor`, `#/laboratorio`,
`#/evidencia`, `#/herramientas`.

## 6. Verificaciones realizadas y limitaciones

Realizadas en Chrome real, con capturas en `design/prototypes/ui-professional/captures/`:

- Carga sin errores de consola; recorrido de las cinco vistas.
- Interacciones: emisión, reloj (botones y selector), detalle por modelo, tabla alternativa,
  formulario de revisión (validación, guardado simulado, corrección), estados de ejemplo,
  carga y error con reintento, pasos y escenarios del laboratorio.
- Sin desbordamiento horizontal en las cinco vistas a 390 px y a 1225 px.
- Controles interactivos de al menos 44 px (salvo el checkbox, contenido en una fila de 44 px) y
  sin controles sin nombre accesible.
- Contraste de texto HTML ≥ 7,25:1 en las cinco vistas, a ambos anchos y con estado de alerta;
  bordes de controles ≥ 4,7:1 (medido por script con la paleta final).
- Orden de tabulación coherente y foco visible de 3 px.
- El frontend operativo y el backend no se modificaron (`git diff` limitado a `design/` y `docs/`).

Limitaciones reales:

- **No se pudo verificar contra el backend**: `scripts/start_defense_demo.ps1` falló al leer la identidad del
  proceso, y el backend no arrancó porque Windows App Control bloqueó una DLL de scikit-learn en un
  entorno virtual nuevo (`_loss`). No se eludió la restricción. El frontend actual sí cargó
  (con «Failed to fetch» al no haber backend). Los contratos se contrastaron solo por lectura de código.
- El ancho de escritorio capturado fue de 1225 px (no 1440 px) porque la ventana del navegador no se
  redimensionaba de forma fiable; la vista móvil de 390 px se renderizó en iframes del mismo navegador.
- El contraste de las etiquetas SVG del gráfico no se midió; usan tonos oscuros de la misma paleta.
- Prueba de teclado parcial (orden y foco); sin lector de pantalla.
- Capturas intermedias del navegador salieron con artefactos de pintado; se repitieron hasta obtener las incluidas.

## 7. Etapas

| Etapa | Contenido | Criterio de aceptación |
| --- | --- | --- |
| 1. Propuesta visual (esta) | Prototipo aislado de las cuatro vistas y herramientas. | Se abre con un comando, se recorre completo, se ve en móvil y se aprueba visualmente. Sin cambios en la app operativa. |
| 2. Integración | Portar tokens y componentes compartidos al `frontend/`; reemplazar las pantallas Pergamino, Melchor, Laboratorio y Evidencia usando los contratos reales; mover las capacidades existentes a Herramientas técnicas. | Sin cambio de contratos ni de rutas funcionales no acordadas; tests del frontend y verificación visual con backend real; estados y reglas científicas intactos. |
| 3. Cierre | Revisión con datos reales, accesibilidad completa, retiro del prototipo o archivo, y actualización de guías y spec `alerting-ui`. | Verificación en 1440 px y 390 px con backend, auditoría de accesibilidad y revisión del contenido sin afirmaciones de validación agronómica ni de preparación productiva. |
