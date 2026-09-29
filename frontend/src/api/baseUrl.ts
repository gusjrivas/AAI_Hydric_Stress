// URL base de la API del backend (fachada FastAPI, ADR-0003). Configurable
// vía `VITE_API_BASE_URL` (ver `frontend/.env.example`); `http://localhost:8000`
// es el valor por defecto de desarrollo, no un valor productivo.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// URL base específica de la fachada `producer_v2` (Pergamino/Melchor Romero).
// Necesaria porque `scripts/start_defense_demo.ps1 -Mode all` arranca DOS
// backends distintos (laboratorio + productor) en puertos distintos: sin
// esta variable separada, los clientes de `producer/` terminaban enviando
// sus solicitudes al mismo backend que el laboratorio (`API_BASE_URL`),
// aunque el productor corriera en otro puerto. Configurable vía
// `VITE_PRODUCER_API_BASE_URL` (ver `frontend/.env.example`); si no está
// definida, cae en `API_BASE_URL` para preservar el comportamiento previo
// a esta variable (un solo backend, como en desarrollo normal).
export const PRODUCER_API_BASE_URL = import.meta.env.VITE_PRODUCER_API_BASE_URL ?? API_BASE_URL;
