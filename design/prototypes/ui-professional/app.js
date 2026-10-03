/* Prototipo de diseño — vistas e interacciones locales.
   No hace solicitudes de red, no usa almacenamiento persistente y no escribe feedback real. */
(function () {
  "use strict";
  var D = window.PROTO_DATA, E = window.EVIDENCE_2023;
  var main = document.getElementById("contenido");
  var live = document.getElementById("live");

  /* ---------- utilidades ---------- */
  var MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  var MONTHS_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function parts(iso) { return iso.split("-").map(Number); }
  function fd(iso) { var p = parts(iso); return p[2] + " " + MONTHS[p[1] - 1]; }
  function fdy(iso) { var p = parts(iso); return p[2] + " " + MONTHS[p[1] - 1] + " " + p[0]; }
  function fdl(iso) { var p = parts(iso); return p[2] + " de " + MONTHS_L[p[1] - 1] + " de " + p[0]; }
  function addDays(iso, n) {
    var p = parts(iso), t = new Date(Date.UTC(p[0], p[1] - 1, p[2] + n));
    return t.getUTCFullYear() + "-" + String(t.getUTCMonth() + 1).padStart(2, "0") + "-" + String(t.getUTCDate()).padStart(2, "0");
  }
  function num(x, d) { return x == null ? "—" : Number(x).toFixed(d == null ? 3 : d).replace(".", ","); }
  function say(msg) { live.textContent = ""; setTimeout(function () { live.textContent = msg; }, 30); }

  var ICON = {
    alert: '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M10 2.5 18.5 17h-17z" fill="currentColor"/><path d="M10 8v4.2M10 14.2v.6" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>',
    calm: '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="2.2"/></svg>',
    na: '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><circle cx="10" cy="10" r="7" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 2.4"/><path d="M5.5 14.5l9-9" stroke="currentColor" stroke-width="2"/></svg>',
    lock: '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><rect x="4.5" y="9" width="11" height="8" rx="1.5" fill="currentColor"/><path d="M7 9V6.5a3 3 0 016 0V9" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    info: '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><circle cx="10" cy="10" r="8" fill="currentColor"/><path d="M10 9v5M10 6v.8" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>',
    check: '<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    pencil: '<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true"><path d="M3 17l1-4 9-9 3 3-9 9z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
    obs: '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="currentColor"/></svg>',
    imp: '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M8 2l6 6-6 6-6-6z" fill="#fff3d1" stroke="currentColor" stroke-width="2"/></svg>',
    miss: '<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    drop: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 3C8.5 9 6 11.5 6 15a6 6 0 0012 0c0-3.5-2.500-6-6-12z" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    flask: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M9 3h6M10 3v6l-5 9a2 2 0 002 3h10a2 2 0 002-3l-5-9V3" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
    chart: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    tools: '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M14.500 6.500a4 4 0 005 5L10 21a2.100 2.100 0 01-3-3zM8 8L5 5 3 7l3 3" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>'
  };

  function chip(kind, icon, text) { return '<span class="chip chip--' + kind + '">' + (icon ? ICON[icon] : "") + esc(text) + "</span>"; }

  /* ---------- estado ---------- */
  var S = {
    site: {
      pergamino: { emission: "2023-06-13", clock: "2023-06-13", demo: "real" },
      melchor: { emission: "2024-10-20", clock: "2024-10-20", demo: "real" }
    },
    reviews: {}, form: null,
    lab: { step: 0, busy: false, error: false, simErr: false },
    ev: { tab: "perg", hz: "1", metric: "mcc" },
    cat: { retry: "error", saved: false }
  };

  /* ---------- navegación ---------- */
  var ROUTES = [
    { id: "pergamino", group: "seguimiento" }, { id: "melchor", group: "seguimiento" },
    { id: "laboratorio", group: "laboratorio" }, { id: "evidencia", group: "evidencia" },
    { id: "herramientas", group: "herramientas" }
  ];
  var NAV = [
    { group: "seguimiento", href: "#/pergamino", label: "Seguimiento histórico", short: "Seguimiento", icon: "drop" },
    { group: "laboratorio", href: "#/laboratorio", label: "Laboratorio", short: "Laboratorio", icon: "flask" },
    { group: "evidencia", href: "#/evidencia", label: "Evidencia", short: "Evidencia", icon: "chart" },
    { group: "herramientas", href: "#/herramientas", label: "Herramientas técnicas", short: "Herramientas", icon: "tools", secondary: true }
  ];
  var TITLES = { pergamino: "Pergamino", melchor: "Melchor Romero", laboratorio: "Laboratorio", evidencia: "Evidencia", herramientas: "Herramientas técnicas" };
  function currentRoute() {
    var id = (location.hash.replace(/^#\/?/, "") || "pergamino");
    return ROUTES.some(function (r) { return r.id === id; }) ? id : "pergamino";
  }
  function renderNav(route) {
    var g = ROUTES.filter(function (r) { return r.id === route; })[0].group;
    var top = NAV.map(function (n) {
      return '<a href="' + n.href + '"' + (n.group === g ? ' aria-current="page"' : "") + (n.secondary ? ' class="is-secondary"' : "") + ">" + n.label + "</a>";
    }).join("");
    document.getElementById("main-nav").innerHTML = top;
    document.getElementById("tab-bar").innerHTML = NAV.map(function (n) {
      return '<a href="' + n.href + '"' + (n.group === g ? ' aria-current="page"' : "") + ">" + ICON[n.icon] + "<span>" + n.short + "</span></a>";
    }).join("");
  }

  /* ---------- gráfico de humedad ---------- */
  var CHARTS = {};
  function chartSvg(cfg, w) {
    w = Math.max(300, w);
    var h = w < 520 ? 280 : 330, m = { l: 54, r: 12, t: 30, b: w < 520 ? 64 : 58 };
    var pw = w - m.l - m.r, ph = h - m.t - m.b, N = cfg.points.length, bw = pw / N;
    var y0 = cfg.yDomain[0], y1 = cfg.yDomain[1];
    function X(i) { return m.l + bw * (i + 0.5); }
    function Y(v) { return m.t + ph * (1 - (v - y0) / (y1 - y0)); }
    var o = [];
    o.push('<svg viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="' + esc(cfg.aria) + '" focusable="false"><title>' + esc(cfg.aria) + "</title>");
    o.push('<defs><pattern id="hatch-' + cfg.id + '" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="2"/></pattern>' +
      '<pattern id="fut-' + cfg.id + '" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#f4f7fb"/><path d="M0 8L8 0" stroke="#dbe3ee" stroke-width="1.5"/></pattern></defs>');
    // grilla y etiquetas
    for (var v = y0; v <= y1 + 1e-9; v += cfg.yStep) {
      o.push('<line x1="' + m.l + '" x2="' + (w - m.r) + '" y1="' + Y(v) + '" y2="' + Y(v) + '" stroke="#e2e8f0"/>');
      o.push('<text x="' + (m.l - 8) + '" y="' + (Y(v) + 4) + '" text-anchor="end" font-size="12" fill="#2f3d52">' + num(v, 2) + "</text>");
    }
    o.push('<text x="14" y="' + (m.t + ph / 2) + '" transform="rotate(-90 14 ' + (m.t + ph / 2) + ')" text-anchor="middle" font-size="12" fill="#2f3d52">' + esc(cfg.unit) + "</text>");
    // no revelado
    var ci = cfg.clockIndex;
    if (ci != null && ci < N - 1) {
      var fx = X(ci) + bw / 2;
      o.push('<rect x="' + fx + '" y="' + m.t + '" width="' + (w - m.r - fx) + '" height="' + ph + '" fill="url(#fut-' + cfg.id + ')"/>');
      if (w - m.r - fx > 96) o.push('<text x="' + (fx + 8) + '" y="' + (m.t + ph - 8) + '" font-size="12" fill="#2f3d52" font-style="italic">Aún no revelado</text>');
    } else if (ci == null) {
      o.push('<rect x="' + m.l + '" y="' + m.t + '" width="' + pw + '" height="' + ph + '" fill="url(#fut-' + cfg.id + ')"/>');
    }
    // banda
    if (cfg.band) {
      var bx = X(cfg.band.from) - bw / 2, bwid = (cfg.band.to - cfg.band.from + 1) * bw;
      o.push('<rect x="' + bx + '" y="' + m.t + '" width="' + bwid + '" height="' + ph + '" fill="#d9f2f8" opacity=".85"/>');
      o.push('<text x="' + (bx + bwid / 2) + '" y="' + (m.t + 14) + '" text-anchor="middle" font-size="12" font-weight="700" fill="#005669">' + esc(cfg.band.label) + "</text>");
    }
    // faltantes (columna con trama)
    cfg.points.forEach(function (p, i) {
      if (p.status === "miss" && (ci == null || i <= ci)) {
        o.push('<rect x="' + (X(i) - bw / 2 + 1) + '" y="' + m.t + '" width="' + (bw - 2) + '" height="' + ph + '" fill="url(#hatch-' + cfg.id + ')" opacity=".35"/>');
      }
    });
    // umbral
    if (cfg.threshold != null) {
      var ty = Y(cfg.threshold);
      o.push('<line x1="' + m.l + '" x2="' + (w - m.r) + '" y1="' + ty + '" y2="' + ty + '" stroke="#0a1430" stroke-width="1.6" stroke-dasharray="7 5"/>');
      o.push('<text x="' + (m.l + 6) + '" y="' + (ty - 6) + '" font-size="12" font-weight="700" fill="#0a1430">Umbral ' + num(cfg.threshold, 3) + " m³/m³</text>");
    }
    // emisión
    if (cfg.emissionIndex != null) {
      var ex = X(cfg.emissionIndex);
      o.push('<line x1="' + ex + '" x2="' + ex + '" y1="' + (m.t - 4) + '" y2="' + (m.t + ph) + '" stroke="#081a3d" stroke-width="2"/>');
      o.push('<text x="' + ex + '" y="' + (m.t - 10) + '" text-anchor="' + (ex < m.l + 60 ? "start" : "middle") + '" font-size="12" font-weight="700" fill="#081a3d">Emisión ' + esc(fd(cfg.points[cfg.emissionIndex].date)) + "</text>");
    }
    // reloj
    if (ci != null) {
      var cx = X(ci);
      o.push('<line x1="' + cx + '" x2="' + cx + '" y1="' + m.t + '" y2="' + (m.t + ph + 6) + '" stroke="#0a1430" stroke-width="1.5" stroke-dasharray="2 3"/>');
      o.push('<path d="M' + (cx - 6) + " " + (m.t + ph + 14) + "L" + (cx + 6) + " " + (m.t + ph + 14) + "L" + cx + " " + (m.t + ph + 6) + 'z" fill="#0a1430"/>');
    }
    // líneas entre puntos con valor
    for (var i = 0; i < N - 1; i++) {
      var a = cfg.points[i], b = cfg.points[i + 1];
      if (ci != null && i + 1 > ci) break;
      if (a.v == null || b.v == null || a.status === "future" || b.status === "future") continue;
      var dashed = a.status === "imp" || b.status === "imp";
      o.push('<line x1="' + X(i) + '" y1="' + Y(a.v) + '" x2="' + X(i + 1) + '" y2="' + Y(b.v) + '" stroke="#081a3d" stroke-width="2"' + (dashed ? ' stroke-dasharray="4 4" opacity=".7"' : "") + "/>");
    }
    // puntos
    cfg.points.forEach(function (p, i) {
      if (ci != null && i > ci) return;
      if (ci == null) return;
      var x = X(i);
      if (p.status === "obs") {
        o.push('<circle cx="' + x + '" cy="' + Y(p.v) + '" r="5" fill="#081a3d" stroke="#fff" stroke-width="1.5"/>');
      } else if (p.status === "imp") {
        var yy = Y(p.v);
        o.push('<path d="M' + x + " " + (yy - 7) + "L" + (x + 7) + " " + yy + "L" + x + " " + (yy + 7) + "L" + (x - 7) + " " + yy + 'z" fill="#fff3d1" stroke="#6a4400" stroke-width="2.4"/>');
      } else if (p.status === "miss") {
        var my = m.t + ph - 12;
        o.push('<path d="M' + (x - 5) + " " + (my - 5) + "l10 10M" + (x + 5) + " " + (my - 5) + 'l-10 10" stroke="#3f4753" stroke-width="2.4" stroke-linecap="round"/>');
      }
      if (p.note) {
        o.push('<path d="M' + x + " " + (Y(p.v) - 26) + "l8 14h-16z\" fill=\"#961f0e\"/><text x=\"" + x + '" y="' + (Y(p.v) - 31) + '" text-anchor="middle" font-size="12" font-weight="700" fill="#961f0e">' + esc(p.note) + "</text>");
      }
    });
    // valor del último punto revelado
    if (ci != null && cfg.points[ci] && cfg.points[ci].v != null && cfg.showLast !== false) {
      var prevP = cfg.points[ci - 1], below = prevP && prevP.v != null && prevP.v > cfg.points[ci].v;
      o.push('<text x="' + X(ci) + '" y="' + (Y(cfg.points[ci].v) + (below ? 24 : -12)) + '" text-anchor="middle" font-size="12" font-weight="700" fill="#0a1430" paint-order="stroke" stroke="#fff" stroke-width="3">' + num(cfg.points[ci].v, 3) + "</text>");
    }
    // eje x
    var step = Math.max(1, Math.ceil(56 / bw));
    cfg.points.forEach(function (p, i) {
      if (i % step === 0) {
        o.push('<text x="' + X(i) + '" y="' + (m.t + ph + 32) + '" text-anchor="middle" font-size="12" fill="#2f3d52">' + esc(p.label) + "</text>");
      }
    });
    if (ci != null) o.push('<text x="' + X(ci) + '" y="' + (m.t + ph + 50) + '" text-anchor="' + (X(ci) > w - 60 ? "end" : "middle") + '" font-size="12" font-weight="700" fill="#0a1430">Reloj: ' + esc(cfg.points[ci].label) + "</text>");
    o.push("</svg>");
    return o.join("");
  }
  function mountCharts() {
    Array.prototype.forEach.call(main.querySelectorAll("[data-chart]"), function (el) {
      var cfg = CHARTS[el.getAttribute("data-chart")];
      if (cfg) el.innerHTML = chartSvg(cfg, el.clientWidth || 600);
    });
  }
  function legend(items) {
    var all = {
      obs: '<li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="#081a3d"/></svg>Observado</li>',
      imp: '<li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.500l6.500 6.500L8 14.500 1.500 8z" fill="#fff3d1" stroke="#6a4400" stroke-width="2"/></svg>Imputado (no es una medición)</li>',
      miss: '<li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="#3f4753" stroke-width="2.400" stroke-linecap="round"/></svg>Sin dato (el trazo no se une)</li>',
      thr: '<li><svg width="26" height="16" viewBox="0 0 26 16" aria-hidden="true"><line x1="1" x2="25" y1="8" y2="8" stroke="#0a1430" stroke-width="2" stroke-dasharray="6 4"/></svg>Umbral del protocolo</li>',
      emi: '<li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><line x1="8" x2="8" y1="1" y2="15" stroke="#081a3d" stroke-width="2.400"/></svg>Fecha de emisión</li>',
      clk: '<li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><line x1="8" x2="8" y1="1" y2="15" stroke="#0a1430" stroke-width="1.600" stroke-dasharray="2 3"/></svg>Reloj histórico</li>'
    };
    return '<ul class="legend" aria-label="Leyenda del gráfico">' + items.map(function (k) { return all[k]; }).join("") + "</ul>";
  }

  /* ---------- piezas del seguimiento ---------- */
  function obsAt(site, date) {
    return site.series.filter(function (p) { return p.date === date; })[0];
  }
  var MODELS = ["Regresión logística", "Random Forest", "HistGradientBoosting"];
  function slotsFor(site, st) {
    var a = st.emission, ex = site.forecastKind === "example", mode = st.demo;
    function slot(h, kind, votes, o) { return Object.assign({ h: h, target: addDays(a, h), kind: kind, votes: votes, example: ex }, o || {}); }
    if (mode === "alert") {
      return [slot(1, "alert", 2, { scores: [0.66, 0.58, 0.41], combined: 0.55 }), slot(2, "alert", 3, { scores: [0.78, 0.71, 0.64], combined: 0.71 }), slot(3, "calm", 1, { scores: [0.55, 0.24, 0.19], combined: 0.33 })].map(function (s) { return Object.assign(s, { example: true }); });
    }
    if (mode === "unavailable") {
      return [slot(1, "calm", 0, { example: true, scores: [0.11, 0.08, 0.14], combined: 0.11 }),
        slot(2, "na", null, { reason: "Uno de los modelos no pudo calcular este horizonte con los datos disponibles.", example: true }),
        slot(3, "na", null, { reason: "Todavía no hay un pronóstico preparado para este horizonte.", example: true })];
    }
    if (mode === "missing") {
      return [1, 2, 3].map(function (h) { return slot(h, "na", null, { missingData: true, example: true, reason: "Faltan datos recientes para calcular este horizonte." }); });
    }
    if (ex) {
      return [slot(1, "calm", 0, { scores: null }), slot(2, "alert", 2, { scores: null }), slot(3, "calm", 0, { scores: null })];
    }
    return [1, 2, 3].map(function (h) {
      var k = a + "|" + h;
      return slot(h, "calm", 0, { combined: site.knownScores[k] != null ? site.knownScores[k] : null, scores: null });
    });
  }
  function agreementText(s) {
    if (s.votes == null) return "Sin acuerdo para mostrar";
    if (s.votes === 3) return "Los 3 modelos coinciden en la alerta";
    if (s.votes === 2) return "2 de 3 modelos indican alerta";
    if (s.votes === 1) return "1 de 3 modelos indica alerta";
    return "Los 3 modelos coinciden en que no hay alerta";
  }
  function pips(votes) {
    var out = "";
    for (var i = 0; i < 3; i++) out += '<span class="pip' + (votes == null ? " pip--missing" : i < votes ? " pip--on" : "") + '"></span>';
    return '<span class="pips" aria-hidden="true">' + out + "</span>";
  }
  function gateFor(site, st, s) {
    if (s.kind === "na") return { state: "none", reason: s.missingData ? "No hay pronóstico para revisar: faltan datos." : "No hay pronóstico para revisar en este horizonte." };
    if (st.clock < s.target) return { state: "locked", reason: "Todavía no disponible según el reloj histórico. Se habilita cuando el reloj llegue al " + fdl(s.target) + "." };
    var p = obsAt(site, s.target);
    if (!p || p.status === "miss") return { state: "blocked", reason: "No se puede revisar con el dato disponible: no hay una observación para el día objetivo." };
    if (p.status === "imp") return { state: "blocked", reason: "No se puede revisar con el dato disponible: el valor del día objetivo fue imputado y no es una observación independiente." };
    return { state: "enabled" };
  }
  function outcomeHtml(site, st, s) {
    if (s.kind === "na") return '<p class="muted">Sin pronóstico, no hay comparación posible.</p>';
    if (st.clock < s.target) return '<p class="muted">Todavía no ocurrió según el reloj: el valor del ' + fd(s.target) + " no se revela.</p>";
    var p = obsAt(site, s.target);
    if (!p || p.status === "miss") return '<div class="outcome">' + chip("miss", "miss", "Sin dato") + "<span>No hay observación para el " + fd(s.target) + ". La falta de datos no equivale a ausencia de alerta ni de estrés.</span></div>";
    var rel = "";
    if (site.threshold != null && p.status === "obs") rel = p.v < site.threshold ? " Quedó por debajo del umbral del protocolo." : " Quedó por encima del umbral del protocolo.";
    if (p.status === "imp") return '<div class="outcome">' + chip("imp", "imp", "Imputado") + "<strong class=\"num\">" + num(p.v) + " m³/m³</strong><span>Valor completado a partir del día anterior para el " + fd(s.target) + ". No es una observación independiente.</span></div>";
    return '<div class="outcome">' + chip("obs", "obs", "Observado") + '<strong class="num">' + num(p.v) + " m³/m³</strong><span>Humedad del suelo el " + fd(s.target) + "." + rel + "</span></div>";
  }
  function reviewHtml(key, gate, s) {
    var r = S.reviews[key];
    if (S.form && S.form.key === key) {
      var f = S.form;
      return '<form class="review-form" data-form="' + key + '" novalidate>' +
        '<fieldset><legend>¿Qué opinás de esta decisión?</legend>' +
        '<label class="radio"><input type="radio" name="act-' + key + '" value="confirm"' + (f.action === "confirm" ? " checked" : "") + ' data-fid="rv-c-' + key + '"> Confirmo la decisión mostrada</label>' +
        '<label class="radio"><input type="radio" name="act-' + key + '" value="reject"' + (f.action === "reject" ? " checked" : "") + ' data-fid="rv-r-' + key + '"> Rechazo la decisión mostrada</label></fieldset>' +
        '<div><label class="control__label" for="cm-' + key + '">Comentario (opcional)</label><textarea id="cm-' + key + '" data-fid="rv-t-' + key + '" data-change="comment">' + esc(f.comment) + "</textarea></div>" +
        (f.error ? '<p role="alert" class="callout callout--alert">' + ICON.alert + "<span>" + esc(f.error) + "</span></p>" : "") +
        '<div class="btn-row"><button type="submit" class="btn btn--review" data-fid="rv-s-' + key + '">Guardar opinión (simulado)</button>' +
        '<button type="button" class="btn btn--ghost" data-act="form-cancel" data-fid="rv-x-' + key + '">Cancelar</button></div>' +
        '<p class="note-sim">Guardado simulado: no se escribe nada. Registrar una opinión no reentrena ni recalibra los modelos automáticamente.</p></form>';
    }
    if (r) {
      return '<div class="chip-row">' + chip("rv-saved", "check", "Revisión guardada") + "</div>" +
        "<p>" + (r.action === "confirm" ? "Confirmaste" : "Rechazaste") + " la decisión mostrada." + (r.comment ? ' Comentario: «' + esc(r.comment) + "»." : "") + "</p>" +
        '<p class="note-sim">Simulado. El pronóstico original se conserva y los próximos resultados no cambian automáticamente. Podés corregir tu opinión cuando quieras.</p>' +
        '<div class="btn-row"><button class="btn btn--ghost btn--sm" data-act="form-open" data-key="' + key + '" data-fid="rv-e-' + key + '">' + ICON.pencil + " Corregir opinión</button></div>";
    }
    if (gate.state === "enabled") {
      return '<div class="chip-row">' + chip("rv-pending", "pencil", "Revisión pendiente") + "</div>" +
        "<p>Ya se conoce el valor del día objetivo. Podés registrar tu revisión.</p>" +
        '<div class="btn-row"><button class="btn btn--sm" data-act="form-open" data-key="' + key + '" data-fid="rv-o-' + key + '">Revisar este resultado</button></div>';
    }
    return '<div class="chip-row">' + chip("rv-lock", "lock", "Revisión no habilitada") + '</div><p class="lock">' + ICON.lock + "<span>" + esc(gate.reason) + "</span></p>";
  }
  function hzCard(site, st, s, key, opts) {
    opts = opts || {};
    var cls = s.kind === "alert" ? "hz--alert" : s.kind === "calm" ? "hz--calm" : "hz--na";
    var sig = s.kind === "alert" ? '<span class="signal signal--alert">' + ICON.alert + "Alerta prevista</span>" :
      s.kind === "calm" ? '<span class="signal signal--calm">' + ICON.calm + "Sin alerta prevista</span>" :
      '<span class="signal signal--na">' + ICON.na + (s.missingData ? "Sin datos" : "Horizonte no disponible") + "</span>";
    var advice = s.kind === "alert" ? "Puede haber falta de agua. Revisá cómo está el cultivo." :
      s.kind === "calm" ? "No se anticipa una alerta para esta fecha. Seguí observando el cultivo: la ausencia de alerta no garantiza ausencia de estrés." :
      esc(s.reason) + " Sin pronóstico no es lo mismo que sin alerta.";
    var detail = "";
    if (s.kind !== "na") {
      var body = "";
      if (s.scores) {
        body = '<ul class="models">' + MODELS.map(function (nm, i) { return "<li><span>" + nm + '</span><span class="num">puntaje ' + num(s.scores[i], 2) + " · " + (s.scores[i] >= 0.5 ? "indica alerta" : "no indica alerta") + "</span></li>"; }).join("") + "</ul>" +
          '<p>Puntaje combinado (promedio de los tres): <strong class="num">' + num(s.combined, 2) + "</strong>. La política vigente promedia los puntajes; es un puntaje, no un porcentaje de riesgo.</p>";
      } else if (s.combined != null) {
        body = '<p>Puntaje combinado (promedio de los tres modelos): <strong class="num">' + num(s.combined, 3) + "</strong>. Es un puntaje, no un porcentaje de riesgo.</p><p class=\"muted\">Los puntajes de cada modelo no están incluidos en este prototipo.</p>";
      } else {
        body = '<p class="muted">Los puntajes no están incluidos en este prototipo. Un puntaje no es un porcentaje de riesgo: no hay una probabilidad calibrada para mostrar.</p>';
      }
      detail = '<details class="disclosure"><summary>Ver detalle por modelo</summary><div class="disclosure__body">' + body + "</div></details>";
    }
    var gate = opts.gate || gateFor(site, st, s);
    return '<article class="card hz ' + cls + (s.example ? " hz--example" : "") + '" aria-labelledby="hz-' + key + '">' +
      '<header class="hz__head"><div class="hz__title"><h3 id="hz-' + key + '"><span class="hz__plus">+' + s.h + '</span> día' + (s.h > 1 ? "s" : "") + '</h3><span class="hz__target">Para el ' + fdl(s.target) + "</span></div>" +
      '<div class="hz__signal">' + sig + (s.example ? chip("example", "", "Ejemplo de interfaz") : "") + "</div></header>" +
      '<p class="hz__advice">' + advice + "</p>" +
      (s.kind !== "na" ? '<div class="agree" aria-label="Acuerdo entre modelos">' + pips(s.votes) + '<span class="agree__txt">' + agreementText(s) + "</span></div>" : "") +
      detail +
      '<div class="hz__block"><h4>Qué ocurrió después</h4>' + (opts.outcome || outcomeHtml(site, st, s)) + "</div>" +
      '<div class="hz__block"><h4>Tu revisión</h4>' + reviewHtml(key, gate, s) + "</div></article>";
  }
  function skeletonCards() {
    var c = '<div class="card hz" aria-hidden="true"><div class="skeleton" style="height:28px;width:45%"></div><div class="skeleton sk-line" style="width:80%"></div><div class="skeleton sk-line" style="width:65%"></div><div class="skeleton" style="height:64px;margin-top:8px"></div><div class="skeleton sk-line" style="width:55%"></div></div>';
    return '<div class="grid-3" role="status" aria-label="Cargando pronóstico">' + c + c + c + "</div>";
  }
  function errorBox(act, label) {
    return '<div class="error-box" role="alert"><div class="callout callout--alert" style="border:0;padding:0;background:none">' + ICON.alert + "<div><strong>No pudimos cargar el pronóstico.</strong><p>Falló la comunicación con el servicio. Esto es un error de carga: no significa que no haya alerta. Podés reintentar.</p></div></div>" +
      '<div class="btn-row"><button class="btn" data-act="' + act + '" data-fid="retry-' + act + '">' + (label || "Reintentar") + "</button></div></div>";
  }

  function chartConfigFor(site, st) {
    var pts = site.series.map(function (p) { return { date: p.date, label: fd(p.date), v: p.v, status: p.date > st.clock ? "future" : p.status }; });
    var ei = pts.findIndex(function (p) { return p.date === st.emission; });
    var ci = pts.findIndex(function (p) { return p.date === st.clock; });
    var band = null;
    if (ei >= 0) band = { from: Math.min(ei + 1, pts.length - 1), to: Math.min(ei + 3, pts.length - 1), label: "+1 +2 +3" };
    var shown = pts.filter(function (p) { return p.date <= st.clock; });
    var nObs = shown.filter(function (p) { return p.status === "obs"; }).length, nImp = shown.filter(function (p) { return p.status === "imp"; }).length, nMiss = shown.filter(function (p) { return p.status === "miss"; }).length;
    return {
      id: "site-" + site.id, points: pts, yDomain: site.yDomain, yStep: site.id === "pergamino" ? 0.02 : 0.03, unit: "Humedad del suelo (m³/m³)",
      threshold: site.threshold, emissionIndex: ei, clockIndex: ci, band: band,
      aria: "Humedad del suelo de " + site.name + " del " + fd(pts[0].date) + " al " + fd(site.clockMax) + ". Revelado hasta el " + fd(st.clock) + ": " + nObs + " observados, " + nImp + " imputados, " + nMiss + " sin dato." + (site.threshold != null ? " Umbral " + num(site.threshold, 3) + " m³/m³." : ""),
      counts: { obs: nObs, imp: nImp, miss: nMiss, total: shown.length }, shown: shown
    };
  }
  function tableHtml(site, shown) {
    var rows = shown.map(function (p) {
      var t = p.status === "obs" ? "Observado" : p.status === "imp" ? "Imputado" : "Sin observación";
      return "<tr><td>" + fdy(p.date) + '</td><td class="r">' + (p.v == null ? "—" : num(p.v)) + "</td><td>" + t + "</td></tr>";
    }).join("");
    return '<div class="tbl-wrap"><table><caption>Humedad del suelo revelada (m³/m³)</caption><thead><tr><th scope="col">Fecha</th><th scope="col" class="r">Humedad</th><th scope="col">Tipo de dato</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
  }
  function coverHtml(c, extra) {
    var t = Math.max(1, c.total);
    return '<div class="cover" role="group" aria-label="Cobertura de humedad del suelo"><div class="cover__bar" aria-hidden="true">' +
      '<span class="cover__seg--obs" style="width:' + (c.obs / t * 100) + '%"></span><span class="cover__seg--imp" style="width:' + (c.imp / t * 100) + '%"></span><span class="cover__seg--miss" style="width:' + (c.miss / t * 100) + '%"></span></div>' +
      '<div class="cover__nums"><span>' + chip("obs", "obs", c.obs + (c.obs === 1 ? " observado" : " observados")) + "</span><span>" + chip("imp", "imp", c.imp + (c.imp === 1 ? " imputado" : " imputados")) + "</span><span>" + chip("miss", "miss", c.miss + " sin dato") + "</span></div>" + (extra || "") + "</div>";
  }

  /* ---------- vista de seguimiento (A y B) ---------- */
  var DEMO_OPTS = [["real", "Datos de ejemplo"], ["alert", "Con alerta"], ["unavailable", "Horizonte no disponible"], ["missing", "Datos faltantes"], ["loading", "Cargando"], ["error", "Error de carga"]];
  function siteView(id) {
    var site = D.sites[id], st = S.site[id];
    var cfg = chartConfigFor(site, st); CHARTS["site-" + id] = cfg;
    var slots = slotsFor(site, st);
    var dates = []; for (var d = st.emission; d <= site.clockMax; d = addDays(d, 1)) dates.push(d);
    var emissions = site.emissions.map(function (e) { return '<button type="button" aria-pressed="' + (e === st.emission) + '" data-act="emission" data-v="' + e + '" data-fid="em-' + e + '">' + fd(e) + "</button>"; }).join("");
    var firstT = addDays(st.emission, 1), lastT = addDays(st.emission, 3);
    var tagIcon = site.tagKind === "external" ? "" : "";
    var forecast;
    if (st.demo === "loading") forecast = skeletonCards();
    else if (st.demo === "error") forecast = errorBox("retry-site", "Reintentar");
    else forecast = (st.demo === "missing" ? '<div class="callout callout--warn" role="note">' + ICON.info + "<div><strong>Datos faltantes.</strong> Faltan datos recientes para calcular los horizontes. Faltar datos no equivale a ausencia de alerta ni de estrés: verificá el cultivo.</div></div>" : "") +
      (st.demo !== "real" || site.forecastKind === "example" ? '<div class="callout callout--na" role="note">' + ICON.info + "<div>" + (site.forecastKind === "example" && st.demo === "real" ? "<strong>Ejemplo de interfaz.</strong> Los pronósticos de " + esc(site.name) + " se generan al preparar la demo y este prototipo no los incluye. Las tarjetas muestran cómo se verán; no son resultados de " + esc(site.name) + "." : "<strong>Estado de ejemplo.</strong> Esta simulación de diseño muestra cómo se ve el estado seleccionado; no es un resultado real.") + "</div></div>" : "") +
      '<div class="grid-3">' + slots.map(function (s) { return hzCard(site, st, s, id + "-" + st.emission + "-" + s.h + "-" + st.demo); }).join("") + "</div>";
    var headline = "";
    if (st.demo === "real" && site.forecastKind === "persisted") {
      headline = '<p class="lead"><strong>Sin alerta prevista en los 3 horizontes</strong> de esta emisión. Los 3 modelos coinciden en cada uno. Sin alerta no significa que el cultivo esté libre de estrés.</p>';
    }
    var evid = site.evidenceLink ?
      '<div class="callout callout--info">' + ICON.info + '<div><strong>Evidencia de este método.</strong> Hay una evaluación agregada de Pergamino 2023, exploratoria y no independiente. <a href="#/evidencia">Ver evidencia y sus límites</a>.</div></div>' :
      '<div class="callout callout--na">' + ICON.info + '<div><strong>Sin evaluación agregada equivalente.</strong> Melchor Romero no tiene una evaluación retrospectiva propia acreditada, y no se le atribuyen los resultados de Pergamino. <a href="#/evidencia">Ver por qué</a>.</div></div>';
    var illus = site.seriesIllustrative ? '<div class="callout callout--sim" role="note">' + ICON.info + "<div><strong>Serie ilustrativa.</strong> La serie diaria de humedad de Pergamino no está versionada en el repositorio: los puntos de este gráfico son un ejemplo de forma, no mediciones. El umbral sí corresponde al protocolo.</div></div>" : "";
    return '<div class="page-head">' +
      '<div class="title-row"><div class="stack" style="gap:6px"><p class="eyebrow">Seguimiento histórico</p><h1>' + site.name + '</h1>' +
      '<div class="chip-row">' + chip(site.tagKind === "external" ? "ext" : "hist", "", site.tag) + chip("hist", "", "Histórico") + "<span class=\"muted\">" + esc(site.periodLabel) + "</span></div></div>" +
      '<div class="locality-switch" role="group" aria-label="Localidad">' +
      '<a href="#/pergamino"' + (id === "pergamino" ? ' aria-current="page"' : "") + ">Pergamino</a><a href=\"#/melchor\"" + (id === "melchor" ? ' aria-current="page"' : "") + ">Melchor Romero</a></div></div>" +
      '<p class="lead">Origen: ' + esc(site.source) + ". " + esc(site.provenanceNote) + "</p></div>" +
      '<div class="facts" role="list" aria-label="Contexto de lectura">' +
      '<div class="fact" role="listitem"><div class="fact__k">Datos que se ven</div><div class="fact__v">' + site.tag + '</div><div class="fact__s">' + esc(site.source) + "</div></div>" +
      '<div class="fact" role="listitem"><div class="fact__k">Pronóstico emitido</div><div class="fact__v">' + fd(st.emission) + '</div><div class="fact__s">con datos hasta el ' + fdy(st.emission) + "</div></div>" +
      '<div class="fact" role="listitem"><div class="fact__k">Aplica para</div><div class="fact__v">' + fd(firstT) + " – " + fd(lastT) + '</div><div class="fact__s">horizontes +1, +2 y +3 días</div></div>' +
      '<div class="fact" role="listitem"><div class="fact__k">Reloj histórico</div><div class="fact__v">' + fd(st.clock) + '</div><div class="fact__s">se revelan datos hasta esta fecha</div></div></div>' +
      '<section class="section" aria-labelledby="h-ctl"><div class="section__head"><h2 id="h-ctl">Elegí qué recorrer</h2><span class="section__step">Este recorrido no genera pronósticos nuevos</span></div>' +
      '<div class="card controls"><div role="group" aria-labelledby="lb-em"><span class="control__label" id="lb-em">Emisión <span class="control__hint">Cuándo se hizo el pronóstico</span></span><div class="seg">' + emissions + "</div></div>" +
      '<div role="group" aria-labelledby="lb-ck"><span class="control__label" id="lb-ck">Reloj histórico <span class="control__hint">Qué observaciones y revisiones se revelan</span></span>' +
      '<div class="clock"><button class="btn btn--ghost" data-act="clock-back" data-fid="ck-b"' + (st.clock <= st.emission ? " disabled" : "") + ' aria-label="Retroceder un día">‹ Día</button>' +
      '<select aria-label="Recorrido hasta" data-change="clock" data-fid="ck-s">' + dates.map(function (x) { return '<option value="' + x + '"' + (x === st.clock ? " selected" : "") + ">" + fdl(x) + "</option>"; }).join("") + "</select>" +
      '<button class="btn" data-act="clock-fwd" data-fid="ck-f"' + (st.clock >= site.clockMax ? " disabled" : "") + ' aria-label="Avanzar un día">Día ›</button></div></div></div>' +
      '<p class="readout">Viendo la emisión del <strong>' + fdl(st.emission) + "</strong> · recorrido avanzado hasta el <strong>" + fdl(st.clock) + "</strong>.</p></section>" +
      '<section class="section" aria-labelledby="h-fc"><div class="section__head"><h2 id="h-fc">Qué indican los modelos</h2><span class="section__step">Tres modelos · puntaje promedio</span></div>' + headline +
      '<div id="forecast-area" aria-live="polite">' + forecast + "</div>" +
      '<details class="disclosure" style="background:#fff"><summary>Estados de ejemplo (solo diseño)</summary><div class="disclosure__body"><p class="muted">Cambia únicamente esta sección para ver cómo se presentan los estados.</p><div class="seg" role="group" aria-label="Estado de ejemplo">' +
      DEMO_OPTS.map(function (o) { return '<button type="button" aria-pressed="' + (st.demo === o[0]) + '" data-act="demo" data-v="' + o[0] + '" data-fid="dm-' + o[0] + '">' + o[1] + "</button>"; }).join("") + "</div></div></details></section>" +
      '<section class="section" aria-labelledby="h-ch"><div class="section__head"><h2 id="h-ch">Qué se observó</h2><span class="section__step">Humedad del suelo · m³/m³</span></div>' + illus +
      '<div class="card chart-card"><div class="chart" data-chart="site-' + id + '"></div>' + legend(site.threshold != null ? ["obs", "imp", "miss", "thr", "emi", "clk"] : ["obs", "imp", "miss", "emi", "clk"]) +
      '<p class="chart-note">' + esc(site.thresholdNote) + " No se muestran valores posteriores al reloj. Los huecos no se conectan como si hubiera mediciones.</p>" +
      '<details class="disclosure"><summary>Ver como tabla</summary><div class="disclosure__body">' + tableHtml(site, cfg.shown) + "</div></details></div></section>" +
      '<section class="section" aria-labelledby="h-dq"><div class="section__head"><h2 id="h-dq">Calidad de los datos</h2><span class="section__step">Hasta el ' + fd(st.clock) + "</span></div>" +
      '<div class="card">' + coverHtml(cfg.counts, '<p class="muted">Humedad del suelo, ' + cfg.counts.total + " días revelados." + (site.seriesIllustrative ? " Cobertura de la serie ilustrativa." : " Cobertura calculada sobre el dataset versionado.") + " Las demás variables no se incluyen en este prototipo.</p>") + "</div></section>" +
      '<section class="section" aria-labelledby="h-ev"><h2 id="h-ev">Evidencia y límites</h2>' + evid +
      '<p class="muted">Herramienta en evaluación para apoyar la revisión: no automatiza el riego. Verificá siempre el cultivo.</p></section>';
  }

  /* ---------- laboratorio (C) ---------- */
  var LAB_STEPS = [
    { id: "A", title: "Historial normal", btn: "Generar historial de prueba", sc: "Normal" },
    { id: "B", title: "Lectura anómala", btn: "Introducir una lectura anómala", sc: "Anomalía" },
    { id: "C", title: "Interrupción", btn: "Simular una interrupción", sc: "Interrupción" },
    { id: "D", title: "Recuperación", btn: "Simular la recuperación", sc: "Recuperación" }
  ];
  function labVal(day) { return 0.31 + 0.026 * Math.sin(day / 5.5) + 0.009 * Math.sin(day * 2.3); }
  function labCfg(step) {
    var pts = [];
    for (var day = 100; day <= 125; day++) {
      var status = "future", v = labVal(day), note = null;
      if (step >= 1 && day <= 120) status = "obs";
      if (step >= 2 && day === 121) { status = "obs"; note = "85 °C"; }
      if (step === 3 && day >= 122) { status = "miss"; v = null; }
      if (step >= 4 && day >= 122) status = "obs";
      if (step === 0) status = "future";
      pts.push({ label: "Día " + day, date: day, v: status === "miss" ? null : v, status: status, note: note });
    }
    var ci = step === 0 ? null : step === 1 ? 20 : step === 2 ? 21 : 25;
    var shown = pts.filter(function (p, i) { return ci != null && i <= ci; });
    return {
      id: "lab", points: pts, yDomain: [0.24, 0.40], yStep: 0.04, unit: "Humedad simulada (m³/m³)", threshold: null, emissionIndex: null, clockIndex: ci,
      band: step >= 4 ? { from: 22, to: 25, label: "Recuperado (sintético)" } : null,
      aria: "Serie sintética de humedad, días 100 a 125. Paso " + step + " de 4." + (step >= 3 ? " Hay días sin lecturas." : ""), showLast: false,
      counts: { obs: shown.filter(function (p) { return p.status === "obs"; }).length, imp: 0, miss: shown.filter(function (p) { return p.status === "miss"; }).length, total: shown.length }, shown: shown
    };
  }
  var LAB_RESULT = [
    { t: "Sesión creada, sin lecturas", b: "Todavía no hay historial. Elegí «Generar historial de prueba» para empezar.", n: "" },
    { t: "Historial normal generado", b: "Se generaron 120 días de lecturas sintéticas (semilla 42) y se simuló la emisión de un pronóstico.", n: "No son mediciones de un cultivo ni de un sensor físico." },
    { t: "Lectura anómala detectada", b: "Se envió una temperatura de 85 °C. El control de calidad la marca como anómala y el valor se conserva a la vista.", n: "Una anomalía de medición no equivale a una alerta de estrés hídrico." },
    { t: "Interrupción simulada", b: "El reloj simulado avanzó 4 días sin lecturas (días 122 a 125).", n: "No se desconecta ningún dispositivo físico: se suspende el envío del generador." },
    { t: "Recuperación simulada", b: "Se generaron lecturas sintéticas para los días 122 a 125 y la serie quedó completa.", n: "No se recuperan mediciones almacenadas por un dispositivo." }
  ];
  function labView() {
    var L = S.lab, step = L.step, cfg = labCfg(step); CHARTS.lab = cfg;
    var next = LAB_STEPS[step];
    var scen = ['<button type="button" aria-pressed="' + (step === 0) + '" data-act="lab-set" data-v="0" data-fid="lb-0">Sin datos</button>'].concat(LAB_STEPS.map(function (s, i) {
      return '<button type="button" aria-pressed="' + (step === i + 1) + '" data-act="lab-set" data-v="' + (i + 1) + '" data-fid="lb-' + (i + 1) + '">' + s.sc + "</button>";
    })).join("");
    var stepper = LAB_STEPS.map(function (s, i) {
      var cls = i < step ? "step--done" : i === step ? "step--now" : "";
      return '<li class="step ' + cls + '"' + (i === step ? ' aria-current="step"' : "") + '><span class="step__n">' + (i < step ? ICON.check : s.id) + '</span><span class="step__t">' + s.title + '</span><span class="step__s">' + (i < step ? "Hecho" : i === step ? "Siguiente acción" : "Pendiente") + "</span></li>";
    }).join("");
    var hist = [["○", "Sesión creada"], ["●", "Normal: historial de 120 días"], ["▲", "Anomalía: temperatura 85 °C"], ["✕", "Interrupción: sin lecturas 4 días"], ["◆", "Recuperación: lecturas completadas"]].map(function (r, i) {
      return '<li class="' + (i <= step ? "" : "is-empty") + '"><span class="tl-ico" aria-hidden="true">' + r[0] + "</span><span>" + r[1] + (i <= step ? (i === step ? " <strong>(actual)</strong>" : "") : " — pendiente") + "</span></li>";
    }).join("");
    var res = LAB_RESULT[step];
    var action;
    if (L.error) action = errorBox("lab-retry", "Reintentar el paso").replace("No pudimos cargar el pronóstico.", "Este paso no pudo completarse.").replace("Falló la comunicación con el servicio. Esto es un error de carga: no significa que no haya alerta. Podés reintentar.", "Falló la simulación del paso. No se modificó ninguna lectura guardada. Podés reintentar.");
    else if (!next) action = '<div class="callout callout--info">' + ICON.check + "<div><strong>Recorrido completo.</strong> Podés volver a empezar con una sesión nueva.</div></div><div class=\"btn-row\"><button class=\"btn btn--ghost\" data-act=\"lab-reset\" data-fid=\"lab-reset\">Iniciar una sesión nueva</button></div>";
    else action = '<div class="btn-row"><button class="btn" data-act="lab-next" data-fid="lab-next"' + (L.busy ? " disabled" : "") + ">" + (L.busy ? '<span class="spinner" aria-hidden="true"></span> Ejecutando…' : "Paso " + next.id + ": " + next.btn) + '</button><button class="btn btn--ghost" data-act="lab-reset" data-fid="lab-reset">Nueva sesión</button></div>';
    var states = step >= 3 ?
      '<div class="callout callout--warn" role="status">' + ICON.alert + "<div><strong>Sin lecturas desde el día 121.</strong> No se muestra «sin alerta» como sustituto de datos faltantes. " + (step === 3 ? "Verificar sensor y cultivo." : "Las lecturas se completaron en la simulación.") + "</div></div>" : "";
    var fcard = step === 0 ? '<div class="chip-row">' + chip("na", "na", "Sin pronóstico") + '</div><p class="muted">Todavía no hay datos para pronosticar.</p>' :
      step >= 3 && step < 4 ? '<div class="chip-row">' + chip("miss", "miss", "Sin datos recientes") + chip("na", "na", "Sin pronóstico") + "</div><p>No se emite pronóstico con datos desactualizados. Sin datos no es lo mismo que sin alerta.</p>" :
      '<div class="chip-row">' + chip("example", "", "Ejemplo de interfaz") + chip("calm", "calm", "Sin alerta prevista") + "</div><p class=\"muted\">Resultado ilustrativo del pipeline sobre datos sintéticos. No tiene valor científico ni es una probabilidad calibrada.</p>";
    return '<div class="lab-banner" role="note"><span style="font-weight:800;letter-spacing:.04em">SIMULACIÓN</span><span>Datos sintéticos</span><span>Sin sensor físico conectado</span></div>' +
      '<div class="page-head" style="margin-top:16px"><p class="eyebrow">Laboratorio</p><h1>Sensor simulado: recorrido guiado</h1><p class="lead">Los días avanzan de forma simulada; no se reciben mediciones de un cultivo. Sirve para ver cómo responde el sistema ante datos normales, una anomalía, una interrupción y una recuperación.</p></div>' +
      '<section class="section" style="margin-top:0" aria-labelledby="h-ls"><h2 id="h-ls">Sesión y escenario</h2><div class="grid-2">' +
      '<div class="card"><dl class="kv"><dt>Sensor de prueba</dt><dd class="mono">lab-0a1b2c3d4e <span class="chip chip--sim">sintético</span></dd><dt>Reloj simulado</dt><dd>' + (step === 0 ? "Sin lecturas" : step === 1 ? "Día 120 del historial" : step === 2 ? "Día 121" : "Día 125") + "</dd><dt>Estado actual</dt><dd>" + res.t + '</dd><dt>Origen de los datos</dt><dd>Simulación (semilla 42)</dd></dl>' +
      '<p class="note-sim" style="margin-top:8px">El reloj simulado no cambia la fecha real del servidor.</p></div>' +
      '<div class="card"><span class="control__label" id="lb-sc">Escenario <span class="control__hint">Saltá a un escenario para ver su estado, o avanzá paso a paso</span></span><div class="seg" role="group" aria-labelledby="lb-sc">' + scen + "</div></div></div></section>" +
      '<section class="section" aria-labelledby="h-lp"><h2 id="h-lp">Recorrido</h2><ol class="stepper">' + stepper + "</ol></section>" +
      '<section class="section" aria-labelledby="h-la"><div class="grid-2"><div class="card stack" aria-live="polite"><h2 id="h-la" style="font-size:1.05rem">Siguiente acción</h2>' + (next ? "<p>" + (step === 0 ? "Empezá generando el historial de prueba." : "Continuá con el paso " + next.id + ".") + "</p>" : "<p>No quedan pasos.</p>") + action + "</div>" +
      '<div class="card stack" aria-live="polite"><h2 style="font-size:1.05rem">Resultado del paso</h2><p><strong>' + res.t + "</strong></p><p>" + res.b + "</p>" + (res.n ? '<p class="callout callout--sim" style="padding:8px 12px">' + res.n + "</p>" : "") + "</div></div>" +
      '<label class="radio" style="margin-top:8px;max-width:30rem"><input type="checkbox" data-change="lab-simerr"' + (L.simErr ? " checked" : "") + ' data-fid="lab-simerr"> Simular un error en la próxima acción (diseño)</label></section>' +
      '<section class="section" aria-labelledby="h-lh"><div class="section__head"><h2 id="h-lh">Historial de la sesión</h2><span class="section__step">Normal · anomalía · interrupción · recuperación</span></div>' + states +
      '<div class="cols-aside"><div class="card chart-card"><div class="chart" data-chart="lab"></div>' +
      '<ul class="legend" aria-label="Leyenda del gráfico"><li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="#081a3d"/></svg>Lectura sintética</li><li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2l7 12H1z" fill="#961f0e"/></svg>Lectura anómala</li><li><svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3l10 10M13 3L3 13" stroke="#3f4753" stroke-width="2.400" stroke-linecap="round"/></svg>Sin lecturas</li></ul>' +
      '<p class="chart-note">Todos los puntos son sintéticos. La anomalía afecta a la temperatura (85 °C), no a la humedad.</p>' +
      '<details class="disclosure"><summary>Ver como tabla</summary><div class="disclosure__body"><div class="tbl-wrap"><table><caption>Lecturas sintéticas reveladas</caption><thead><tr><th scope="col">Día</th><th scope="col" class="r">Humedad (m³/m³)</th><th scope="col">Estado</th></tr></thead><tbody>' +
      cfg.shown.map(function (p) { return "<tr><td>" + p.label + '</td><td class="r">' + (p.v == null ? "—" : num(p.v)) + "</td><td>" + (p.status === "miss" ? "Sin lectura" : p.note ? "Lectura anómala de temperatura (" + p.note + ")" : "Sintético") + "</td></tr>"; }).join("") + '</tbody></table></div></div></details></div>' +
      '<div class="stack"><div class="card"><h3 style="margin-bottom:8px">Línea de tiempo</h3><ul class="timeline">' + hist + '</ul></div><div class="card"><h3 style="margin-bottom:8px">Calidad de los datos de prueba</h3>' + (step === 0 ? '<p class="muted">Sin datos todavía.</p>' : coverHtml(cfg.counts, '<p class="muted">Días del 100 al reloj. Sintéticos.</p>')) + '</div><div class="card"><h3 style="margin-bottom:8px">Pronóstico y revisión</h3>' + fcard + "</div></div></div></section>" +
      '<section class="section"><details class="disclosure" style="background:#fff"><summary>¿Cómo se conectaría un sensor real?</summary><div class="disclosure__body"><p>Un sensor real enviaría lecturas con su identificador al mismo pipeline de ingesta y calidad. Este laboratorio no prueba precisión en campo ni conecta ningún dispositivo.</p></div></details></section>';
  }

  /* ---------- evidencia (D) ---------- */
  var MNAME = {
    average: ["Promedio de modelos", "Política vigente", "active"], majority: ["Mayoría", "Comparación exploratoria", ""], persistence: ["Persistencia", "Referencia sin modelo", "ref"],
    logistic_regression: ["Regresión logística", "Modelo individual", ""], random_forest: ["Random Forest", "Modelo individual", ""], hist_gradient_boosting_classifier: ["HistGradientBoosting", "Modelo individual", ""]
  };
  var METRICS = {
    mcc: { l: "MCC", d: "Acierto equilibrado entre alertas y no alertas (−1 a 1; más es mejor)", k: "mcc", max: 1, fmt: 3 },
    f1: { l: "F1", d: "Equilibrio entre precisión y recall (0 a 1; más es mejor)", k: "f1", max: 1, fmt: 3 },
    recall: { l: "Recall", d: "Días con baja humedad que se detectaron (0 a 1; más es mejor)", k: "recall", max: 1, fmt: 3 },
    precision: { l: "Precisión", d: "De los días con alerta, cuántos eran de baja humedad (0 a 1; más es mejor)", k: "precision", max: 1, fmt: 3 },
    false_alerts: { l: "Falsas alertas", d: "Días con alerta sin baja humedad real (menos es mejor)", k: "false_alerts", max: null, fmt: 0 },
    missed: { l: "Omisiones", d: "Días con baja humedad sin alerta (menos es mejor)", k: "missed", max: null, fmt: 0 }
  };
  var V3 = [["base", .5592, .0287], ["recent_fraction_0.5", .6891, .0407], ["sinteticos", .5450, .0986], ["noise_test_only_0.3", .5605, .0346], ["completa", .5052, .0374], ["noise_both_0.3", .5041, .0719], ["anomalias", .5689, .0395], ["coverage_fraction_0.5", .5238, .0631]];
  var V3_LIM = [
    "«base» es una configuración experimental (Random Forest fijo, sin anomalías ni sintéticos), no un enfoque tradicional de riego.",
    "Detección de anomalías: evidencia mixta. F1 y MCC mejoran en 3 de 5 semillas, pero AP empeora en las 5.",
    "Datos sintéticos: evidencia mixta, restringida a este generador y a un único sitio y año.",
    "«Completa» es consistentemente peor que «base»; no incluye retroalimentación humana cuantitativa.",
    "Escasez por recencia (recent_fraction_0.5) es el único efecto consistente; no permite afirmar que menos datos mejora el desempeño en general.",
    "Ruido: patrón casi nulo o mixto, sin evidencia de robustez general.",
    "Retroalimentación humana: hay evidencia funcional, pero no evidencia cuantitativa de mejora predictiva."
  ];
  function evidenceView() {
    var ev = S.ev, tabs = [["perg", "Pergamino 2023 · pronóstico"], ["v3", "Experimento controlado v3"], ["melc", "Melchor Romero"]];
    var gov = '<div class="gov" role="note">' + ICON.alert + "<div><strong>Estado de gobernanza: evaluación exploratoria no independiente.</strong><p>La ejecución duplicada incumplió el requisito de corrida única: auditoría científica FAIL. Ese estado se distingue del funcionamiento de esta interfaz. No hay un ganador general ni probabilidades operativas acreditadas.</p></div></div>";
    var body = "";
    if (ev.tab === "perg") body = evPerg(); else if (ev.tab === "v3") body = evV3(); else body = evMelchor();
    return '<div class="page-head"><p class="eyebrow">Evidencia</p><h1>Qué se midió y qué se puede afirmar</h1><p class="lead">Resultados agregados, ordenados de lo más simple a lo más técnico. Ningún resultado de esta sección acredita validación agronómica ni preparación productiva.</p></div>' + gov +
      '<div class="ev-tabs" role="tablist" aria-label="Fuente de evidencia" style="margin-top:16px">' + tabs.map(function (t) { return '<button role="tab" aria-selected="' + (ev.tab === t[0]) + '" data-act="ev-tab" data-v="' + t[0] + '" data-fid="evt-' + t[0] + '">' + t[1] + "</button>"; }).join("") + "</div>" +
      '<div role="tabpanel" aria-label="' + esc(tabs.filter(function (t) { return t[0] === ev.tab; })[0][1]) + '">' + body + "</div>";
  }
  function evPerg() {
    var ev = S.ev, H = E.horizons, h = H[ev.hz], M = METRICS[ev.metric];
    var avg = function (k) { return ["1", "2", "3"].map(function (z) { return num(H[z].methods.average[k]); }).join(" → "); };
    var order = ["average", "majority", "persistence", "logistic_regression", "random_forest", "hist_gradient_boosting_classifier"];
    var maxCount = Math.max.apply(null, order.map(function (m) { return h.methods[m][M.k] || 0; })) || 1;
    var bars = order.map(function (m) {
      var val = h.methods[m][M.k], nm = MNAME[m];
      var w = val == null ? 0 : Math.max(0, (M.max ? val / M.max : val / maxCount)) * 100;
      return '<div class="bar-row bar-row--' + (nm[2] || "n") + '"><div class="bar-row__name">' + nm[0] + "<small>" + nm[1] + '</small></div><div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:' + w + '%"></div></div><div class="bar-val">' + (val == null ? "n/d" : num(val, M.fmt)) + "</div></div>";
    }).join("");
    var rows = order.map(function (m) {
      var x = h.methods[m];
      return "<tr><th scope=\"row\">" + MNAME[m][0] + '</th><td class="r">' + num(x.precision) + '</td><td class="r">' + num(x.recall) + '</td><td class="r">' + num(x.f1) + '</td><td class="r">' + num(x.mcc) + '</td><td class="r">' + x.false_alerts + '</td><td class="r">' + x.missed + '</td><td class="r">' + num(x.ap) + '</td><td class="r">' + num(x.brier) + "</td></tr>";
    }).join("");
    var ci = function (k) { var c = h.unc[k]; return c ? "[" + num(c[0]) + "; " + num(c[1]) + "]" : "n/d"; };
    var hzSel = '<div class="seg" role="group" aria-label="Horizonte">' + ["1", "2", "3"].map(function (z) { return '<button type="button" aria-pressed="' + (ev.hz === z) + '" data-act="ev-hz" data-v="' + z + '" data-fid="evh-' + z + '">+' + z + " día" + (z > 1 ? "s" : "") + "</button>"; }).join("") + "</div>";
    var metSel = '<div class="seg" role="group" aria-label="Métrica">' + Object.keys(METRICS).map(function (k) { return '<button type="button" aria-pressed="' + (ev.metric === k) + '" data-act="ev-met" data-v="' + k + '" data-fid="evm-' + k + '">' + METRICS[k].l + "</button>"; }).join("") + "</div>";
    return '<section class="section tier" aria-labelledby="t1"><span class="tier__label"><span class="tier__n">1</span> Resumen</span><h2 id="t1">Pergamino 2023: qué muestra</h2><div class="card"><ul class="takeaways">' +
      "<li>Evaluación sobre " + h.n + " emisiones de 2023 en Pergamino (un sitio, un año ya usado en análisis previos).</li>" +
      "<li>El promedio de los tres modelos detecta la mayoría de los días de baja humedad (recall " + avg("recall") + " en +1, +2 y +3 días), con más falsas alertas a mayor horizonte (" + ["1", "2", "3"].map(function (z) { return H[z].methods.average.false_alerts; }).join(", ") + " días).</li>" +
      "<li>Frente a la mayoría y a la persistencia, las diferencias son pequeñas y sus intervalos incluyen o rozan el cero: no hay un ganador general.</li>" +
      "<li>Los puntajes no son probabilidades calibradas; no se presentan como porcentaje de riesgo.</li></ul></div></section>" +
      '<section class="section tier" aria-labelledby="t2"><span class="tier__label"><span class="tier__n">2</span> Comparación por horizonte</span><h2 id="t2">Cómo se comparan los métodos</h2><div class="card stack"><div class="controls"><div><span class="control__label">Horizonte</span>' + hzSel + '</div><div><span class="control__label">Métrica</span>' + metSel + "</div></div>" +
      '<p class="muted">' + M.d + ". Soporte común: " + h.n + " casos.</p><div class=\"bars\" role=\"group\" aria-label=\"Comparación por método, " + M.l + ", horizonte +" + ev.hz + '">' + bars + "</div>" + (ev.metric === "mcc" || ev.metric === "f1" ? '<p class="note-sim">Rayado: referencia sin modelo (persistencia). Color fuerte: política vigente (promedio).</p>' : "") + "</div></section>" +
      '<section class="section tier" aria-labelledby="t3"><span class="tier__label"><span class="tier__n">3</span> Métricas y soporte</span><h2 id="t3">Soporte y tabla completa</h2><div class="card stack"><div class="chip-row">' + chip("hist", "", "N = " + h.n) + chip("hist", "", h.methods.average.positives + " días con baja humedad") + chip("hist", "", "Prevalencia " + num(h.methods.average.prevalence, 3)) + "</div>" +
      '<details class="disclosure"><summary>Ver tabla de métricas (+' + ev.hz + ' día' + (ev.hz > 1 ? "s" : "") + ")</summary><div class=\"disclosure__body\"><div class=\"tbl-wrap\"><table><caption>Métricas por método, horizonte +" + ev.hz + '</caption><thead><tr><th scope="col">Método</th><th scope="col" class="r">Precisión</th><th scope="col" class="r">Recall</th><th scope="col" class="r">F1</th><th scope="col" class="r">MCC</th><th scope="col" class="r">Falsas alertas</th><th scope="col" class="r">Omisiones</th><th scope="col" class="r">AP</th><th scope="col" class="r">Brier</th></tr></thead><tbody>' + rows + "</tbody></table></div></div></details></div></section>" +
      '<section class="section tier" aria-labelledby="t4"><span class="tier__label"><span class="tier__n">4</span> Detalle técnico</span><h2 id="t4">Intervalos, episodios y trazabilidad</h2><details class="disclosure" style="background:#fff"><summary>Abrir detalle técnico (+' + ev.hz + " día" + (ev.hz > 1 ? "s" : "") + ')</summary><div class="disclosure__body">' +
      "<p><strong>Diferencia de MCC con intervalo de confianza al 95 %</strong> (bootstrap):</p><ul class=\"meta-list\"><li>Promedio − mayoría: <span class=\"num\">" + ci("average_minus_majority") + "</span></li><li>Promedio − persistencia: <span class=\"num\">" + ci("average_minus_persistence") + "</span></li></ul>" +
      "<p><strong>Inicios de episodio detectados</strong> (descriptivo, sin intervalos), sobre " + h.episodes_total + " episodios:</p><ul class=\"meta-list\">" + order.map(function (m) { return "<li>" + MNAME[m][0] + ': <span class="num">' + h.methods[m].detected + " de " + h.episodes_total + "</span></li>"; }).join("") + "</ul>" +
      '<p class="muted">Procedencia: ' + esc(E.source) + " · esquema " + esc(E.schema) + " · sha256 <span class=\"mono\">" + E.sha256.slice(0, 12) + "…</span></p></div></details></section>" +
      '<section class="section tier" aria-labelledby="t5"><span class="tier__label"><span class="tier__n">5</span> Metodología, procedencia y limitaciones</span><h2 id="t5">Cómo leer estos resultados</h2><div class="card"><ul class="meta-list">' +
      "<li><strong>Objetivo:</strong> baja humedad del suelo según el umbral P20 del protocolo. No es un diagnóstico agronómico validado.</li>" +
      "<li><strong>Datos:</strong> Pergamino, reanálisis externos (ERA5-Land y NASA POWER), emisiones diarias de 2023.</li>" +
      "<li><strong>Limitación:</strong> evaluación exploratoria no independiente; 2023 ya se utilizó en análisis anteriores.</li><li><strong>Limitación:</strong> un único sitio y período.</li>" +
      "<li><strong>Limitación:</strong> los puntajes no son probabilidades operativas calificadas.</li><li><strong>Limitación:</strong> las métricas por episodio son descriptivas, sin intervalos.</li>" +
      "<li><strong>Limitación:</strong> no hay función de costo agronómico; no se evaluó riego ni ahorro de agua.</li>" +
      "<li><strong>Comparaciones:</strong> «mayoría» es solo exploratoria; la política vigente conserva el promedio.</li></ul></div></section>";
  }
  function evV3() {
    var bars = V3.map(function (r, i) {
      return '<div class="bar-row bar-row--' + (i === 0 ? "active" : "n") + '"><div class="bar-row__name">' + r[0] + "<small>± " + num(r[2], 3) + " entre semillas</small></div><div class=\"bar-track\" aria-hidden=\"true\"><div class=\"bar-fill\" style=\"width:" + r[1] * 100 + '%"></div></div><div class="bar-val">' + num(r[1], 3) + "</div></div>";
    }).join("");
    return '<section class="section tier"><span class="tier__label"><span class="tier__n">1</span> Resumen</span><h2>Experimento controlado v3</h2><div class="card"><ul class="takeaways"><li>8 configuraciones × 5 semillas, con tag científico congelado. Es un diseño distinto a la evaluación de Pergamino 2023 y a la demo operativa.</li>' +
      "<li>El único efecto consistente es la escasez por recencia; el resto es mixto o casi nulo.</li><li>No hay evidencia cuantitativa de mejora por retroalimentación humana.</li></ul></div></section>" +
      '<section class="section tier"><span class="tier__label"><span class="tier__n">2</span> Comparación por configuración</span><h2>F1 medio por configuración</h2><div class="card stack"><div class="bars" role="group" aria-label="F1 medio por configuración">' + bars + '</div><p class="note-sim">Color fuerte: configuración «base».</p>' +
      '<details class="disclosure"><summary>Ver tabla</summary><div class="disclosure__body"><div class="tbl-wrap"><table><caption>F1 medio y desvío (5 semillas)</caption><thead><tr><th scope="col">Configuración</th><th scope="col" class="r">F1 medio</th><th scope="col" class="r">Desvío</th></tr></thead><tbody>' + V3.map(function (r) { return "<tr><th scope=\"row\">" + r[0] + '</th><td class="r">' + num(r[1], 4) + '</td><td class="r">' + num(r[2], 4) + "</td></tr>"; }).join("") + "</tbody></table></div></div></details></div></section>" +
      '<section class="section tier"><span class="tier__label"><span class="tier__n">5</span> Limitaciones</span><h2>Qué no permite concluir</h2><div class="card"><ul class="meta-list">' + V3_LIM.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul></div></section>";
  }
  function evMelchor() {
    return '<section class="section"><div class="callout callout--na">' + ICON.info + "<div><h2 style=\"font-size:1.1rem;margin-bottom:6px\">Melchor Romero no tiene evaluación agregada propia</h2><p>No se ejecutó ninguna corrida de evaluación retrospectiva agregada para este sitio. Mostrar un panel equivalente al de Pergamino sería fabricar paridad, por eso no se muestra.</p><p>Lo que sí ofrece es un recorrido histórico reproducible desde datos versionados, con la distinción entre observaciones e imputaciones. <a href=\"#/melchor\">Ir al seguimiento de Melchor Romero</a>.</p></div></div></section>" +
      '<section class="section"><div class="card"><h3 style="margin-bottom:8px">Diferencias de alcance</h3><div class="tbl-wrap"><table><thead><tr><th scope="col">Aspecto</th><th scope="col">Pergamino</th><th scope="col">Melchor Romero</th></tr></thead><tbody><tr><th scope="row">Procedencia</th><td>Datos externos (reanálisis)</td><td>Dataset histórico del repositorio</td></tr><tr><th scope="row">Evaluación agregada</th><td>Exploratoria, no independiente (2023)</td><td>No disponible</td></tr><tr><th scope="row">Reproducible desde el repositorio</th><td>No (artefactos externos)</td><td>Sí</td></tr></tbody></table></div></div></section>';
  }

  /* ---------- herramientas técnicas + estados ---------- */
  var TOOLS = [
    ["Mi cultivo", "Seguimiento por sector y punto de medición."], ["Historial y observaciones", "Pronósticos anteriores y observaciones propias."],
    ["Datos disponibles", "Cobertura y calidad de las mediciones."], ["Ajustar próximos pronósticos", "Trazabilidad y recalibración."],
    ["Acerca de esta herramienta", "Alcance, límites y evidencia formal."], ["Reproducción histórica", "Reproducción causal de emisiones históricas."],
    ["Demostración acelerada", "Sensor simulado con reloj acelerado."], ["Resumen", "Último pronóstico guardado y datos disponibles."]
  ];
  function catalogView() {
    var site = D.sites.melchor, st = { emission: "2024-10-24", clock: "2024-10-27", demo: "real" };
    var s = function (h, kind, votes, o) { return Object.assign({ h: h, target: addDays(st.emission, h), kind: kind, votes: votes, example: true }, o || {}); };
    var okGate = { state: "enabled" };
    var cells = [
      ["Alerta", hzCard(site, st, s(1, "alert", 3, { scores: [0.78, 0.71, 0.64], combined: 0.71 }), "cat-1", { gate: { state: "locked", reason: "Ejemplo." }, outcome: '<p class="muted">Sin comparación en el catálogo.</p>' })],
      ["Sin alerta", hzCard(site, st, s(1, "calm", 0, { scores: [0.12, 0.09, 0.15], combined: 0.12 }), "cat-2", { gate: { state: "locked", reason: "Ejemplo." }, outcome: '<p class="muted">Sin comparación en el catálogo.</p>' })],
      ["Horizonte no disponible", hzCard(site, st, s(2, "na", null, { reason: "Uno de los modelos no pudo calcular este horizonte." }), "cat-3")],
      ["Datos faltantes", '<div class="card stack"><div class="chip-row">' + chip("miss", "miss", "Sin dato") + chip("na", "na", "Sin pronóstico") + "</div><p>Faltan datos recientes. <strong>Faltar datos no equivale a ausencia de alerta</strong>: verificá el cultivo.</p></div>"],
      ["Observación imputada", '<div class="card stack"><h3>Humedad del 26 oct</h3>' + outcomeHtml(site, { clock: "2024-10-27" }, s(2, "calm", 0)) + '<p class="muted">Un valor imputado no se presenta como observación real.</p></div>'],
      ["Carga", skeletonCards().replace('grid-3', 'stack')],
      ["Error con reintento", S.cat.retry === "error" ? errorBox("cat-retry", "Reintentar") : S.cat.retry === "loading" ? '<div class="card stack" role="status"><div class="chip-row"><span class="spinner" style="border-color:#cbd5e1;border-top-color:#1d63ed"></span> Reintentando…</div></div>' : '<div class="card stack"><div class="chip-row">' + chip("rv-saved", "check", "Carga correcta") + '</div><p>Se recuperó la conexión.</p><button class="btn btn--ghost" data-act="cat-reset" data-fid="cat-reset">Restablecer ejemplo</button></div>'],
      ["Revisión pendiente", '<div class="card stack">' + reviewHtml("cat-p", okGate, s(1, "calm", 0)) + "</div>"],
      ["Revisión guardada", '<div class="card stack">' + (function () { S.reviews["cat-g"] = { action: "confirm", comment: "" }; var h = reviewHtml("cat-g", okGate, s(1, "calm", 0)); delete S.reviews["cat-g"]; return h; })() + "</div>"],
      ["Revisión no habilitada", '<div class="card stack">' + reviewHtml("cat-l", { state: "locked", reason: "Todavía no disponible según el reloj histórico. Se habilita cuando el reloj llegue al 26 de octubre de 2024." }, s(1, "calm", 0)) + '<hr style="border:0;border-top:1px solid var(--line);width:100%">' + reviewHtml("cat-b", { state: "blocked", reason: "No se puede revisar con el dato disponible: el valor del día objetivo fue imputado y no es una observación independiente." }, s(1, "calm", 0)) + "</div>"]
    ];
    return '<div class="page-head"><p class="eyebrow">Herramientas técnicas</p><h1>Capacidades existentes y catálogo de estados</h1><p class="lead">Acceso secundario a lo que ya existe. Ninguna capacidad se elimina: todas se integrarán al nuevo sistema visual sin cambiar su funcionamiento.</p></div>' +
      '<section class="section" style="margin-top:0"><h2>Capacidades actuales</h2><div class="grid-3">' + TOOLS.map(function (t) { return '<div class="card tool-card"><h3>' + t[0] + "</h3><p class=\"muted\">" + t[1] + '</p><div class="chip-row">' + chip("example", "", "Se integrará sin cambios funcionales") + "</div></div>"; }).join("") + "</div></section>" +
      '<section class="section"><h2>Tres lenguajes de estado, tres colores distintos</h2><div class="grid-3">' +
      '<div class="card stack"><h3>Señal del pronóstico</h3><div class="chip-row">' + chip("alert", "alert", "Alerta prevista") + chip("calm", "calm", "Sin alerta prevista") + chip("na", "na", "No disponible") + '</div><p class="muted">Bermellón y pizarra. Sin alerta no es verde: no significa ausencia de estrés.</p></div>' +
      '<div class="card stack"><h3>Calidad del dato</h3><div class="chip-row">' + chip("obs", "obs", "Observado") + chip("imp", "imp", "Imputado") + chip("miss", "miss", "Sin dato") + '</div><p class="muted">Azul marino, ámbar y gris con trama; cada uno con su forma.</p></div>' +
      '<div class="card stack"><h3>Estado de revisión</h3><div class="chip-row">' + chip("rv-pending", "pencil", "Pendiente") + chip("rv-saved", "check", "Guardada") + chip("rv-lock", "lock", "No habilitada") + '</div><p class="muted">Índigo, con contorno, relleno o candado.</p></div></div></section>' +
      '<section class="section"><h2>Catálogo de estados</h2><p class="muted">Ejemplos reproducibles de diseño. No son resultados reales.</p><div class="state-grid">' + cells.map(function (c) { return '<div class="state-cell"><span class="eyebrow">' + c[0] + "</span>" + c[1] + "</div>"; }).join("") + "</div></section>";
  }

  /* ---------- render y eventos ---------- */
  var VIEWS = { pergamino: function () { return siteView("pergamino"); }, melchor: function () { return siteView("melchor"); }, laboratorio: labView, evidencia: evidenceView, herramientas: catalogView };
  var lastRoute = null;
  function render(opts) {
    var route = currentRoute();
    var active = document.activeElement, fid = active && active.getAttribute && active.getAttribute("data-fid");
    var sx = window.scrollX, sy = window.scrollY;
    main.innerHTML = VIEWS[route]();
    renderNav(route);
    document.title = TITLES[route] + " — Prototipo de diseño · Seguimiento del agua";
    mountCharts(); setHdr();
    if (route !== lastRoute) { window.scrollTo(0, 0); main.focus({ preventScroll: true }); say("Vista: " + TITLES[route]); }
    else { window.scrollTo(sx, sy); if (fid) { var el = main.querySelector('[data-fid="' + fid + '"]'); if (el) el.focus({ preventScroll: true }); } }
    lastRoute = route;
    if (S.form && S.form.focus) { var first = main.querySelector('form[data-form] input[type=radio]'); if (first) first.focus(); S.form.focus = false; }
    else if (!fid && S.form && S.form.error) { var er = main.querySelector('form[data-form] [role=alert]'); if (er) er.setAttribute("tabindex", "-1"), er.focus(); }
  }
  function setHdr() { var h = document.querySelector(".app-header"); document.documentElement.style.setProperty("--hdr", (h ? h.offsetHeight : 0) + "px"); }
  function site() { return S.site[currentRoute()]; }
  function setSite(patch) { Object.assign(site(), patch); S.form = null; }

  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-act]"); if (!t || t.disabled) return;
    var act = t.getAttribute("data-act"), v = t.getAttribute("data-v"), st;
    switch (act) {
      case "emission": st = site(); setSite({ emission: v, clock: st.clock < v ? v : st.clock }); say("Emisión del " + fdl(v)); break;
      case "clock-fwd": setSite({ clock: addDays(site().clock, 1) }); say("Reloj: " + fdl(site().clock)); break;
      case "clock-back": setSite({ clock: addDays(site().clock, -1) }); say("Reloj: " + fdl(site().clock)); break;
      case "demo": site().demo = v; break;
      case "retry-site":
        site().demo = "loading"; render();
        setTimeout(function () { site().demo = "real"; render(); say("Pronóstico cargado."); }, 800); return;
      case "form-open": S.form = { key: t.getAttribute("data-key"), action: (S.reviews[t.getAttribute("data-key")] || {}).action || "", comment: (S.reviews[t.getAttribute("data-key")] || {}).comment || "", focus: true }; break;
      case "form-cancel": S.form = null; break;
      case "lab-set": S.lab.step = Number(v); S.lab.error = false; break;
      case "lab-reset": S.lab = { step: 0, busy: false, error: false, simErr: S.lab.simErr }; break;
      case "lab-next": case "lab-retry":
        if (act === "lab-retry") S.lab.simErr = false;
        if (S.lab.simErr) { S.lab.busy = true; render(); setTimeout(function () { S.lab.busy = false; S.lab.error = true; S.lab.simErr = false; render(); say("El paso no pudo completarse."); }, 700); return; }
        S.lab.busy = true; S.lab.error = false; render();
        setTimeout(function () { S.lab.busy = false; S.lab.step = Math.min(4, S.lab.step + 1); render(); say("Paso completado: " + LAB_RESULT[S.lab.step].t); }, 700); return;
      case "ev-tab": S.ev.tab = v; break;
      case "ev-hz": S.ev.hz = v; break;
      case "ev-met": S.ev.metric = v; break;
      case "cat-retry": S.cat.retry = "loading"; render(); setTimeout(function () { S.cat.retry = "ok"; render(); }, 800); return;
      case "cat-reset": S.cat.retry = "error"; break;
      default: return;
    }
    render();
  });
  document.addEventListener("change", function (e) {
    var t = e.target, kind = t.getAttribute && t.getAttribute("data-change"); if (!kind) return;
    if (kind === "clock") { setSite({ clock: t.value }); say("Reloj: " + fdl(t.value)); render(); }
    else if (kind === "lab-simerr") { S.lab.simErr = t.checked; render(); }
    else if (kind === "comment" && S.form) S.form.comment = t.value;
    else if (t.name && t.name.indexOf("act-") === 0 && S.form) S.form.action = t.value;
  });
  document.addEventListener("input", function (e) { if (e.target.getAttribute && e.target.getAttribute("data-change") === "comment" && S.form) S.form.comment = e.target.value; });
  document.addEventListener("submit", function (e) {
    var f = e.target.closest("[data-form]"); if (!f) return;
    e.preventDefault();
    var key = f.getAttribute("data-form"), data = new FormData(f), act = data.get("act-" + key);
    if (!act) { S.form.error = "Elegí si confirmás o rechazás la decisión antes de guardar."; render(); return; }
    S.reviews[key] = { action: act, comment: (data.get ? f.querySelector("textarea").value : "").trim() };
    S.form = null; render(); say("Revisión guardada de forma simulada.");
  });
  window.addEventListener("hashchange", function () { S.form = null; render(); });
  var rt; window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { mountCharts(); setHdr(); }, 120); });
  render();
})();
