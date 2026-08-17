# Change: Add anomaly-detection capability

> **Estado: implementado.** Ver `openspec/specs/data-quality/spec.md` (spec vigente, con notas de verificación real) y `tasks.md` de este *change* (todas las tareas marcadas). Este documento queda como registro histórico de la propuesta original.

## Trazabilidad

- **Épica:** 2. Núcleo de IA.
- **Historia de usuario:** HU3 — Componente de calidad y robustez de datos (subconjunto: detección de anomalías, segundo de tres sub-proyectos en que se dividió HU3).
- **Fase de CRISP-DM:** Preparación de los datos / Modelado.
- **Configuración experimental afectada:** base+anomalías y completa (Épica 4) — este componente es uno de los que se activa/desactiva para comparar configuraciones.
- **Insumo de diseño:** [`openspec/specs/data-quality/spec.md`](../../specs/data-quality/spec.md) (reporte de calidad y rangos), [`docs/research/hu1-retroalimentacion-humana.md`](../../../docs/research/hu1-retroalimentacion-humana.md) y [`docs/research/hu1-variables-y-antecedentes.md`](../../../docs/research/hu1-variables-y-antecedentes.md) (antecedentes de detección de anomalías en sensores agrícolas).

## Why

El reporte de calidad de `data-quality-basics` detecta valores fuera de un rango físico/climático fijo, pero no detecta anomalías relativas al comportamiento propio de cada variable (ej. un valor dentro del rango físico plausible pero estadísticamente atípico para la serie). Los antecedentes relevados en HU1 (DeepQC, detección autosupervisada de sensores defectuosos) coinciden en que no hay etiquetas de anomalía disponibles de antemano en este dominio — el esquema de datos ya lo anticipó (vacancia identificada en `docs/research/hu1-variables-y-antecedentes.md`, sección 3), por lo que el método debe ser no supervisado.

## What Changes

- Se agrega la detección de anomalías al componente `data-quality`, como método no supervisado que no requiere etiquetas previas.
- **Método candidato seleccionado:** Isolation Forest (`scikit-learn`), consistente con la elección de scikit-learn para modelos base/candidatos de ADR-0002. Se descartan como método base (no como descarte definitivo) autoencoders y otros métodos de aprendizaje profundo mencionados en los antecedentes de HU1 (DeepQC, detección autosupervisada), por ser más complejos de lo que exige un método base y estar mejor justificados si el desempeño de Isolation Forest resulta insuficiente en HU4.
- Se implementa el método base: ajuste de un `IsolationForest` sobre las columnas numéricas del esquema y marcado de cada fila como anómala o no.
- Se evalúa el comportamiento del detector inyectando anomalías sintéticas conocidas sobre una copia del dataset real (no hay anomalías reales etiquetadas para medir contra ellas) y midiendo qué proporción de esas anomalías inyectadas el detector logra marcar.

## Impact

- **Specs afectadas:** `data-quality` (extiende el spec existente con un nuevo requirement).
- **Specs futuras que dependen de esta:** `predictive-modeling` (HU4) podrá excluir o marcar filas anómalas antes de entrenar; el *change* de generación de datos sintéticos (tercer sub-proyecto de HU3) es independiente de este.
- **Código afectado:** nuevo módulo `src/data_quality/anomaly_detection.py`, sin modificar los módulos ya existentes de `data_quality`.
- **Fuera de alcance de este change:** generación de datos sintéticos (tercer *change* de HU3); integración de la detección de anomalías con el mecanismo de retroalimentación humana (HU5, no iniciada).
