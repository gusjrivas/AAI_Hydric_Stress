# Plan de rediseño profesional de la interfaz

## 1. Objetivo y base

Presentar una propuesta visual única, navegable y coherente de la interfaz, basada
en las capacidades reales del repositorio.

> **Estado vigente de la rama (2026-10-03).** La etapa 1 (prototipo) fue solo de diseño y prototipado y no integraba nada en
> las pantallas operativas; esa descripción es **histórica** y rige las secciones 2 a 7. Después se integró el diseño en
> `frontend/` (etapa 2, sección 8), se reorganizó sobre el backend de `main` (sección 9), se cerró la accesibilidad y la
> documentación (etapa 3, sección 10) y se hizo una ronda final de auditoría (sección 11). La estructura de navegación
> vigente es la de la sección 9 (cinco secciones). El PR #231 está abierto, sin merge.

- Rama: `design/ui-professional-prototype`
- Worktree: `C:\Repo\AAI_Hydric_Stress_ui_design`
- SHA base (`origin/main`): `b56b97a267045147648c507d68e3ce976f20d946`
- Trazabilidad: HU6 (integración/UI), capacidad OpenSpec `alerting-ui`; fase CRISP-DM
  de despliegue/comunicación. Sin impacto sobre configuración experimental,
  hipótesis, alcance ni arquitectura. Sin impacto sobre HU7/HU8.

## 2. Alcance del prototipo (etapa 1, histórico)

Ubicación: `design/prototypes/ui-professional/` (HTML, CSS y JS sin dependencias ni
recursos remotos). No toca `frontend/`, el backend ni los artefactos de evidencia.

| Vista | Contenido |
| --- | --- |
| A. Pergamino | Procedencia y período, selección de emisión, reloj histórico, horizontes +1/+2/+3, acuerdo entre modelos, observaciones posteriores, gráfico de humedad, calidad de datos, revisión humana simulada, acceso a evidencia. |
| B. Melchor Romero | Mismo sistema visual con procedencia y período propios, observado/imputado diferenciados y ausencia explícita de evaluación agregada equivalente. |
| C. Laboratorio | Recorrido guiado A–D (normal, anomalía, interrupción, recuperación), sesión, estado, siguiente acción, resultado del paso, línea de tiempo y banda permanente «Simulación · Datos sintéticos · Sin sensor físico». |
| D. Evidencia | Cinco niveles: resumen, comparación por horizonte y métrica, soporte y tabla, detalle técnico, metodología y limitaciones. Pestañas: Pergamino 2023, experimento controlado v3 y Melchor Romero (sin evaluación). |
| Herramientas técnicas | Acceso secundario a las capacidades existentes y catálogo de los diez estados requeridos. |

## 3. Decisiones principales (etapa 1; la estructura vigente está en la sección 9)

- **Estructura (etapa 1)**: cuatro entradas estables (Seguimiento histórico, Laboratorio, Evidencia,
  Herramientas técnicas; desde la sección 9 son cinco, con Mi cultivo). Pergamino y Melchor Romero son una conmutación dentro de
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

## 6. Verificaciones y limitaciones de la etapa 1 (histórico)

Lo que sigue describe el estado de esa etapa. Varias limitaciones se resolvieron después (backend real en Docker, laboratorio y
flujo móvil contra Docker): ver las secciones 8 a 11.

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
| 1. Propuesta visual (hecha) | Prototipo aislado de las cuatro vistas y herramientas. | Se abre con un comando, se recorre completo, se ve en móvil y se aprueba visualmente. Sin cambios en la app operativa. |
| 2. Integración | Portar tokens y componentes compartidos al `frontend/`; reemplazar las pantallas Pergamino, Melchor, Laboratorio y Evidencia usando los contratos reales; mover las capacidades existentes a Herramientas técnicas. | Sin cambio de contratos ni de rutas funcionales no acordadas; tests del frontend y verificación visual con backend real; estados y reglas científicas intactos. |
| 3. Cierre | Revisión con datos reales, accesibilidad completa, retiro del prototipo o archivo, y actualización de guías y spec `alerting-ui`. | Verificación en 1440 px y 390 px con backend, auditoría de accesibilidad y revisión del contenido sin afirmaciones de validación agronómica ni de preparación productiva. |

## 8. Estado de la etapa 2 (integración)

Rama `design/ui-professional-prototype`; el prototipo de `design/prototypes/ui-professional/` se conserva hasta el cierre (etapa 3).

