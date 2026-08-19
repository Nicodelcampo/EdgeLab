// ===========================================================================
// VISTA «GRAFICO» — un visor normal: velas, o linea con un punto por tick.
//
// Las BARRAS no se arman aca: vienen de `barras.js`, construidas por
// `build_time_bars` / `build_tick_bars` del motor. `build_tick_bars` reinicia el
// contador en cada frontera de sesion (TICKBAR-001), asi que un `arange(n)//N` en
// esta pagina daria barras DISTINTAS de las que mide el proyecto -- y el que
// diverge seria justamente el que se mira.
//
// `tiempo` y `ticks` son EJES DISTINTOS, no dos unidades del mismo (CLAUDE.md), y
// por eso van en dos grupos de botones separados y no en un desplegable unico.
// ===========================================================================
let B = null, gTipo = "velas", gEje = "tiempo", gRes = null, gVista = null, TICKS = null;
// Escala vertical MANUAL: null = automatica al rango visible. Arrastrar sobre el eje de
// precios la fija y la comprime/expande, como en NT8 y en cualquier plataforma.
let gEscala = null;
let arrastrando = false;

function iniGrafico() {
  B = window.BARRAS;
  if (!B) {
    document.querySelector("#wrapG").innerHTML =
      '<div class="vacio"><div><h2>No se pudo leer <code>barras.js</code></h2>' +
      '<p>Generalo con <code>visor_barras_export.py</code>.</p></div></div>';
    return;
  }
  // decodificar los ticks: el payload viene en deltas (dt en ms, dprecio en ticks)
  const t = B.ticks, n = t.n, ts = new Float64Array(n), px = new Int32Array(n);
  let acT = t.t0, acP = t.p0;
  for (let i = 0; i < n; i++) { acT += t.dt_ms[i] * 1e6; acP += t.dp[i]; ts[i] = acT; px[i] = acP; }
  ts[0] = t.t0; px[0] = t.p0;
  TICKS = { ts: ts, px: px, v: t.v, n: n };

  const mk = (id, lista, eje) => document.querySelector(id).insertAdjacentHTML("beforeend",
    lista.map(r => '<button data-eje="' + eje + '" data-res="' + r + '">' + r + "</button>").join(""));
  mk("#gTiempo", B.resoluciones.tiempo, "tiempo");
  mk("#gTicks", B.resoluciones.ticks, "ticks");
  gRes = B.resoluciones.tiempo[0];

  document.querySelectorAll("[data-res]").forEach(b => b.addEventListener("click", () => {
    gEje = b.dataset.eje; gRes = b.dataset.res; gVista = null; pintarG();
  }));
  document.querySelectorAll("[data-tipo]").forEach(b => b.addEventListener("click", () => {
    gTipo = b.dataset.tipo; gVista = null; pintarG();
  }));
  const cg = document.querySelector("#cg");
  cg.addEventListener("wheel", e => { e.preventDefault(); zoomG(e); }, { passive: false });
  cg.addEventListener("mousedown", ev => {
    // Si el click cae sobre el eje de precios, arrastra la ESCALA; si no, paneo.
    const r = ev.currentTarget.getBoundingClientRect();
    if (gEje_area && (ev.clientX - r.left) > gEje_area.xEje) arrastreEscala(ev);
    else arrastreG(ev);
  });
  cg.addEventListener("dblclick", ev => {
    const r = ev.currentTarget.getBoundingClientRect();
    if (gEje_area && (ev.clientX - r.left) > gEje_area.xEje) {
      gEscala = null;                // doble clic en el EJE: escala vertical a auto
    } else {
      gEscala = null; gVista = null; // doble clic en el CHART: encuadra todo de nuevo
    }
    pintarG();
  });
  // Cursor: `crosshair` en el area del chart (lo que usa cualquier plataforma),
  // `ns-resize` sobre el eje de precios, y `grabbing` SOLO mientras se arrastra.
  //
  // La version anterior ponia `grab` en reposo y la manito quedaba pegada: si el
  // mouse salia del canvas durante un arrastre, o si el puntero terminaba sobre el
  // panel, nadie la reseteaba. Con `grabbing` solo durante el arrastre el estado
  // pegado no puede existir -- se elimina la causa, no se la limpia despues.
  cg.addEventListener("mousemove", ev => {
    if (arrastrando) return;
    const r = ev.currentTarget.getBoundingClientRect();
    const enEje = gEje_area && (ev.clientX - r.left) > gEje_area.xEje;
    ev.currentTarget.style.cursor = enEje ? "ns-resize" : "crosshair";
  });
  cg.addEventListener("mouseleave", ev => {
    if (!arrastrando) ev.currentTarget.style.cursor = "default";
  });
  pintarG();
}

