// ===========================================================================
// PANEL DE INDICADORES
//
// El formulario NO esta escrito a mano: se genera desde `PARAM_SPEC`, que es el
// espacio parametrico DECLARADO de cada kernel (F6.1). Si un kernel agrega o
// cambia un parametro, el formulario cambia solo -- no puede quedar desfasado de
// lo que el kernel realmente acepta.
//
// Y el indicador que se dibuja ES el que mide el research: lo ejecuta
// `tools/visor_server.py` llamando al mismo `run()` de
// `edgelab/bridge/indicators/`. Reimplementarlo en JS habria sido un segundo
// implementador -- y el que diverge seria el que se mira.
//
// Sin MAE/MFE, sin P&L, sin holdout.
// ===========================================================================
let IND = null, INDsel = null, INDparams = {}, OVERLAYS = [];

function abrirPanelInd() {
  const p = document.querySelector("#panelInd");
  p.classList.toggle("on");
  if (p.classList.contains("on") && !IND) cargarCatalogo();
}

function cargarCatalogo() {
  const cont = document.querySelector("#listaInd");
  cont.innerHTML = '<div style="padding:10px;color:var(--dim)">cargando…</div>';
  fetch("/api/indicadores")
    .then(r => r.json())
    .then(d => { IND = d.indicadores; pintarLista(); })
    .catch(() => {
      // Estado honesto: sin backend no hay indicadores, y se dice por que.
      cont.innerHTML =
        '<div class="vacio" style="height:auto;padding:18px 12px"><div>' +
        "<h2>Backend apagado</h2><p>Los indicadores son kernels de Python: para " +
        "cambiarles parámetros hay que <b>ejecutarlos</b>. Reimplementarlos en el " +
        "navegador seria un segundo implementador del mismo objeto.<br><br>" +
        "Levantá el visor con:<br><code>python tools/visor_server.py</code></p></div></div>";
    });
}

function pintarLista() {
  const cont = document.querySelector("#listaInd");
  cont.innerHTML = Object.entries(IND).map(([n, v]) => {
    const off = !v.disponible;
    return '<div class="ind ' + (off ? "off" : "") + '" data-ind="' + n + '">' +
      '<div class="ind-h"><b>' + n + "</b>" +
      '<span class="chip">' + v.driven + "</span>" +
      (off ? '<span class="chip warn">no cableado</span>' : "") + "</div>" +
      (off && v.motivo ? '<div class="ind-m">' + v.motivo + "</div>" : "") + "</div>";
  }).join("");
  cont.querySelectorAll(".ind:not(.off)").forEach(el =>
    el.addEventListener("click", () => elegirInd(el.dataset.ind)));
}

function elegirInd(n) {
  INDsel = n;
  INDparams = { ...IND[n].defaults };
  document.querySelectorAll(".ind").forEach(e =>
    e.classList.toggle("sel", e.dataset.ind === n));
  pintarParams();
}