**Qué se integró en `frontend/`** (sin cambiar contratos, rutas funcionales ni política del backend):

- Tokens únicos de la paleta azul sobre blanco en `index.css`; se eliminaron las paletas locales por pantalla y los verdes.
- Navegación en secciones estables (`AppHeader`, barra inferior en móvil; cuatro en este momento, cinco desde la sección 9). Todas las rutas y anclas existentes
  siguen vigentes; se agregó `#evidencia-resultados`. Las capacidades anteriores quedan en «Herramientas técnicas».
- Seguimiento histórico: `SiteHeader` compartido, franja de contexto, reloj con pasos, gráfico de humedad
  (`HistoricalMoistureChart`) con datos del contrato (imputado, sin dato y no verificado diferenciados; sin valores
  posteriores al reloj; umbral del backend), tarjetas con señal por forma y color, y revisión sin cambios de lógica.
- Evidencia por niveles (`EvidenceResultsPage`): Pergamino 2023, experimento v3 y Melchor Romero (sin evaluación),
  con el estado de gobernanza siempre visible. El texto completo de Melchor queda en un detalle accesible.
- Laboratorio: banda permanente de simulación, «Siguiente acción» y recorrido A–D como tarjetas.

**Verificado contra el backend real en Docker** (proyecto aislado `aai-defense-rehearsal`: `lab-backend` y
`producer-backend`, imagen de hace 3 días): Pergamino y Melchor Romero con sus emisiones persistidas, el umbral del
backend (Pergamino 31,3 %; Melchor Romero 32,2 %) y la imputación real del 26 de octubre. Capturas en
`docs/design/ui-professional-integration-captures/`. Pruebas del frontend, `tsc` y build en verde; el lint solo muestra
advertencias que ya existían (`ProducerTabs`, `HistoricalReplayPage`).

**Diferencias respecto del prototipo (por los datos reales):**

- Melchor Romero muestra su umbral y sus pronósticos reales del backend; el prototipo usaba ejemplos rotulados.
- La serie de Pergamino es la del backend; ya no hay serie ilustrativa.
- El laboratorio no muestra gráfico de humedad: su pantalla no consume lecturas del sensor de prueba; se agregaría con
  un contrato de lectura nuevo, fuera del alcance de esta etapa.

**Pendientes que tenía esta etapa** (resueltos o actualizados después): los pasos del laboratorio contra el backend, que
se ejecutaron en la ronda final (sección 11); la navegación por teclado y los lectores de pantalla, que se revisaron en
parte en la etapa 3 y siguen sin lector de pantalla (secciones 10 y 11).

## 9. Reorganización sobre el backend de `main` (tag `memoria-base-2026-09-29`)

El backend expone tres familias: `/api/v2` (productor: sectores, sensores, lecturas, pronósticos, revisiones e
históricos), el pipeline plano (pronóstico, feedback, recalibración, calidad, linaje, modelo activo) y `/replay`. La
primera versión del rediseño cubría el histórico de `/api/v2`, el laboratorio (pipeline plano) y la evidencia, pero el flujo
en vivo de `/api/v2` solo había cambiado de colores. Cambios:

- **Cinco secciones** en la navegación principal: Seguimiento histórico, **Mi cultivo**, Laboratorio, Evidencia y
  Herramientas técnicas (barra inferior de cinco entradas en móvil).
- **Mi cultivo** rediseñado sobre `/api/v2`: encabezado de página, selector de sector y punto de medición en tarjeta,
  pestañas Pronóstico, Historial y Datos, y la franja de contexto compartida (`FactsStrip`) con procedencia, fecha de
  emisión, fechas de aplicación y antigüedad de los datos. La franja aparece solo después de una consulta explícita:
  entrar a la pantalla, cambiar de pestaña o de sensor nunca emite un pronóstico.
- **Herramientas técnicas** queda con el pipeline plano: «Resumen e historial» (una entrada con selector interno; las
  anclas `#resumen` y `#prediccion` siguen válidas), Datos disponibles, Ajustar próximos pronósticos y Acerca de esta
  herramienta, más la reproducción histórica. «Ajustar próximos pronósticos» sigue sin exponerse en Mi cultivo porque
  el ensamble no tiene esa capacidad.
- Se definieron cuatro variables de color que Mi cultivo usaba y que habían quedado sin valor al eliminar las paletas
  locales.

