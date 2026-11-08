/**
 * Catálogo del diagrama de despliegue: DISEÑO DOCUMENTADO de los componentes de
 * Docker Compose y sus conexiones. No descubre servicios en vivo ni refleja su
 * estado. Cada componente cita rutas del repositorio y los puertos que declara
 * `docker-compose.yml` (ambos verificados por `deploymentCatalog.test.ts`).
 */
export interface DeploymentComponent {
  id: string;
  label: string;
  /** Líneas de texto dentro de la caja del diagrama. */
  lines: readonly string[];
  /** Puertos tal como figuran en docker-compose.yml. */
  ports?: readonly string[];
  /** Fuera de Docker. */
  external?: boolean;
  /** Existe solo con un perfil opcional de Compose. */
  optional?: boolean;
  box: { x: number; y: number; w: number; h: number };
  responsibility: string;
  connections: string;
  evidence: readonly string[];
  limits: string;
}

export interface DeploymentEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  /** Trazado SVG. */
  d: string;
  labelAt?: { x: number; y: number };
  /** Petición y respuesta: punta de flecha en ambos extremos. */
  bidirectional?: boolean;
}

export interface TourStep {
  id: string;
  caption: string;
  nodes: readonly string[];
  edges: readonly string[];
}

export const DEPLOYMENT_COMPONENTS: readonly DeploymentComponent[] = [
  {
    id: "usuario",
    label: "Usuario",
    lines: ["navegador"],
    external: true,
    box: { x: 20, y: 62, w: 150, h: 62 },
    responsibility: "Quien opera la interfaz.",
    connections: "Solo habla con el frontend por HTTP; no accede a MLflow, MinIO ni a la base.",
    evidence: ["frontend/src/main.tsx"],
    limits: "El sistema es apoyo a la decisión; la persona decide.",
  },
  {
    id: "fuentes",
    label: "Fuentes de datos",
    lines: ["sensores IoT", "ERA5-Land · NASA POWER", "(fuera de Docker)"],
    external: true,
    box: { x: 20, y: 196, w: 170, h: 104 },
    responsibility: "Proveer lecturas de sensores y datos de reanálisis.",
    connections: "Entran por la ingesta del núcleo Python.",
    evidence: ["src/data_ingestion/storage.py", "src/data_ingestion/mock_sensor.py"],
    limits: "Los sensores son fuente de datos, no la contribución central del trabajo.",
  },
  {
    id: "frontend",
    label: "Frontend",
    lines: ["React · Vite"],
    ports: ["5173"],
    box: { x: 240, y: 58, w: 160, h: 72 },
    responsibility: "Interfaz de apoyo a la decisión.",
    connections: "Consume únicamente la API REST del backend (ADR-0003).",
    evidence: ["frontend/src/App.tsx", "docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md"],
    limits: "No contiene lógica de modelos ni reimplementa reglas del dominio.",
  },
  {
    id: "backend",
    label: "Backend",
    lines: ["FastAPI · API REST"],
    ports: ["8000"],
    box: { x: 470, y: 50, w: 190, h: 96 },
    responsibility: "Fachada delgada sobre el núcleo: pronóstico, calidad, feedback, recalibración, reproducción histórica y linaje.",
    connections: "Recibe del frontend, invoca al núcleo y en la aplicación base registra recalibraciones del predictor individual en MLflow (MLFLOW_TRACKING_URI).",
    evidence: ["backend/app/main.py", "backend/Dockerfile"],
    limits: "No es el operativo de riego: entrega avisos para revisión humana.",
  },
  {
    id: "demo",
    label: "demo-control",
    lines: ["perfil «demo» (opcional)"],
    ports: ["8010"],
    optional: true,
    box: { x: 740, y: 58, w: 190, h: 72 },
    responsibility: "Controlador local de la demo acelerada.",
    connections: "Depende del backend; solo existe con el perfil «demo» de Compose.",
    evidence: ["docker/demo-control/Dockerfile", "docs/adr/0012-controlador-local-demo-acelerada.md"],
    limits: "No reemplaza al backend operativo ni forma parte del flujo científico.",
  },
  {
    id: "modelos",
    label: "Modelos",
    lines: ["Regresión logística", "Random Forest", "Hist. Gradient Boosting", "ensamble · promedio"],
    box: { x: 240, y: 190, w: 170, h: 130 },
    responsibility: "Tres familias combinadas con la política ensemble_agreement_v1 (pesos uniformes 1/3).",
    connections: "Se cargan desde bundles que lee el núcleo.",
    evidence: ["src/predictive_modeling/ensemble_bundle.py"],
    limits: "La señal no es una probabilidad agronómicamente calibrada ni indica cuánto regar.",
  },
  {
    id: "nucleo",
    label: "Núcleo Python (src/)",
    lines: ["ingesta · calidad", "modelado predictivo", "retroalimentación humana", "reproducción histórica"],
    box: { x: 440, y: 190, w: 250, h: 130 },
    responsibility: "Lógica del dominio: data_ingestion, data_quality, predictive_modeling, human_feedback, historical_replay y architecture_integration.",
    connections: "Lo invoca el backend; lee y escribe en data/; usa los modelos y, en la aplicación base, registra recalibraciones del predictor individual en MLflow.",
    evidence: ["src/architecture_integration/pipeline.py", "src/human_feedback/model_registry.py"],
    limits: "El experiment_runner corre fuera de línea y no forma parte de este flujo.",
  },
  {
    id: "data",
    label: "data/",
    lines: ["volumen montado", "datasets (parquet)", "operational_bundles"],
    box: { x: 740, y: 190, w: 190, h: 130 },
    responsibility: "Datasets versionados y bundles operativos.",
    connections: "Se monta como volumen en el backend y en demo-control.",
    evidence: ["data", "docker-compose.yml"],
    limits: "Los artefactos de Pergamino no se distribuyen en un clon limpio.",
  },
  {
    id: "mlflow",
    label: "MLflow",
    lines: ["recalibraciones y linaje"],
    ports: ["5000"],
    box: { x: 470, y: 372, w: 190, h: 72 },
    responsibility: "Registra y permite recuperar versiones del predictor individual de la aplicación base, junto con los parámetros, métricas y referencias de linaje asociados a sus recalibraciones.",
    connections: "Guarda metadatos en PostgreSQL y sirve artefactos desde MinIO.",
    evidence: ["src/human_feedback/model_registry.py", "docker/mlflow/Dockerfile", "docs/adr/0004-orquestacion-experimentos-mlflow-minio.md"],
    limits: "El pronóstico del ensamble carga sus modelos desde paquetes locales. La aplicación base sí utiliza MLflow para recuperar versiones del predictor individual.",
  },
  {
    id: "postgres",
    label: "PostgreSQL 16",
    lines: ["backend store"],
    box: { x: 245, y: 468, w: 190, h: 62 },
    responsibility: "Backend store de MLflow: corridas, parámetros y métricas.",
    connections: "Solo lo usa MLflow; volumen persistente mlflow_postgres_data.",
    evidence: ["docker-compose.yml"],
    limits: "No almacena lecturas de sensores ni feedback de la aplicación.",
  },
  {
    id: "minio",
    label: "MinIO",
    lines: ["bucket «mlflow»"],
    ports: ["9000", "9001"],
    box: { x: 700, y: 468, w: 230, h: 62 },
    responsibility: "Almacenamiento S3 de artefactos de MLflow; el bucket lo crea el servicio minio-init.",
    connections: "Solo lo usa MLflow; la consola está en el puerto 9001.",
    evidence: ["docker-compose.yml"],
    limits: "No almacena datasets del dominio.",
  },
];