function pintarParams() {
  const spec = IND[INDsel].params, cont = document.querySelector("#formInd");
  const campos = Object.entries(spec).map(([k, s]) => {
    const v = INDparams[k];
    let control;
    if (s.type === "bool") {
      control = '<input type="checkbox" data-k="' + k + '"' + (v ? " checked" : "") + ">";
    } else if (s.values || s.choices) {
      const ops = (s.values || s.choices);
      control = '<select data-k="' + k + '">' + ops.map(o =>
        '<option' + (o === v ? " selected" : "") + ">" + o + "</option>").join("") + "</select>";
    } else {
      control = '<input type="number" data-k="' + k + '" value="' + v + '"' +
        (s.min !== undefined ? ' min="' + s.min + '"' : "") +
        (s.max !== undefined ? ' max="' + s.max + '"' : "") +
        (s.type === "float" ? ' step="any"' : ' step="1"') + ">";
    }
    // `class` y `branches` vienen del PARAM_SPEC: dicen si el parametro obliga a
    // recomputar y que rama toca. Se muestran porque son parte del contrato.
    return '<label class="campo"><span title="' + (s.branches || []).join(", ") + '">' +
      k + '<i>' + (s.class || "") + "</i></span>" + control + "</label>";
  }).join("");
  cont.innerHTML = campos +
    '<div class="acciones"><button id="btnAplicar">aplicar y dibujar</button>' +
    '<button id="btnReset">volver a defaults</button>' +
    '<button id="btnQuitar">quitar del gráfico</button></div>' +
    '<div id="estadoInd" class="ind-m"></div>';

  cont.querySelectorAll("[data-k]").forEach(el => el.addEventListener("change", e => {
    const k = e.target.dataset.k, s = spec[k];
    INDparams[k] = s.type === "bool" ? e.target.checked
      : (s.type === "int" ? parseInt(e.target.value, 10)
        : (s.type === "float" ? parseFloat(e.target.value) : e.target.value));
  }));
  document.querySelector("#btnAplicar").addEventListener("click", aplicarInd);
  document.querySelector("#btnReset").addEventListener("click", () => {
    INDparams = { ...IND[INDsel].defaults }; pintarParams();
  });
  document.querySelector("#btnQuitar").addEventListener("click", () => {
    OVERLAYS = OVERLAYS.filter(o => o.indicador !== INDsel);
    document.querySelector("#estadoInd").textContent = "quitado del gráfico";
    if (typeof pintarG === "function") pintarG();
  });
}

function aplicarInd() {
  const est = document.querySelector("#estadoInd");
  est.textContent = "corriendo el kernel…";
  fetch("/api/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      indicador: INDsel, params: INDparams,
      instrumento: (window.BARRAS && window.BARRAS.instrumento) || "6E", sesiones: 2
    })
  }).then(r => r.json()).then(d => {
    if (!d.ok) { est.textContent = "error: " + d.error; return; }
    OVERLAYS = OVERLAYS.filter(o => o.indicador !== INDsel);
    OVERLAYS.push({ indicador: INDsel, zonas: d.zonas });
    est.textContent = d.n_zonas + " zonas · " + d.n_eventos + " eventos";
    if (typeof pintarG === "function") pintarG();
  }).catch(e => { est.textContent = "sin backend: " + e; });
}

// --- dibujo de las zonas sobre el chart -------------------------------------
// Se llama desde `pintarG()`. Las coordenadas de precio vienen en TICKS ENTEROS,
// igual que las devuelve el kernel: no se convierte a float para dibujar.
function dibujarOverlays(g, X, Y, pad, W, ts_de) {
  if (!OVERLAYS.length) return;
  const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  OVERLAYS.forEach(ov => {
    ov.zonas.forEach(z => {
      // `top_t`/`bottom_t` en ticks enteros los calcula el servidor: la pagina no
      // hace aritmetica de unidades.
      if (z.top_t == null || z.bottom_t == null) return;
      const y1 = Y(Math.max(z.top_t, z.bottom_t)), y2 = Y(Math.min(z.top_t, z.bottom_t));
      const activa = z.state === "ACTIVE";
      const col = (z.kind || "").indexOf("support") === 0 ? cssv("--ok") : cssv("--err");
      const x0 = ts_de(z.created_ms), x1 = z.ended_ms ? ts_de(z.ended_ms) : pad.l + W;
      if (x1 < pad.l || x0 > pad.l + W) return;
      g.globalAlpha = activa ? 0.18 : 0.07;
      g.fillStyle = col;
      g.fillRect(Math.max(pad.l, x0), y1, Math.min(pad.l + W, x1) - Math.max(pad.l, x0),
        Math.max(1, y2 - y1));
      g.globalAlpha = activa ? 0.85 : 0.35;
      g.strokeStyle = col; g.lineWidth = 1;
      g.strokeRect(Math.max(pad.l, x0), y1,
        Math.min(pad.l + W, x1) - Math.max(pad.l, x0), Math.max(1, y2 - y1));
      g.globalAlpha = 1;
    });
  });
}