function serieG() {
  if (gTipo === "linea") return { tipo: "linea", n: TICKS.n };
  const b = B.barras[gEje][gRes];
  return { tipo: "velas", b: b, n: b.n };
}

function pintarG() {
  const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  document.querySelectorAll("[data-res]").forEach(b =>
    b.classList.toggle("on", b.dataset.eje === gEje && b.dataset.res === gRes));
  document.querySelectorAll("[data-tipo]").forEach(b =>
    b.classList.toggle("on", b.dataset.tipo === gTipo));

  const S = serieG();
  if (!gVista) gVista = { a: Math.max(0, S.n - (gTipo === "linea" ? 1500 : 160)), b: S.n - 1 };
  if (gVista.b - gVista.a < 8) gVista.b = gVista.a + 8;

  const cv = document.querySelector("#cg"), dpr = devicePixelRatio || 1;
  const w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr;
  const g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
  // `pad.r` es el ancho de las etiquetas de precio; `GAP_DER` es aire entre la ultima
  // barra y el eje, como el "right margin" de NT8 / TradingView. Sin el, la vela mas
  // reciente queda pegada al borde y no se ve hacia donde va.
  const GAP_DER = 156;
  const pad = { l: 12, r: 66 + GAP_DER, t: 12, b: 22 };
  const W = w - pad.l - pad.r, H = h - pad.t - pad.b;
  const xEje = pad.l + W + GAP_DER;        // donde arranca la columna de precios
  const a = gVista.a, b = gVista.b, m = b - a + 1;

  // La vista puede salirse del rango de datos: TradingView deja seguir scrolleando
  // hacia el vacio a los costados. Los recorridos se acotan a [0, n-1] pero el mapeo
  // X() sigue usando [a, b], asi que el espacio de mas queda vacio en vez de estirar
  // la serie.
  const av = Math.max(0, a), bv = Math.min(S.n - 1, b);
  let lo = Infinity, hi = -Infinity;
  if (bv >= av) {
    if (S.tipo === "velas") { for (let i = av; i <= bv; i++) { lo = Math.min(lo, S.b.l[i]); hi = Math.max(hi, S.b.h[i]); } }
    else { for (let i = av; i <= bv; i++) { lo = Math.min(lo, TICKS.px[i]); hi = Math.max(hi, TICKS.px[i]); } }
  } else { lo = hi = (gEscala ? gEscala.c : 0); }
  const marg = Math.max(1, (hi - lo) * 0.08); lo -= marg; hi += marg;
  // `gEscala.k` = zoom vertical (arrastre sobre el eje); `gEscala.c` = centro, que
  // el arrastre vertical mueve. Con `gEscala` en null la escala sigue al dato.
  if (gEscala) {
    // SIN TOPE VERTICAL (Nico, 2026-08-19). El limite anterior frenaba el paneo con el
    // precio todavia adentro, y lo que se veia en el borde parecia un corte.
    const semi = Math.max(1, (hi - lo) / 2 * gEscala.k);
    lo = gEscala.c - semi; hi = gEscala.c + semi;
  }

  const X = i => pad.l + (i - a + 0.5) / m * W;
  const Y = p => pad.t + H - (p - lo) / (hi - lo) * H;
  gEje_area = { pad: pad, W: W, H: H, lo: lo, hi: hi, w: w, xEje: xEje };

  g.strokeStyle = cssv("--border"); g.lineWidth = 1;
  g.fillStyle = cssv("--dim2"); g.font = "10px ui-monospace,monospace"; g.textAlign = "left";
  // Cota defensiva del numero de lineas de grilla. NO es la causa del "se corta" que
  // reporto Nico: lo medi despues de escribirlo y con el tope puesto `lo`/`hi` estaban
  // acotados, asi que este bucle nunca podia dispararse. Queda como guarda barata
  // ahora que el paneo es libre y `lo`/`hi` no tienen limite, no como diagnostico.
  //
  // La causa real del corte era el TOPE: frenaba el paneo con parte del precio ya
  // fuera de la pantalla, y lo que quedaba se leia como una serie cortada.
  const paso = Math.max(1, Math.round((hi - lo) / 6));
  const p0 = Math.ceil(lo / paso) * paso;
  const nLineas = Math.min(40, Math.floor((hi - p0) / paso) + 1);
  for (let k = 0, p = p0; k < nLineas; k++, p = p0 + k * paso) {
    const y = Y(p); g.beginPath(); g.moveTo(pad.l, y); g.lineTo(xEje, y); g.stroke();
    g.fillText((p * B.tick_size).toFixed(5), xEje + 6, y + 3);
  }

  if (S.tipo === "velas") {
    // Verde sube / rojo baja: convencion universal de velas, y la de la captura que
    // paso Nico. No colisiona con los chips de estado, que son otra superficie.
    const celda = W / m, cuerpo = Math.max(1, Math.min(14, celda * 0.68));
    for (let i = av; i <= bv; i++) {
      const sube = S.b.c[i] >= S.b.o[i], col = cssv(sube ? "--ok" : "--err"), x = X(i);
      g.strokeStyle = col; g.lineWidth = 1;
      g.beginPath(); g.moveTo(x, Y(S.b.h[i])); g.lineTo(x, Y(S.b.l[i])); g.stroke();
      const y1 = Y(Math.max(S.b.o[i], S.b.c[i])), y2 = Y(Math.min(S.b.o[i], S.b.c[i]));
      g.fillStyle = col; g.fillRect(x - cuerpo / 2, y1, cuerpo, Math.max(1, y2 - y1));
    }
  } else {
    // Linea escalonada con un PUNTO por tick, como el chart de la captura.
    g.strokeStyle = cssv("--dim"); g.lineWidth = 1; g.beginPath();
    for (let i = av; i <= bv; i++) {
      const x = X(i), y = Y(TICKS.px[i]);
      if (i === av) g.moveTo(x, y); else { g.lineTo(x, Y(TICKS.px[i - 1])); g.lineTo(x, y); }
    }
    g.stroke();
    const r = Math.max(0.8, Math.min(2.4, W / m * 0.32));
    for (let i = av; i <= bv; i++) {
      const d = i > 0 ? TICKS.px[i] - TICKS.px[i - 1] : 0;
      g.fillStyle = cssv(d > 0 ? "--ok" : d < 0 ? "--err" : "--dim2");
      g.beginPath(); g.arc(X(i), Y(TICKS.px[i]), r, 0, 6.283); g.fill();
    }
  }

  // overlays de indicadores, ANTES del ultimo precio para que no los tape
  if (typeof dibujarOverlays === "function") {
    const tsDe = ms => {
      // ms -> x, buscando la barra/tick mas cercano en el tramo visible
      const leer = i => (S.tipo === "velas" ? S.b.end_ns[i] : TICKS.ts[i]) / 1e6;
      if (ms <= leer(av)) return X(av);
      if (ms >= leer(bv)) return X(bv);
      let x = av, y = bv;
      while (y - x > 1) { const md = (x + y) >> 1; if (leer(md) < ms) x = md; else y = md; }
      return X(x);
    };
    dibujarOverlays(g, X, Y, pad, W, tsDe);
  }

  // Con paneo libre la vista puede quedar ENTERA fuera de los datos. Ahi no hay
  // ultimo precio ni horas que mostrar: se dibuja el marco vacio y se sale.
  // (Sin esto `hora()` leia un indice inexistente y tiraba "Invalid time value" --
  // un caso que el paneo con clamp no podia alcanzar y el libre si.)
  if (bv < av) {
    g.fillStyle = cssv("--dim2"); g.font = "11px ui-monospace,monospace";
    g.textAlign = "center";
    g.fillText("sin datos en esta ventana — doble clic para reencuadrar",
               pad.l + W / 2, pad.t + H / 2);
    document.querySelector("#infoG").textContent =
      B.instrumento + " · fuera del rango de datos";
    return;
  }

  const ult = S.tipo === "velas" ? S.b.c[bv] : TICKS.px[bv];
  g.strokeStyle = cssv("--accent"); g.setLineDash([3, 3]);
  g.beginPath(); g.moveTo(pad.l, Y(ult)); g.lineTo(xEje, Y(ult)); g.stroke(); g.setLineDash([]);
  g.fillStyle = cssv("--accent"); g.fillRect(xEje + 2, Y(ult) - 8, 62, 16);
  g.fillStyle = "#fff"; g.textAlign = "left";
  g.fillText((ult * B.tick_size).toFixed(5), xEje + 6, Y(ult) + 3);

  const hora = i => {
    const t = S.tipo === "velas" ? S.b.end_ns[i] : TICKS.ts[i];
    return new Date(t / 1e6).toISOString().slice(11, 19);
  };
  g.fillStyle = cssv("--dim2"); g.textAlign = "left"; g.fillText(hora(av), X(av), h - 6);
  g.textAlign = "right"; g.fillText(hora(bv), Math.min(pad.l + W, X(bv)), h - 6);

  document.querySelector("#infoG").textContent =
    B.instrumento + " · " + (gTipo === "linea" ? "tick a tick" : gRes) + " · " +
    (bv - av + 1) + " de " + S.n + (gEscala ? "  · escala manual" : "");
  document.querySelector("#legG").innerHTML = gTipo === "velas"
    ? "<div><b>" + gRes + "</b> · eje <b>" + gEje + "</b></div>" +
      '<div style="color:var(--dim2)">barras del motor, no de la página</div>'
    : "<div><b>tick a tick</b> · un punto por operación</div>" +
      '<div style="color:var(--dim2)">' + TICKS.n.toLocaleString() + " ticks cargados</div>";
}

