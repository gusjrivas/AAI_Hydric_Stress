---
name: tdd-project-conventions
description: Use when writing or reviewing tests for Python modules in src/data_ingestion or src/data_quality in this repo — complements superpowers:test-driven-development with this project's specific fixture and verification conventions.
---

# Convenciones de TDD en este repo

**REQUIRED BACKGROUND:** superpowers:test-driven-development (RED-GREEN-REFACTOR genérico). Esta skill agrega lo específico de este proyecto, no lo reemplaza.

## Fixtures: usar el esquema real, no dicts sueltos

Construí los DataFrames de test con `data_ingestion.schema.normalize_to_schema(...)`, no con un DataFrame armado a mano sin pasar por el esquema:

```python
df = normalize_to_schema(
    pd.DataFrame({"timestamp": pd.to_datetime([...]), "temperature": [...]}),
    provenance="real",
)
```

Esto ejercita la lógica real de columnas obligatorias/opcionales y el flag de procedencia en cada test, en vez de asumir una forma de datos que el código de producción nunca ve así.

## Mockear solo la capa de red, nunca la lógica de parseo

Para conectores que llaman a una API externa (ver `tests/test_nasa_power.py`, `tests/test_esa_cci_soil_moisture.py`): construí una clase `_FakeSession`/`_FakeResponse` mínima que implementa solo los métodos que el conector usa (`.get(url, timeout)`, `.content`, `.status_code`), y dejá que el resto del código (parseo de JSON, parseo de NetCDF con xarray, normalización al esquema) corra de verdad. Nunca mockees la función que estás probando ni la librería de parseo — si mockeás `xarray.open_dataset`, el test no prueba nada del código real.

## El gate final: verificar contra el dataset real, no solo con sintéticos

Los tests unitarios con datos sintéticos prueban que el código funciona en principio. **Antes de marcar una tarea como ✅ en `docs/seguimiento-tareas.md` o de abrir el PR**, corré el módulo también contra el dataset real consolidado (`data/melchor_romero_2024_consolidado.parquet` u otro dataset real disponible) y reportá números concretos (cuántas filas, qué porcentaje, qué valores) en el commit/PR — no alcanza con "los tests pasan".

Esto ya sacó bugs reales que el sintético no hubiera mostrado: el bloqueo de SMN/AGRIS, el píxel de ESA CCI enmascarado por agua en La Plata, y dos fallas de red transitorias (500, `ConnectionError`) en la descarga completa de ESA CCI. Ningún test sintético los hubiera encontrado.

## Regla de graduación en `docs/seguimiento-tareas.md`

No marques una tarea ✅ basándote solo en que los tests con datos sintéticos pasan. Usá 🟡 si el mecanismo existe y está testeado pero no se corrió (o no se corrió con éxito) sobre datos reales; ✅ solo cuando hay evidencia concreta de una ejecución real citada en la fila de la tabla.