export const DEPLOYMENT_EDGES: readonly DeploymentEdge[] = [
  { id: "usuario-frontend", from: "usuario", to: "frontend", label: "HTTP", d: "M170,93 H240", labelAt: { x: 205, y: 84 }, bidirectional: true },
  { id: "frontend-backend", from: "frontend", to: "backend", label: "REST", d: "M400,94 H470", labelAt: { x: 435, y: 84 }, bidirectional: true },
  { id: "demo-backend", from: "demo", to: "backend", label: "control", d: "M740,94 H660", labelAt: { x: 700, y: 84 } },
  { id: "backend-nucleo", from: "backend", to: "nucleo", label: "invoca", d: "M565,146 V190", labelAt: { x: 595, y: 172 }, bidirectional: true },
  { id: "nucleo-modelos", from: "nucleo", to: "modelos", d: "M440,255 H410", bidirectional: true },
  { id: "nucleo-data", from: "nucleo", to: "data", label: "E/S", d: "M690,255 H740", labelAt: { x: 715, y: 246 }, bidirectional: true },
  { id: "fuentes-nucleo", from: "fuentes", to: "nucleo", label: "lecturas · reanálisis", d: "M105,300 V348 H500 V320", labelAt: { x: 300, y: 342 } },
  { id: "nucleo-mlflow", from: "nucleo", to: "mlflow", label: "recalibración", d: "M610,320 V372", labelAt: { x: 650, y: 352 } },
  { id: "mlflow-postgres", from: "mlflow", to: "postgres", label: "metadatos", d: "M500,444 L400,468", labelAt: { x: 420, y: 446 } },
  { id: "mlflow-minio", from: "mlflow", to: "minio", label: "artefactos s3", d: "M630,444 L740,468", labelAt: { x: 700, y: 446 } },
];