Verificado: 272/272 pruebas del frontend (más una nueva), `tsc` y lint sin advertencias nuevas; a 390 px, sin
desbordamiento, contraste de texto ≥ 7,35:1 y controles ≥ 44 px en Mi cultivo y en las herramientas. Mi cultivo se revisó
en el navegador contra el backend productor de Docker (sensores `pergamino-ensemble-demo` y `melchor-romero-demo`).
Además se probó el flujo en vivo: con respaldo previo del directorio de datos del ensayo (huellas SHA-256), se emitió un
pronóstico para `pergamino-ensemble-demo` desde Mi cultivo y la franja de contexto mostró la procedencia, la emisión del
17 de junio de 2023 y la antigüedad real de los datos (captura `escritorio-7`). La emisión modificó el JSON de metadatos del
sensor y creó un archivo de bloqueo; se restauró el directorio completo desde el respaldo y se verificó que quedó
idéntico al estado previo (huellas iguales) antes de reiniciar el backend productor.

## 10. Cierre (etapa 3)

- **Accesibilidad.** Barrido por script del DOM real en las 10 rutas: un `<h1>` por pantalla, sin saltos de nivel, ids únicos,
  referencias `aria-*` válidas, campos con etiqueta, foco al navegar hacia `#<ruta>-heading` en todas las pantallas. Se
  corrigieron los saltos h1→h3 del seguimiento histórico, Mi cultivo y Evidencia; el foco que no tenía destino en
  seguimiento y laboratorio; y las pestañas de Evidencia, que ahora siguen el patrón ARIA (tabindex móvil, flechas,
  Inicio y Fin). 277/277 pruebas.
- **Documentación.** `docs/design/alerting-ui-visual-design.md` (tokens, navegación y contrastes vigentes, con la versión
  anterior como antecedente), `openspec/specs/alerting-ui/spec.md` (notas de implementación de navegación y
  accesibilidad) y `docs/seguimiento-tareas.md` (trazabilidad HU6 / `alerting-ui` / CRISP-DM).
- **Pendientes al cierre de la etapa 3** (actualizados en la sección 11): lector de pantalla; contraste de las etiquetas SVG
  por script; pasos del laboratorio contra Docker (hechos después). El prototipo `design/prototypes/ui-professional/` se
  conserva como referencia. La publicación se hizo después: rama subida y PR #231 abierto, sin merge.

## 11. Ronda final de auditoría (estado vigente)

Alcance: solo frontend, textos, navegación, accesibilidad, responsive y documentación. Sin cambios de hipótesis, alcance,
arquitectura, modelos, bundles, datasets, evidencia, política del ensamble, umbral, contratos ni backend.

**Hallazgos corregidos**

1. *Semántica de «sin alerta».* `alert=false` se informa como «Sin alerta prevista…», con la aclaración de que no garantiza
   buenas condiciones del cultivo; «Alerta prevista: posible falta de agua…» para `alert=true`. Prueba exhaustiva sobre las
   combinaciones de días y antigüedad de datos (`producerOutlook.test.ts`).
2. *Pronóstico desactualizado.* Un único aviso jerarquizado (titular «Este pronóstico no es actual»); el aviso secundario
   solo aparece si el tono no es ya «desactualizado».
3. *Foco y título en `#demo` y `#reproduccion-historica`.* Ambas se resuelven como la ruta «resumen»; el foco y el título
   dependen ahora de la vista abierta. Pruebas: Resumen→Replay, Replay→Demo, Demo→Resumen, Atrás/Adelante y sin re-foco.
4. *Barra móvil.* Medida a 390 y 360 px: las etiquetas caben sin acortarse, por lo que no se cambiaron. Se corrigió el
   relleno inferior con `safe-area`.
5. *Documentación.* Se separaron la historia (etapa 1), la integración y el estado vigente; se corrigió el comentario de
   «cuatro secciones».

**Mejoras adicionales:** gráfico histórico con lo observado después de la emisión como anillo (no existía al emitir); nota
del límite del laboratorio visible arriba; campos de formulario de 44 px; texto de «Cómo leer esta pantalla» en palabras
simples; recorrido técnico del historial como detalle avanzado.

**Verificaciones:** backend real en Docker (proyecto `aai-defense-rehearsal`): flujo móvil en iframes de 390 y 360 px y
laboratorio A→B→C→D. Pruebas automatizadas: 309/309, `tsc`, build y lint (solo advertencias previas).

**Pendientes reales (no resueltos):** revisión con lector de pantalla; contraste de etiquetas SVG por script; barrido a 360 px
con dos rutas sin resultado; prueba con un productor real.

**Backend:** sin cambios.
