(() => {
  const $ = (id) => document.getElementById(id);
  const wsDot = $("ws-dot");
  const wsStatus = $("ws-status");
  const signalCount = $("signal-count");
  const signalsList = $("signals-list");
  const symbolsList = $("symbols-list");
  const filterSymbol = $("filter-symbol");
  const filterAction = $("filter-action");

  const signals = [];
  let count = 0;

  function setStatus(state, text) {
    wsDot.className = "dot " + state;
    wsStatus.textContent = text;
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString("he-IL", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function renderSignal(sig) {
    if (filterSymbol.value && sig.symbol !== filterSymbol.value) return null;
    if (filterAction.value && sig.action !== filterAction.value) return null;

    const el = document.createElement("div");
    el.className = "signal " + sig.action.toLowerCase();
    el.dataset.symbol = sig.symbol;
    el.dataset.action = sig.action;

    const componentsHtml = (sig.components || []).map(
      (c) => `<div>• <b>${c.name}</b>: ${c.reason}</div>`
    ).join("");

    el.innerHTML = `
      <div class="badge">${sig.action}</div>
      <div class="body">
        <div class="head">
          <span class="symbol">${sig.symbol}</span>
          <span class="score">score ${sig.score?.toFixed(2) ?? "—"}</span>
          <span class="agree">${sig.agreeing}/${sig.total_active} agree · ${sig.interval}</span>
        </div>
        ${sig.narration ? `<div class="narration">${sig.narration}</div>` : ""}
        <div class="components">${componentsHtml}</div>
      </div>
      <div class="time">${formatTime(sig.created_at)}</div>
    `;
    return el;
  }

  function addSignal(sig, prepend = true) {
    signals.push(sig);
    count = signals.length;
    signalCount.textContent = `${count} signals`;

    const el = renderSignal(sig);
    if (!el) return;

    if (signalsList.querySelector(".empty")) signalsList.innerHTML = "";

    if (prepend) signalsList.prepend(el);
    else signalsList.append(el);

    while (signalsList.children.length > 200) {
      signalsList.removeChild(signalsList.lastChild);
    }
  }

  function rerender() {
    signalsList.innerHTML = "";
    const filtered = signals.slice().reverse();
    if (filtered.length === 0) {
      signalsList.innerHTML = '<div class="empty">אין signals עדיין. מחכים לטריגר…</div>';
      return;
    }
    for (const sig of filtered) {
      const el = renderSignal(sig);
      if (el) signalsList.append(el);
    }
  }

  filterSymbol.addEventListener("change", rerender);
  filterAction.addEventListener("change", rerender);

  async function loadSymbols() {
    try {
      const res = await fetch("/api/symbols");
      const symbols = await res.json();

      symbolsList.innerHTML = "";
      filterSymbol.innerHTML = '<option value="">All symbols</option>';

      for (const s of symbols) {
        const card = document.createElement("div");
        card.className = "symbol-card";
        const inds = s.indicators.map((i) => `<span class="ind-chip">${i.name}</span>`).join("");
        card.innerHTML = `
          <div class="symbol">${s.symbol} <span style="color:#666;font-size:12px;font-weight:400">@ ${s.interval}</span></div>
          <div class="indicators">${inds}</div>
        `;
        symbolsList.append(card);

        const opt = document.createElement("option");
        opt.value = s.symbol;
        opt.textContent = s.symbol;
        filterSymbol.append(opt);
      }
    } catch (e) {
      console.error("failed to load symbols", e);
    }
  }

  function connect() {
    setStatus("connecting", "Connecting…");
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${proto}//${location.host}/ws`);

    ws.onopen = () => {
      setStatus("connected", "Live");
    };

    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }

      if (msg.type === "snapshot") {
        signals.length = 0;
        for (const s of (msg.signals || []).slice().reverse()) signals.push(s);
        rerender();
        count = signals.length;
        signalCount.textContent = `${count} signals`;
      } else if (msg.type === "signal") {
        addSignal(msg.signal, true);
      }
      // ping → ignore
    };

    ws.onclose = () => {
      setStatus("disconnected", "Disconnected — reconnecting…");
      setTimeout(connect, 2000 + Math.random() * 2000);
    };

    ws.onerror = (e) => {
      console.warn("ws error", e);
      ws.close();
    };
  }

  loadSymbols();
  rerender();
  connect();
})();