function zoomG(e) {
  const S = serieG(), r = e.currentTarget.getBoundingClientRect();
  const f = (e.clientX - r.left) / r.width, c = gVista.a + f * (gVista.b - gVista.a);
  const w = Math.max(12, (gVista.b - gVista.a) * (e.deltaY > 0 ? 1.25 : 0.8));
  let a = Math.round(c - f * w), b = Math.round(c + (1 - f) * w);
  // Mismo tope que el paneo: la serie llega hasta el borde y no se sale.
  if (a < 0) { b -= a; a = 0; }
  if (b > S.n - 1) { a -= (b - (S.n - 1)); b = S.n - 1; }
  gVista = { a: Math.max(0, a), b: Math.min(S.n - 1, b) };
  pintarG();
}

let gEje_area = null;

function arrastreEscala(ev) {
  // Arrastrar sobre el eje de precios comprime o expande el rango vertical, anclado
  // al centro visible. Doble clic vuelve a la escala automatica.
  ev.preventDefault();
  const y0 = ev.clientY;
  const base = gEscala ? gEscala.k : 1;
  const centro = gEscala ? gEscala.c : (gEje_area.lo + gEje_area.hi) / 2;
  arrastrando = true;
  const mover = e => {
    const f = Math.exp((e.clientY - y0) / 220);
    gEscala = { k: Math.max(0.05, Math.min(20, base * f)), c: centro };
    pintarG();
  };
  const soltar = () => {
    arrastrando = false;
    removeEventListener("mousemove", mover); removeEventListener("mouseup", soltar);
  };
  addEventListener("mousemove", mover); addEventListener("mouseup", soltar);
}

