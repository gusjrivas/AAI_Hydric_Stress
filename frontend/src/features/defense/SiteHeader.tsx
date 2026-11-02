export type DefenseSite = "pergamino" | "melchor";

const SITES: Record<DefenseSite, { route: string; name: string; period: string }> = {
  pergamino: {
    route: "defensa-pergamino",
    name: "Pergamino",
    period: "Pergamino · emisiones persistidas del 13 al 17 de junio de 2023.",
  },
  melchor: {
    route: "defensa-melchor-romero",
    name: "Melchor Romero",
    period: "Melchor Romero · emisiones persistidas del 20 al 24 de octubre de 2024.",
  },
};

/**
 * Encabezado común de las pantallas de seguimiento histórico. Pergamino y
 * Melchor Romero comparten estructura, no contenido: cada sitio conserva su
 * período. El carácter histórico y la fuente de los datos los declara la escena.
 */
export function SiteHeader({ site }: { site: DefenseSite }) {
  const info = SITES[site];
  return (
    <header className="site-header">
      <div className="site-header-row">
        <div className="site-header-title">
          <h1 id={`${info.route}-heading`} tabIndex={-1}>{info.name}</h1>
        </div>
      </div>
      <p className="site-period">{info.period}</p>
    </header>
  );
}
