---
name: memoria-tecnica
description: Use when writing, drafting, or reviewing any section of the thesis memoria técnica (TTFA/LSE-UBA master's defense document) in this repo — structure, LaTeX formatting, wording, or chapter content questions.
---

# Memoria técnica (TTFA)

## Overview

Style and structure rules for the memoria técnica of this project's master's thesis (Taller de Preparación del Trabajo Final, LSE-UBA). Extracted from the Clase 1 guidelines. The LaTeX template lives at https://github.com/TTFA-TTFB/Plantilla-para-memoria — follow this skill for content/wording, that repo for the LaTeX skeleton itself.

**When reviewing or drafting a chapter, check every section below in order — most violations are invisible unless checked explicitly (bold text and gerunds read as "normal" prose).**

## Estructura obligatoria (5 capítulos)

| Cap. | Objetivo | Extensión | No puede faltar | Opcional | Evitar |
|---|---|---|---|---|---|
| 1. Introducción general | Estado del arte para alguien ajeno al tema; transmitir su importancia | 5 hojas | Estado del arte, contexto y motivación | Describir la empresa/cliente | Requerimientos |
| 2. Introducción específica | Herramientas/elementos de terceros usados en el cap. 3 | 5 hojas | Toda tecnología/framework mencionado en cap. 3 que no fue desarrollado por el autor | — | Requerimientos |
| 3. Diseño e implementación | Criterios de diseño y arquitectura construida | 15-20 hojas | Diagrama de bloques/arquitectura detallado, todos los componentes del trabajo | — | Bloques de código |
| 4. Ensayos y resultados | Cómo se hicieron los ensayos, resultados y su análisis | 10-15 hojas | Todas las pruebas (unitarias e integración), tablas y gráficos | Pruebas descartadas, validar requerimientos | Tablas con info innecesaria |
| 5. Conclusiones | Principales aportes y cómo continuar el trabajo | 2 hojas | Comparar planificado vs. logrado | Conocimientos aplicados | Tablas e imágenes |

Cada capítulo lleva un **resumen introductorio de 2-3 líneas sin título propio** antes de la primera sección.

## Resumen de la memoria (independiente de los capítulos)

- Uno o dos párrafos, sin negrita/itálica, sin siglas ni acrónimos, sin referencias ni notas al pie.
- Debe cubrir: qué se hizo/logró, qué importancia/valor tiene, si fue para una empresa/instituto (si aplica), qué conocimientos se aplicaron.

## Reglas de formato

- **Negrita y subrayado**: no usar en ningún párrafo.
- **Itálica**: solo para definir siglas originadas en otro idioma (ej. RTOS, *del inglés, Real Time Operating System*).
- **Escritura impersonal, en pasado, sobre un trabajo concluido**: "se implementó...", nunca "yo hice/diseñé...". La memoria narra algo terminado, no un plan futuro — no mezclar el registro de la planificación (futuro, "proyecto") con el de la memoria (pasado, "trabajo"). Frases guía: "En este capítulo se presenta...", "En la figura X se puede observar...".
- **Referencias bibliográficas**: inline con `[1]` dentro del párrafo (ej. "el diseño está basado en la EDU-CIAA [1]..."), nunca solo al final del capítulo.
- **Imágenes**: siempre referenciadas con nota al pie citando la fuente (o "Fuente: adaptado de [n]" si corresponde); texto legible; respetar márgenes; traducir el texto que contengan si está en otro idioma.
- **Tablas**: un único formato consistente en toda la memoria (ver plantilla).
- **Ecuaciones**: numeradas, formato de la plantilla.
- **Código**: no incluir. Si es excepcionalmente necesario, usar el formato de la plantilla y numerar las líneas correctamente. Preferir diagramas de flujo, estado o secuencia (PlantUML es la herramienta sugerida) en su lugar.
- **Todo listado, tabla o imagen debe tener una oración que lo introduzca/desarrolle antes de mostrarlo** — nunca aparece "pelado".

## Letra monoespaciada (`\texttt{}`, `\verb||`, `verbatim`)

Se usa **solo** para nombres literales de la implementación propia: variables, funciones, clases, archivos, carpetas, rutas, campos, tablas, claves, tópicos, endpoints, identificadores, módulos propios, configuraciones, columnas, etiquetas, parámetros, archivos de modelos.

**No** se usa para: tecnologías/lenguajes/sistemas operativos, herramientas y plataformas externas, sensores/microcontroladores/componentes, bibliotecas externas, protocolos, algoritmos/modelos/arquitecturas/métricas, conjuntos de datos externos. Estos van con tipografía normal, denominación oficial, y referencia bibliográfica cuando corresponda.

Ejemplo: `solar_db` (nombre propio de la base) va en monoespaciada; TensorFlow, MySQL, JSON, LoRaWAN, YOLO no.

## Unificación de criterio

Elegir un criterio y mantenerlo en toda la memoria:
- Cifras: todas en letras o todas en números (no mezclar).
- Epígrafes y enumeraciones: con o sin punto final, consistente.
- Pronombres y el adverbio "solo": con o sin tilde, consistente (RAE moderna: sin tilde).

## Errores típicos de IA (ChatGPT y similares) a evitar

- Conectores de cierre: "en resumen", "en conclusión", "en conjunto", "en síntesis", "en contraste"...
- Abuso del gerundio ("logrando", "acelerando", "permitiendo" encadenados).
- Referencias bibliográficas inventadas — toda referencia debe verificarse contra una fuente real.
- Guion largo (—) como separador de segundo nivel dentro de una oración — evitarlo, preferir puntuación normal o reestructurar la oración.
- Redacción en primera persona.

## Flujo de revisión (cómo se evalúa)

Un capítulo se aprueba pasando cuatro filtros en orden — cada uno bloquea si falla:
1. ¿Se usa correctamente el diccionario y el formato? (reglas de arriba)
2. ¿La redacción es coherente? (probar leyendo en voz alta)
3. ¿La distribución de los contenidos es correcta? (tabla de estructura)
4. ¿La explicación del contenido es correcta?

Al revisar un fragmento, aplicá estos cuatro filtros en ese orden y señalá en cuál falla primero.

## Quick reference al corregir

| Se ve así | Se corrige a |
|---|---|
| "el diseño lo hice de acuerdo a..." | "el diseño se realizó de acuerdo a..." |
| "en este proyecto se implementará" (memoria) | "en este trabajo se implementó" |
| `\texttt{TensorFlow}` | TensorFlow (tipografía normal + referencia) |
| tabla o figura sin oración previa | agregar oración que la introduzca antes de mostrarla |
| imagen sin nota al pie | agregar nota al pie con la fuente |
| bloque de código | reemplazar por diagrama de flujo/estado/secuencia, o pseudocódigo de la plantilla si es imprescindible |
| "En conclusión, ..." / "logrando un..." | reescribir sin conector de cierre ni gerundio encadenado |
