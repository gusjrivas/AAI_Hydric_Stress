// URL base del controlador local opcional de demostración acelerada
// (HU6, ADR-0012). A diferencia de `API_BASE_URL`, no tiene valor por
// defecto: si `VITE_DEMO_CONTROL_BASE_URL` no está configurada, la
// funcionalidad de demostración queda deshabilitada y la aplicación
// normal sigue funcionando sin el controlador.
export const DEMO_CONTROL_BASE_URL: string | null =
  import.meta.env.VITE_DEMO_CONTROL_BASE_URL ?? null;