export const DEPLOYMENT_TOUR: readonly TourStep[] = [
  { id: "p1", caption: "1 · Llega una lectura del sensor (o un dato histórico) y entra por la ingesta del núcleo.", nodes: ["fuentes", "nucleo"], edges: ["fuentes-nucleo"] },
  { id: "p2", caption: "2 · Se evalúa la calidad del dato: observado, imputado o sin observación.", nodes: ["nucleo"], edges: [] },
  { id: "p3", caption: "3 · Se calculan las variables y se cargan los modelos del bundle.", nodes: ["nucleo", "modelos"], edges: ["nucleo-modelos"] },
  { id: "p4", caption: "4 · Tres familias (regresión logística, Random Forest y Hist Gradient Boosting) estiman si habrá baja humedad (por debajo del umbral); el ensamble por promedio (ensemble_agreement_v1) combina los resultados y conserva el acuerdo entre modelos como indicador.", nodes: ["modelos"], edges: [] },
  { id: "p5", caption: "5 · El backend entrega el pronóstico y el aviso a la interfaz por la API REST.", nodes: ["nucleo", "backend", "frontend"], edges: ["backend-nucleo", "frontend-backend"] },
  { id: "p6", caption: "6 · La interfaz muestra el aviso como apoyo a la decisión. No automatiza el riego.", nodes: ["frontend", "usuario"], edges: ["usuario-frontend"] },
  { id: "p7", caption: "7 · La persona revisa el pronóstico del ensamble. La revisión queda registrada, pero no modifica sus modelos ni ejecuta una recalibración.", nodes: ["usuario", "frontend", "backend", "nucleo"], edges: ["usuario-frontend", "frontend-backend", "backend-nucleo"] },
  { id: "p8", caption: "8 · Circuito distinto: en la aplicación base, una solicitud manual puede incorporar correcciones elegibles al reajuste de un predictor individual y registrar una nueva versión en MLflow.", nodes: ["nucleo", "mlflow"], edges: ["nucleo-mlflow"] },
  { id: "p9", caption: "9 · Para ese circuito de la aplicación base, MLflow conserva los metadatos en PostgreSQL y los artefactos en MinIO. Esta operación no actualiza los modelos del ensamble.", nodes: ["mlflow", "postgres", "minio"], edges: ["mlflow-postgres", "mlflow-minio"] },
];
