import { useEffect, useState, type KeyboardEvent } from "react";
import "./DeploymentDiagram.css";
import { DEPLOYMENT_COMPONENTS, DEPLOYMENT_EDGES, DEPLOYMENT_TOUR } from "./deploymentCatalog";
import type { DeploymentComponent } from "./deploymentCatalog";

const STEP_MS = 4200;
const LAST_STEP = DEPLOYMENT_TOUR.length - 1;
const IDLE_CAPTION =
  "Mostrá, paso a paso, cómo viaja un dato desde el sensor hasta el registro de una recalibración.";

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function portsText(component: DeploymentComponent): string {
  return (component.ports ?? []).map((port) => `:${port}`).join(" / ");
}

function kindText(component: DeploymentComponent): string {
  if (component.external) return "Externo a Docker";
  if (component.optional) return "Contenedor opcional";
  return "Contenedor";
}

function connectedTo(component: DeploymentComponent): string {
  const labelOf = (id: string) => DEPLOYMENT_COMPONENTS.find((c) => c.id === id)?.label ?? id;
  return DEPLOYMENT_EDGES.filter((edge) => edge.from === component.id || edge.to === component.id)
    .map((edge) => {
      const other = labelOf(edge.from === component.id ? edge.to : edge.from);
      return edge.label ? `${other} (${edge.label})` : other;
    })
    .join(", ");
}

/**
 * Diagrama de despliegue con recorrido ilustrativo. Es diseño documentado: el
 * recorrido resalta componentes y conexiones según un guion fijo; no consulta
 * servicios ni muestra datos, métricas o estados.
 */