function arrastreG(ev) {
  // Desplazamiento LIBRE en los dos ejes, como TradingView: dx mueve el tiempo, dy
  // mueve el precio. Antes el arrastre solo paneaba en horizontal y el eje vertical
  // quedaba clavado al rango del dato.
  //
  // El limite horizontal deja salirse hasta MEDIA ventana a cada lado en vez de
  // clavarse en la ultima barra: sin eso no se puede mirar el borde de los datos con
  // aire alrededor.
  const S = serieG(), r = ev.currentTarget.getBoundingClientRect();
  const cv = ev.currentTarget;
  arrastrando = true; cv.style.cursor = "grabbing";
  const x0 = ev.clientX, y0 = ev.clientY;
  const v0 = { a: gVista.a, b: gVista.b }, span = v0.b - v0.a;
  // Si la escala venia en automatica, el primer arrastre vertical la fija en el rango
  // que se estaba viendo, para que el paneo arranque justo donde esta el ojo.
  const e0 = gEscala ? { k: gEscala.k, c: gEscala.c }
                     : { k: 1, c: (gEje_area.lo + gEje_area.hi) / 2 };
  const alto0 = gEje_area.hi - gEje_area.lo, H0 = gEje_area.H;
  // TOPE HORIZONTAL: el desplazamiento termina cuando la ultima barra llega al BORDE
  // del area de dibujo, no media pantalla despues.
  //
  // Antes la holgura era media ventana a cada lado, asi que al llegar al tope el
  // precio quedaba terminando en la mitad del chart con el resto vacio -- que es
  // exactamente lo que Nico mostro ("100 de 1440" con mil pixeles en blanco). El aire
  // a la derecha ya lo da `GAP_DER` (156 px), que es espacio de LAYOUT y no de scroll:
  // por eso no hace falta holgura de indices encima.
  const mover = e => {
    const dx = Math.round((e.clientX - x0) / r.width * span);
    let a = v0.a - dx, b = v0.b - dx;
    if (a < 0) { b -= a; a = 0; }
    if (b > S.n - 1) { a -= (b - (S.n - 1)); b = S.n - 1; }
    gVista = { a: Math.max(0, a), b: Math.min(S.n - 1, b) };
    // Signo, derivado y no adivinado. `Y(p) = pad.t + H - (p - lo)/(hi - lo) * H`, o
    // sea que la pantalla crece hacia ABAJO y el precio hacia ARRIBA. Para que un
    // precio P se dibuje `dy` pixeles mas abajo hace falta que `Y(P)` aumente, y eso
    // exige que `lo` aumente: el centro SUBE cuando el mouse baja.
    //
    // Estaba al reves --restaba-- y el contenido se iba para arriba al arrastrar hacia
    // abajo. El error era mio en la derivacion, no en el gesto.
    const dy = (e.clientY - y0) / H0 * alto0;
    gEscala = { k: e0.k, c: e0.c + dy };
    pintarG();
  };
  const soltar = () => {
    arrastrando = false; cv.style.cursor = "crosshair";
    removeEventListener("mousemove", mover); removeEventListener("mouseup", soltar);
  };
  addEventListener("mousemove", mover); addEventListener("mouseup", soltar);
}

// --- pestañas --------------------------------------------------------------
let tabG = false;
function tab(g) {
  tabG = g;
  document.querySelector("#vCorr").classList.toggle("on", !g);
  document.querySelector("#vGraf").classList.toggle("on", g);
  document.querySelector("#tabCorr").classList.toggle("on", !g);
  document.querySelector("#tabGraf").classList.toggle("on", g);
  if (g) { if (!B) iniGrafico(); else pintarG(); }
  else if (typeof dibujar === "function") dibujar();
}
document.querySelector("#tabCorr").addEventListener("click", () => tab(false));
document.querySelector("#tabGraf").addEventListener("click", () => tab(true));
addEventListener("resize", () => { if (tabG) pintarG(); });

document.querySelector("#btnInd").addEventListener("click", () => {
  if (typeof abrirPanelInd === "function") abrirPanelInd();
});
