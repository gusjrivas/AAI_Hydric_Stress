import {
  PRODUCER_TABS,
  PRODUCER_TAB_LABELS,
  type ProducerTab,
} from "./producerTabsConfig";

/** Pestañas internas del productor. No hay pestaña "Ajustes": este ensamble
 * no tiene una capacidad real de ajustar los próximos pronósticos a partir
 * de las observaciones (esa capacidad, ligada al flujo de un solo modelo,
 * sigue disponible en su propia ruta técnica -- "Ajustar próximos
 * pronósticos" -- sin exponerse acá como si aplicara al ensamble). */
export function ProducerTabs({
  active,
  onSelect,
}: {
  active: ProducerTab;
  onSelect: (tab: ProducerTab) => void;
}) {
  return (
    <nav className="producer-tabs" aria-label="Secciones de Mi cultivo">
      <ul className="producer-tabs-list">
        {PRODUCER_TABS.map((tab) => (
          <li key={tab}>
            <button
              type="button"
              className="producer-tab"
              aria-current={active === tab ? "page" : undefined}
              onClick={() => onSelect(tab)}
            >
              {PRODUCER_TAB_LABELS[tab]}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