export function DeploymentDiagram() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [step, setStep] = useState(-1);
  const [playing, setPlaying] = useState(false);

  // La reproducción termina sola al llegar al último paso: se deriva en el render.
  const isPlaying = playing && step < LAST_STEP;

  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => setStep((current) => Math.min(current + 1, LAST_STEP)), STEP_MS);
    return () => clearInterval(timer);
  }, [isPlaying]);

  const current = step >= 0 ? DEPLOYMENT_TOUR[step] : null;
  const selected = DEPLOYMENT_COMPONENTS.find((component) => component.id === selectedId) ?? null;

  function togglePlay() {
    if (isPlaying) {
      setPlaying(false);
      return;
    }
    if (step < 0 || step >= LAST_STEP) setStep(0);
    if (!prefersReducedMotion()) setPlaying(true);
  }

  function select(id: string) {
    setSelectedId(id);
  }

  function onKeyDown(event: KeyboardEvent<SVGGElement>, id: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      select(id);
    }
  }

  return (
    <section className="dd" aria-labelledby="dd-title">
      <h3 id="dd-title" className="dd-title">
        Componentes y conexiones
      </h3>

      <div className="dd-tour" role="group" aria-label="Recorrido ilustrativo del flujo">
        <button type="button" className="dd-primary" onClick={togglePlay}>
          {isPlaying ? "❚❚ Pausar" : "▶ Ver el recorrido"}
        </button>
        <button type="button" onClick={() => { setPlaying(false); setStep((s) => Math.max(0, s - 1)); }}>
          ‹ Anterior
        </button>
        <button type="button" onClick={() => { setPlaying(false); setStep((s) => Math.min(s + 1, LAST_STEP)); }}>
          Siguiente ›
        </button>
        <button type="button" onClick={() => { setPlaying(false); setStep(-1); }}>
          Salir
        </button>
        <span className="dd-flag">Recorrido ilustrativo · sin datos ni métricas reales</span>
      </div>
      <p className="dd-caption" data-testid="tour-caption" aria-live="polite">
        {current ? current.caption : IDLE_CAPTION}
      </p>

      <div className="dd-scroll" tabIndex={0} role="region" aria-label="Diagrama de despliegue, desplazable en pantallas angostas">
      <svg
        className={`dd-svg${current ? " dd-playing" : ""}`}
        viewBox="0 0 1000 560"
        role="img"
        aria-label="Diagrama de despliegue de la aplicación en Docker Compose"
      >
        <defs>
          <marker id="dd-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="14" markerHeight="14" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" className="dd-arrowhead" />
          </marker>
        </defs>
        <rect x="205" y="12" width="785" height="536" rx="14" className="dd-compose" />
        <text x="220" y="34" className="dd-enc">
          Docker Compose · aai-hydric-stress
        </text>

        {DEPLOYMENT_COMPONENTS.map((component) => {
          const { x, y, w, h } = component.box;
          const active = current?.nodes.includes(component.id) ?? false;
          const ports = portsText(component);
          const classes = ["dd-node"];
          if (component.external) classes.push("dd-ext");
          if (component.optional) classes.push("dd-opt");
          if (active) classes.push("dd-active");
          if (selectedId === component.id) classes.push("dd-selected");
          return (
            <g
              key={component.id}
              className={classes.join(" ")}
              role="button"
              tabIndex={0}
              aria-label={ports ? `${component.label}, puerto ${ports.replaceAll(":", "")}` : component.label}
              aria-current={active ? "step" : undefined}
              onClick={() => select(component.id)}
              onKeyDown={(event) => onKeyDown(event, component.id)}
            >
              <rect x={x} y={y} width={w} height={h} rx={10} />
              <text x={x + w / 2} y={y + 22} className="dd-t">
                {component.label}
              </text>
              {component.lines.map((line, index) => (
                <text key={line} x={x + w / 2} y={y + 42 + index * 16} className="dd-s">
                  {line}
                </text>
              ))}
              {ports && (
                <text x={x + w / 2} y={y + 42 + component.lines.length * 16} className="dd-p">
                  {ports}
                </text>
              )}
            </g>
          );
        })}

        <g className="dd-edges">
          {DEPLOYMENT_EDGES.map((edge) => {
            const active = current?.edges.includes(edge.id) ?? false;
            const classes = [edge.bidirectional ? "dd-bi" : "", active ? "dd-active" : ""].filter(Boolean).join(" ");
            return <path key={edge.id} d={edge.d} className={classes || undefined} />;
          })}
          {DEPLOYMENT_EDGES.filter((edge) => edge.label && edge.labelAt).map((edge) => (
            <text key={edge.id} x={edge.labelAt!.x} y={edge.labelAt!.y} className="dd-l">
              {edge.label}
            </text>
          ))}
        </g>
      </svg>
      </div>

      {selected ? (
        <section className="dd-sheet" aria-label={`Ficha de ${selected.label}`} aria-live="polite">
          <h4>{selected.label}</h4>
          <dl>
            <dt>Responsabilidad</dt>
            <dd>{selected.responsibility}</dd>
            <dt>Conexiones</dt>
            <dd>{selected.connections}</dd>
            <dt>Evidencia</dt>
            <dd>
              <ul>
                {selected.evidence.map((path) => (
                  <li key={path}>
                    <code>{path}</code>
                  </li>
                ))}
              </ul>
            </dd>
            <dt>Límites</dt>
            <dd>{selected.limits}</dd>
          </dl>
        </section>
      ) : (
        <p className="dd-hint">Elegí un componente del diagrama para ver su ficha.</p>
      )}

      <div className="dd-table-scroll" tabIndex={0} role="region" aria-label="Tabla de componentes, desplazable en pantallas angostas">
      <table className="dd-table">
        <caption>Componentes y conexiones del despliegue (alternativa textual del diagrama)</caption>
        <thead>
          <tr>
            <th scope="col">Componente</th>
            <th scope="col">Tipo</th>
            <th scope="col">Puertos</th>
            <th scope="col">Se conecta con</th>
          </tr>
        </thead>
        <tbody>
          {DEPLOYMENT_COMPONENTS.map((component) => (
            <tr key={component.id}>
              <th scope="row">{component.label}</th>
              <td>{kindText(component)}</td>
              <td>{portsText(component) || "—"}</td>
              <td>{connectedTo(component)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </section>
  );
}
