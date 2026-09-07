// URL base de la API del backend (fachada FastAPI, ADR-0003). Configurable
// vía `VITE_API_BASE_URL` (ver `frontend/.env.example`); `http://localhost:8000`
// es el valor por defecto de desarrollo, no un valor productivo.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
