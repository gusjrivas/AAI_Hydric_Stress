import { useLayoutEffect, useRef, type ReactNode } from "react";
import "./AppHeader.css";
import type { NavGroup } from "./useHashRoute";

interface PrimaryItem {
  /** Secciones de navegación que dejan marcada esta entrada como activa. */
  groups: readonly NavGroup[];
  href: string;
  label: string;
  /** Etiqueta breve para la barra inferior de pantallas muy angostas (el nombre accesible es `label`). */
  shortLabel: string;
  icon: ReactNode;
}

const ICON_PROPS = { viewBox: "0 0 24 24", width: 22, height: 22, "aria-hidden": true, focusable: false } as const;

/**
 * Menú de presentación: tres entradas en el orden de la defensa (cómo está construido,
 * cómo se usa, qué se obtuvo). El resto de los destinos sigue disponible bajo «Más».
 */
const PRIMARY_ITEMS: PrimaryItem[] = [
  {
    groups: ["arquitectura"],
    href: "#arquitectura",
    label: "Arquitectura",
    shortLabel: "Arquitectura",
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M4 5h6v5H4zM14 5h6v5h-6zM9 14h6v5H9zM7 10v2h10v-2M12 12v2" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    groups: ["seguimiento", "laboratorio"],
    href: "#defensa-pergamino",
    label: "Caso de demostración",
    shortLabel: "Caso",
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M12 3C8.500 9 6 11.500 6 15a6 6 0 0 0 12 0c0-3.500-2.500-6-6-12z" fill="none" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    groups: ["evidencia"],
    href: "#evidencia-resultados",
    label: "Resultados",
    shortLabel: "Resultados",
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
  },
];

interface MoreItem {
  group: NavGroup;
  href: string;
  label: string;
}

/** Destinos que ya existían y que no forman parte del relato de la defensa. */
const MORE_ITEMS: MoreItem[] = [
  { group: "cultivo", href: "#productor", label: "Mi cultivo" },
  { group: "herramientas", href: "#resumen", label: "Herramientas técnicas" },
];

/**
 * Encabezado de marca y navegación principal. Un único `<nav>`: en pantallas
 * anchas son píldoras dentro del encabezado; en móvil el mismo elemento pasa a
 * ser una barra inferior fija (solo CSS), sin duplicar enlaces en el DOM.
 */
export function AppHeader({ activeGroup }: { activeGroup: NavGroup }) {
  const headerRef = useRef<HTMLElement>(null);
  // Publica la altura real del encabezado para elementos pegajosos debajo de él
  // (p. ej. la banda permanente «Simulación» del laboratorio).
  useLayoutEffect(() => {
    const publish = () => {
      document.documentElement.style.setProperty("--app-header-h", `${headerRef.current?.offsetHeight ?? 72}px`);
    };
    publish();
    window.addEventListener("resize", publish);
    return () => window.removeEventListener("resize", publish);
  }, []);
  const moreActive = MORE_ITEMS.some((item) => item.group === activeGroup);
  return (
    <header className="app-header" ref={headerRef}>
      <div className="app-header-inner">
        <a className="app-brand" href="#arquitectura" aria-label="Seguimiento del agua en el cultivo, ir a Arquitectura">
          <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true" focusable="false">
            <path d="M16 3C11 11 7 15 7 20a9 9 0 0 0 18 0c0-5-4-9-9-17z" fill="currentColor" />
          </svg>
          <span className="app-brand-text">
            <span className="app-brand-name">Seguimiento del agua</span>
            <span className="app-brand-sub">en el cultivo · apoyo a la decisión</span>
          </span>
        </a>
        <nav className="app-primary-nav" aria-label="Secciones principales">
          <ul>
            {PRIMARY_ITEMS.map((item) => (
              <li key={item.href}>
                <a href={item.href} aria-current={item.groups.includes(activeGroup) ? "page" : undefined}>
                  {item.icon}
                  <span className="nav-full">{item.label}</span>
                  <span className="nav-short" aria-hidden="true">{item.shortLabel}</span>
                </a>
              </li>
            ))}
            <li className="app-more">
              <details>
                <summary className={moreActive ? "is-current" : undefined}>
                  <svg {...ICON_PROPS}>
                    <path d="M5 12h.01M12 12h.01M19 12h.01" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                  <span>Más</span>
                </summary>
                <ul className="app-more-list">
                  {MORE_ITEMS.map((item) => (
                    <li key={item.href}>
                      <a href={item.href} aria-current={item.group === activeGroup ? "page" : undefined}>
                        {item.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </details>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
