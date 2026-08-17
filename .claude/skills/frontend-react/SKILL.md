---
name: frontend-react
description: Use when implementing or reviewing code in frontend/ (React) in this repo — covers the monorepo location, the API-only consumption boundary from ADR-0003, and baseline React conventions for a project with no frontend code yet.
---

# Frontend React en este repo

## Estructura (ADR-0003)

- El código vive en `frontend/`, dentro del mismo monorepo (no un repositorio separado).
- El frontend **consume la API del backend por HTTP, y nada más**: no llama directamente a `src/` de Python, no lee `data/` ni habla con MLflow/MinIO/Postgres. Si un componente necesita un dato que el backend no expone todavía, el fix es agregar el endpoint al backend, no saltear la fachada.
- No existe todavía ningún código de `frontend/` en el repo (se crea recién con HU5, ver ADR-0003 "Consecuencias"). No anticipes el scaffolding antes de que una HU lo pida — esta skill guía esa primera implementación cuando llegue el momento.

## Convenciones base (estándares razonables, no decisiones formales de ADR)

Como todavía no hay código propio del que derivar convenciones, se parte de prácticas estándar de React hasta que el propio código del proyecto justifique desviarse:

- Componentes funcionales con hooks; nada de componentes de clase.
- Estado con los hooks nativos (`useState`, `useReducer`, `useContext`) hasta que la complejidad real justifique una librería de estado — no agregar Redux/Zustand/etc. de entrada.
- Organización por *feature* (una carpeta por capacidad: alertas, retroalimentación, etc.), no por tipo de archivo (`components/`, `hooks/` a secas) — evita que crecer la app implique reordenar todo.
- Testing con React Testing Library (+ Vitest o Jest), probando comportamiento visible al usuario, no detalles de implementación internos del componente.

## Cuándo revisar/actualizar esta skill

Cuando exista código real de `frontend/`, esta skill debe actualizarse para reflejar los patrones que el propio proyecto adopte (no quedarse en genérico indefinidamente) — mismo criterio que ya se aplicó al resto de la documentación de este repo: preferir evidencia real por sobre recomendaciones genéricas apenas exista.
