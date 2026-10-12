/* Australian Data Centre Atlas — application logic (vanilla JS, Leaflet, Chart.js). */
(() => {
  "use strict";
  const STAGES = ["Operational", "Under Construction", "Approved", "Planning", "Withdrawn"];
  const DEFAULT_OFF_STAGES = ["Withdrawn"];   // shown only when the user ticks them
  const STAGE_VAR = { "Operational": "--stage-operational", "Under Construction": "--stage-construction", "Approved": "--stage-approved", "Planning": "--stage-planning", "Withdrawn": "--stage-withdrawn" };
  const SERIES = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6", "--s7", "--s8"];
  const JUR_ORDER = ["FED", "NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"];
  const INFRA_LAYERS = [
    { key: "Terminal Station/Substation (≥220kV)", en: "Terminal stations ≥220 kV (key)", zh: "关键终端站 ≥220 kV", color: "--s2", shape: "sq" },
    { key: "Terminal Station/Substation (132/110/66kV)", en: "Zone substations 132/110 kV (key)", zh: "关键区域变电站 132/110 kV", color: "--s7", shape: "sq" },
    { key: "Power Station (major)", en: "Major power stations", zh: "主要电站", color: "--s8", shape: "sq" },
    { key: "Internet Exchange / Carrier Hotel", en: "Internet exchanges / carrier hotels", zh: "互联网交换中心 / 运营商枢纽", color: "--s3", shape: "dot" },
    { key: "Cable Landing Station", en: "Submarine cable landing stations", zh: "海缆登陆站", color: "--s4", shape: "dot" },
    { key: "Telstra Exchange (major)", en: "Major Telstra exchanges", zh: "主要 Telstra 交换局", color: "--s5", shape: "dot" },
    { key: "NBN POI", en: "NBN POIs (key)", zh: "NBN 关键互联点", color: "--s6", shape: "dot" },
    { key: "__nbn_all", en: "NBN POIs (all 121)", zh: "NBN 全部 121 个互联点", color: "--s6", shape: "dot", off: true },
    { key: "__lines", en: "tl_lines", zh: "tl_lines", color: "--s2", shape: "line", geo: "transmission_lines.geojson", off: true },
    { key: "__subs", en: "tl_subs", zh: "tl_subs", color: "--s2", shape: "sq", geo: "substations.geojson", off: true },
    { key: "__cables", en: "tl_cables", zh: "tl_cables", color: "--s4", shape: "line", geo: "submarine_cables.geojson", off: true },
  ];

  const D = {};            // loaded data
  let lang = localStorage.getItem("adc_lang") || (navigator.language.startsWith("zh") ? "zh" : "en");
  const charts = {};
  let map, facLayer, infraGroups = {}, geoCache = {}, sortState = { key: "it_load_mw_planned", asc: false };

  // ---------- helpers
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const t = (k) => (I18N[lang][k] ?? I18N.en[k] ?? k);
  const L2 = (o, f) => (o ? (o[`${f}_${lang}`] || o[`${f}_en`] || o[`${f}_zh`] || "") : "");
  const cssVar = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const stageColor = (s) => cssVar(STAGE_VAR[s] || "--muted");
  const fmt = (n, d = 0) => (n == null || isNaN(n) ? "—" : Number(n).toLocaleString(lang === "zh" ? "zh-CN" : "en-AU", { maximumFractionDigits: d }));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const linkList = (arr) => (arr || []).map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\/(www\.)?/, "").slice(0, 48))}${u.length > 56 ? "…" : ""}</a>`).join(" · ");
  // "lead sentence\n- point\n- point" -> <p> + <ul>; plain text stays a paragraph
  const rich = (str) => {
    const lines = String(str || "").split("\n").map((x) => x.trim()).filter(Boolean);
    if (!lines.length) return "";
    const lead = [], items = [];
    for (const l of lines) {
      if (l.startsWith("- ") || l.startsWith("• ")) items.push(l.slice(2));
      else if (items.length) items[items.length - 1] += " " + l;
      else lead.push(l);
    }
    return (lead.length ? `<p>${esc(lead.join(" "))}</p>` : "") +
           (items.length ? `<ul class="dots">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "");
  };
  const stageBadge = (s) => `<span class="stage-badge" style="background:${stageColor(s)}">${esc(t("stage_" + s))}</span>`;
  const isDark = () => matchMedia("(prefers-color-scheme: dark)").matches;

  async function loadJSON(name, optional = false) {
    try {
      const r = await fetch(`data/${name}?v=${Date.now() >> 16}`);
      if (!r.ok) throw new Error(r.status);
      return await r.json();
    } catch (e) {
      if (optional) return null;
      throw new Error(`Failed to load data/${name}: ${e.message}`);
    }
  }

  // ---------- language
  function applyLang() {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
    $$(".lang-toggle button").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
    $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    $$("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
    $("#siteTitle").textContent = L2(D.meta, "site_title") || "Australian Data Centre Atlas";
    document.title = $("#siteTitle").textContent;
    $("#siteSubtitle").textContent = L2(D.meta, "site_subtitle");
    $("#nationalSummary").innerHTML = rich(L2(D.meta, "national_summary"));
    $("#footerOrg").textContent = `${D.meta.organisation || ""} · ${new Date().getFullYear()}`;
    $("#disclaimer").textContent = L2(D.meta, "disclaimer");
    $("#dataAsOf").textContent = D.meta.data_as_of || "—";
    Chart.defaults.color = cssVar("--text-2");
    Chart.defaults.borderColor = cssVar("--border");
    renderOverview(); renderStakeholders(); renderRegulation(); renderNews(); renderData();
    populateFilters(); renderMapLegend(); renderLayerToggles(); applyFilters();
    if (facLayer) facLayer.eachLayer((m) => m.getPopup() && m.setPopupContent(popupHtml(m.options.fac)));
    const sel = $("#detailPanel").dataset.fid;
    if (sel) showDetail(D.facById[sel]);
  }

  // ---------- charts (thin marks, one axis, fixed hue order, hover tooltips)
  function mkChart(id, cfg) {
    if (charts[id]) charts[id].destroy();
    const ctx = $("#" + id);
    if (!ctx) return;
    cfg.options = Object.assign({ responsive: true, maintainAspectRatio: false, animation: false }, cfg.options || {});
    cfg.options.plugins = Object.assign({ legend: { labels: { boxWidth: 10, boxHeight: 10, usePointStyle: true } }, tooltip: { mode: "nearest", intersect: true } }, cfg.options.plugins || {});
    charts[id] = new Chart(ctx, cfg);
  }
  const grid = { color: cssVar("--border"), drawTicks: false };
  const barOpts = (horizontal, extra = {}) => Object.assign({
    indexAxis: horizontal ? "y" : "x",
    scales: {
      x: { grid: horizontal ? grid : { display: false }, border: { display: false }, ticks: { precision: 0 }, stacked: !!extra.stacked },
      y: { grid: horizontal ? { display: false } : grid, border: { display: false }, stacked: !!extra.stacked },
    },
    datasets: { bar: { borderRadius: 3, borderSkipped: "start", barPercentage: 0.7, categoryPercentage: 0.8, borderWidth: 0 } },
  }, extra.options || {});

  function renderOverview() {
    // KPIs from Market sheet + tracked totals
    // KPI tiles: Market rows flagged kpi=TRUE (ordered by kpi_order) plus the three computed from tracked data.
    const fullbuild = Object.values(D.stats.by_state).reduce((a, s) => a + s.fullbuild_mw, 0);
    const kpis = D.market.filter((m) => m.kpi).map((m) => ({ v: m.value, u: m.unit, l: L2(m, "label"), s: `${m.notes ? m.notes + " · " : ""}${m.source || ""}`, o: m.kpi_order }));
    kpis.push({ v: D.stats.tracked_operational_mw_total, u: "MW", l: t("kpi_tracked_op"), s: t("kpi_tracked_op_sub"), o: 2 });
    kpis.push({ v: Math.round(fullbuild), u: "MW", l: t("kpi_tracked"), s: `${t("kpi_tracked_sub")} · ${t("excl_other_basis").replace("{mw}", fmt(D.stats.other_basis_mw_total))}`, o: 6 });
    kpis.push({ v: D.stats.facility_count, u: "", l: t("kpi_count"), s: t("kpi_count_sub"), o: 9 });
    kpis.sort((a, b) => (a.o ?? 99) - (b.o ?? 99));
    $("#kpiRow").innerHTML = kpis.filter((k) => k.v != null).slice(0, 8).map((k) => {
      let v = k.v, u = k.u;
      if (u === "MW" && v >= 1000) { v = v / 1000; u = "GW"; }
      return `<div class="kpi"><div class="v">${fmt(v, u === "GW" ? 1 : 0)}<small>${esc(u)}</small></div><div class="l">${esc(k.l)}</div><div class="s">${esc(k.s)}</div></div>`;
    }).join("");

    const states = Object.keys(D.stats.by_state).sort((a, b) => D.stats.by_state[b].fullbuild_mw - D.stats.by_state[a].fullbuild_mw);
    mkChart("chStateStage", {
      type: "bar",
      data: { labels: states, datasets: STAGES.map((s) => ({
        label: t("stage_" + s),
        data: states.map((st) => Math.round(D.stats.by_state[st].mw_by_stage[s])),
        counts: states.map((st) => D.stats.by_state[st].by_stage[s]),
        backgroundColor: stageColor(s) })) },
      options: barOpts(false, { stacked: true, options: { plugins: { tooltip: { callbacks: {
        label: (c) => `${c.dataset.label}: ${fmt(c.raw)} MW · ${c.dataset.counts[c.dataIndex]} ${t("count_label")}` } } } } }),
    });

    const fb = (f) => ((f.capacity_basis || "IT load") !== "IT load" ? 0 : (f.it_load_mw_planned || f.it_load_mw_operational || 0));
    const top = [...D.facilities].sort((a, b) => fb(b) - fb(a)).slice(0, 12);
    mkChart("chTopSites", {
      type: "bar",
      data: { labels: top.map((f) => f.name.length > 34 ? f.name.slice(0, 33) + "…" : f.name),
              datasets: [{ label: "MW", data: top.map(fb), backgroundColor: top.map((f) => stageColor(f.stage)) }] },
      options: barOpts(true, { options: { plugins: { legend: { display: false }, tooltip: { callbacks: {
        title: (c) => top[c[0].dataIndex].name,
        label: (c) => `${fmt(c.raw)} MW · ${t("stage_" + top[c.dataIndex].stage)} · ${top[c.dataIndex].operator}` } } } } }),
    });

    $("#topSitesLegend").innerHTML = STAGES.map((st) => `<span><i class="sw" style="background:${stageColor(st)}"></i>${esc(t("stage_" + st))}</span>`).join("");

    const opStates = states.filter((s) => D.stats.by_state[s].operational_mw > 0)
      .sort((a, b) => D.stats.by_state[b].operational_mw - D.stats.by_state[a].operational_mw);
    mkChart("chStateMw", {
      type: "bar",
      data: { labels: opStates, datasets: [{ label: t("mw_operational"),
        data: opStates.map((s) => Math.round(D.stats.by_state[s].operational_mw)), backgroundColor: cssVar("--s1") }] },
      options: barOpts(false, { options: { plugins: { legend: { display: false } } } }),
    });

    const moves = D.operators.flatMap((o) => o.latest_moves.map((m) => ({ ...m, op: o.name }))).sort((a, b) => String(b.date).localeCompare(String(a.date))).slice(0, 12);
    $("#recentMoves").innerHTML = moves.map((m) => `<li><span class="d">${esc(m.date)}</span><span><span class="op">${esc(m.op)}</span>${m.source ? `<a href="${esc(m.source)}" target="_blank" rel="noopener">${esc(L2(m, "headline"))}</a>` : esc(L2(m, "headline"))}</span></li>`).join("");
  }

  // ---------- stakeholders
  function renderStakeholders() {
    const ops = D.stats.operators;
    const withOp = ops.filter((o) => o.operational_mw).sort((a, b) => b.operational_mw - a.operational_mw);
    const top = withOp.slice(0, 8), rest = withOp.slice(8).reduce((a, o) => a + o.operational_mw, 0);
    const labels = top.map((o) => o.name).concat(rest ? [t("other")] : []);
    const vals = top.map((o) => o.share_of_tracked_operational).concat(rest ? [Math.round(1000 * rest / D.stats.tracked_operational_mw_total) / 10] : []);
    $("#shareSub").textContent = t("share_sub").replace("{total}", fmt(D.stats.tracked_operational_mw_total));
    mkChart("chShare", {
      type: "bar",
      data: { labels, datasets: [{ label: "%", data: vals, backgroundColor: labels.map((_, i) => i < top.length ? cssVar("--s1") : cssVar("--muted")) }] },
      options: barOpts(true, { options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.raw}% · ${fmt(top[c.dataIndex]?.operational_mw ?? rest)} MW (${top[c.dataIndex]?.operational_basis ?? ""})` } } }, scales: { x: { ticks: { callback: (v) => v + "%" } } } } }),
    });
    const named = (o) => !/^undisclosed/i.test(o.name || "");
    const pipe = ops.filter((o) => o.pipeline_mw && named(o)).sort((a, b) => b.pipeline_mw - a.pipeline_mw).slice(0, 14);
    mkChart("chPipeline", {
      type: "bar",
      data: { labels: pipe.map((o) => o.name), datasets: [{ label: "MW", data: pipe.map((o) => Math.round(o.pipeline_mw)), backgroundColor: pipe.map((o) => o.pipeline_basis === "operator-reported" ? cssVar("--s2") : cssVar("--muted")) }] },
      options: barOpts(true, { options: { plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${fmt(c.raw)} MW (${pipe[c.dataIndex].pipeline_basis})` } } } } }),
    });
    const inv = ops.filter((o) => o.announced_investment_aud_bn).sort((a, b) => b.announced_investment_aud_bn - a.announced_investment_aud_bn).slice(0, 12);
    mkChart("chInvest", {
      type: "bar",
      data: { labels: inv.map((o) => o.name), datasets: [{ label: "A$bn", data: inv.map((o) => o.announced_investment_aud_bn), backgroundColor: cssVar("--s3") }] },
      options: barOpts(true, { options: { plugins: { legend: { display: false } } } }),
    });
    const byMw = ops.filter((o) => o.fullbuild_mw && named(o)).sort((a, b) => b.fullbuild_mw - a.fullbuild_mw).slice(0, 12);
    mkChart("chOpStage", {
      type: "bar",
      data: { labels: byMw.map((o) => o.name), datasets: STAGES.map((s) => ({
        label: t("stage_" + s), data: byMw.map((o) => Math.round(o.mw_by_stage[s])),
        counts: byMw.map((o) => o.by_stage[s]), backgroundColor: stageColor(s) })) },
      options: barOpts(true, { stacked: true, options: { plugins: { tooltip: { callbacks: {
        label: (c) => `${c.dataset.label}: ${fmt(c.raw)} MW · ${c.dataset.counts[c.dataIndex]} ${t("count_label")}` } } } } }),
    });
    // profile cards
    const catSel = $("#opCategory");
    const cats = [...new Set(D.operators.map((o) => o.category).filter(Boolean))];
    const cur = catSel.value;
    catSel.innerHTML = `<option value="">${t("all_categories")}</option>` + cats.map((c) => `<option ${c === cur ? "selected" : ""}>${esc(c)}</option>`).join("");
    const statById = Object.fromEntries(ops.filter((o) => o.operator_id).map((o) => [o.operator_id, o]));
    const opOrder = [...D.operators].sort((a, b) => ((statById[b.operator_id] || {}).fullbuild_mw || 0) - ((statById[a.operator_id] || {}).fullbuild_mw || 0)
      || ((statById[b.operator_id] || {}).announced_investment_aud_bn || 0) - ((statById[a.operator_id] || {}).announced_investment_aud_bn || 0));
    $("#opGrid").innerHTML = opOrder.filter((o) => !catSel.value || o.category === catSel.value).map((o) => {
      const s = statById[o.operator_id] || {};
      return `<div class="op-card" data-op="${esc(o.operator_id)}"><h4>${esc(lang === "zh" && o.name_zh ? o.name_zh : o.name)}</h4><div class="cat">${esc(o.category || "")} · ${esc(o.ownership_type || "")}${o.ticker ? " · " + esc(o.ticker) : ""}</div>
        <div class="figs"><span><b>${s.operational_mw ? fmt(s.operational_mw) : "—"}</b>${t("mw_operational")}</span><span><b>${s.pipeline_mw ? fmt(s.pipeline_mw) : "—"}</b>${t("mw_pipeline")}</span><span><b>${s.fullbuild_mw ? fmt(s.fullbuild_mw) : "—"}</b>${t("fullbuild_mw")}</span></div></div>`;
    }).join("");
  }

  function openOperator(id) {
    const o = D.operators.find((x) => x.operator_id === id);
    if (!o) return;
    const s = D.stats.operators.find((x) => x.operator_id === id) || {};
    const facs = D.facilities.filter((f) => f.operator_id === id);
    $("#drawerBody").innerHTML = `
      <h2>${esc(o.name)}${o.name_zh && o.name_zh !== o.name ? ` <small>${esc(o.name_zh)}</small>` : ""}</h2>
      <p class="muted small">${esc(o.legal_name || "")} · ${esc(o.category || "")}</p>
      <div class="prose">${rich(L2(o, "background"))}</div>
      <dl class="kv">
        <dt>${t("founded")}</dt><dd>${esc(o.founded_year ?? "—")}</dd>
        <dt>${t("hq")}</dt><dd>${esc([o.hq_city, o.hq_country].filter(Boolean).join(", "))}</dd>
        <dt>${t("ownership")}</dt><dd>${esc(o.ownership_type || "—")}${o.ticker ? ` (${esc(o.ticker)})` : ""}</dd>
        <dt>${t("shareholders")}</dt><dd>${esc(o.key_shareholders || "—")}</dd>
        <dt>${t("mw_operational")}</dt><dd>${s.operational_mw ? `${fmt(s.operational_mw)} MW <small class="muted">(${esc(s.operational_basis)})</small>` : t("not_disclosed")}</dd>
        <dt>${t("mw_pipeline")}</dt><dd>${s.pipeline_mw ? `${fmt(s.pipeline_mw)} MW <small class="muted">(${esc(s.pipeline_basis)})</small>` : t("not_disclosed")}</dd>
        <dt>${t("fullbuild_mw")}</dt><dd>${s.fullbuild_mw ? `${fmt(s.fullbuild_mw)} MW` : "—"}</dd>
        <dt>${t("investment")}</dt><dd>${o.announced_investment_aud_bn ? `A$${fmt(o.announced_investment_aud_bn, 2)} bn` : "—"}</dd>
        <dt>${t("customers")}</dt><dd>${esc(o.key_customers || "—")}</dd>
        <dt>Web</dt><dd>${o.website ? `<a href="${esc(o.website)}" target="_blank" rel="noopener">${esc(o.website)}</a>` : "—"}</dd>
      </dl>
      <h3>${t("latest_moves")}</h3>
      <ul class="moves">${o.latest_moves.map((m) => `<li><span class="d">${esc(m.date)}</span><span>${m.source ? `<a href="${esc(m.source)}" target="_blank" rel="noopener">${esc(L2(m, "headline"))}</a>` : esc(L2(m, "headline"))}</span></li>`).join("") || "<li>—</li>"}</ul>
      <h3>${t("tracked_facilities")} (${facs.length})</h3>
      <ul class="facs">${facs.map((f) => `<li>${stageBadge(f.stage)} <a href="#" data-fac="${esc(f.facility_id)}">${esc(f.name)}</a> <small class="muted">${esc(f.state)}${f.it_load_mw_planned ? ` · ${fmt(f.it_load_mw_planned)} MW` : ""}</small></li>`).join("")}</ul>
      <p class="small">${t("sources_lbl")}: ${linkList(o.sources)}</p>`;
    $("#drawer").hidden = false;
  }

  // ---------- regulation
  let curJur = "NSW";
  function renderRegulation() {
    const jurs = D.reg.jurisdictions;
    $("#jurTabs").innerHTML = jurs.map((j) => `<button data-jur="${j.jurisdiction_id}" class="${j.jurisdiction_id === curJur ? "active" : ""}">${esc(j.jurisdiction_id === "FED" ? (lang === "zh" ? "联邦 / NEM" : "Federal / NEM") : j.jurisdiction_id)}</button>`).join("");
    const j = jurs.find((x) => x.jurisdiction_id === curJur) || jurs[0];
    const fed = jurs.find((x) => x.jurisdiction_id === "FED");
    const jname = (id) => { const x = jurs.find((y) => y.jurisdiction_id === id); return x ? L2(x, "name") : id; };
    $("#regMain").innerHTML = `
      <div class="card">
        <div class="reg-head"><h2>${esc(L2(j, "name"))}</h2>
          <div class="bodies"><b>${t("market")}:</b> ${esc(j.market || "")}</div>
          <div class="bodies"><b>${t("key_bodies")}:</b> ${esc(j.key_bodies || "")}</div></div>
        <div class="prose">${rich(L2(j, "overview"))}</div>
      </div>
      <div class="card">
        <ol class="stepper">${j.steps.map((s) => `
          <li class="step ${s.overlap_with.includes("FED") || (j.jurisdiction_id === "FED" && s.overlap_with.length) ? "has-fed" : ""}">
            <span class="no">${s.step_no}</span>
            <h4>${esc(L2(s, "title"))}</h4>
            <div class="meta">${s.authority ? `<span><b>${t("authority")}:</b> ${esc(s.authority)}</span>` : ""}${s.typical_duration ? `<span><b>${t("duration")}:</b> ${esc(s.typical_duration)}</span>` : ""}</div>
            <div class="prose step-detail">${rich(L2(s, "detail"))}</div>
            ${s.legal_basis ? `<p class="small"><b>${t("legal_basis")}:</b> ${esc(s.legal_basis)}</p>` : ""}
            ${s.overlap_with.length ? `<div class="overlap"><b>${t("overlaps_with")}:</b> ${s.overlap_with.map((o) => `<span class="chip ${o === "FED" ? "fed" : ""}">${esc(jname(o))}</span>`).join("")}<br>${esc(L2(s, "overlap_note"))}</div>` : ""}
            ${s.sources.length ? `<details><summary>${t("sources_lbl")}</summary><p class="small">${linkList(s.sources)}</p></details>` : ""}
          </li>`).join("")}</ol>
      </div>
      ${j.recent_changes.length ? `<div class="card"><h3>${t("recent_changes")}</h3><ul class="changes">${j.recent_changes.map((c) => `<li><span class="d">${esc(c.date)}</span>${c.source ? `<a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(L2(c, "summary"))}</a>` : esc(L2(c, "summary"))}</li>`).join("")}</ul></div>` : ""}`;
    // overlap matrix: rows = federal steps, cols = states
    if (fed) {
      const states = JUR_ORDER.filter((x) => x !== "FED" && jurs.some((y) => y.jurisdiction_id === x));
      $("#overlapMatrix").innerHTML = `<thead><tr><th>${t("fed_step")}</th>${states.map((s) => `<th class="${s === curJur ? "sorted" : ""}">${s}</th>`).join("")}</tr></thead><tbody>` +
        fed.steps.map((s) => `<tr><td title="${esc(L2(s, "detail"))}">${s.step_no}. ${esc(L2(s, "title"))}</td>${states.map((st) => {
          const hit = s.overlap_with.includes(st);   // driven purely by Reg_Steps.overlap_with on the federal rows
          return `<td>${hit ? '<span class="dot"></span>' : ""}</td>`;
        }).join("")}</tr>`).join("") + "</tbody>";
    }
    $("#overlapNotes").innerHTML = rich(L2(D.reg, "overlap_notes"));
  }

  // ---------- news
  function renderNews() {
    const n = D.news || { items: [] };
    const sSel = $("#nState"), oSel = $("#nOperator");
    const cs = sSel.value, co = oSel.value;
    sSel.innerHTML = `<option value="">${t("all_states")}</option>` + JUR_ORDER.filter((x) => x !== "FED").map((s) => `<option ${s === cs ? "selected" : ""}>${s}</option>`).join("");
    const opsInNews = [...new Set(n.items.flatMap((i) => i.operators || []))].sort();
    oSel.innerHTML = `<option value="">${t("all_operators")}</option>` + opsInNews.map((o) => `<option ${o === co ? "selected" : ""}>${esc(o)}</option>`).join("");
    const q = $("#nSearch").value.trim().toLowerCase(), lg = $("#nLang").value;
    const items = n.items.filter((i) => (!cs || (i.states || []).includes(cs)) && (!co || (i.operators || []).includes(co)) && (!lg || i.language === lg) && (!q || (i.title + " " + i.summary).toLowerCase().includes(q)));
    $("#newsMeta").textContent = n.fetched_at ? `${items.length} ${t("items")} · ${t("news_fetched")} ${n.fetched_at.slice(0, 16).replace("T", " ")} UTC` : "";
    $("#newsList").innerHTML = items.length ? items.map((i) => `<li><span class="d">${esc((i.published || "").slice(0, 10))}</span><div><a href="${esc(i.link)}" target="_blank" rel="noopener">${esc(i.title)}</a>${i.publisher ? `<span class="pub">${esc(i.publisher)}</span>` : ""}
      <div class="tags">${(i.states || []).map((s) => `<span class="chip">${s}</span>`).join("")}${(i.operators || []).map((o) => `<span class="chip">${esc(o)}</span>`).join("")}</div></div></li>`).join("")
      : `<li><span></span><span class="muted">${t("news_empty")}</span></li>`;
  }

  // ---------- data tab
  function renderData() {
    const b = D.build || {};
    $("#buildInfo").innerHTML = `<dt>Workbook</dt><dd>${esc(b.workbook || "—")}</dd><dt>Built (UTC)</dt><dd>${esc(b.built_at_utc || "—")}</dd>` +
      Object.entries(b.counts || {}).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("");
    if (b.workbook) $("#wbLink").href = `data/workbook/${b.workbook}`;
    $("#dataHow").innerHTML = lang === "zh" ? `
      <p>本站为纯静态网页，所有内容均来自 <code>data/source/</code> 下时间戳最新的 Excel 主数据表。维护流程：</p>
      <ol><li>运行 <code>python scripts/new_version.py</code>：旧表归档至 <code>data/archive/</code>，生成新的时间戳副本。</li>
      <li>在 Excel 中编辑新副本（新增设施、更新 MW、补充监管步骤、调整新闻源）。</li>
      <li><code>git commit</code> + <code>git push</code>。GitHub Actions 自动运行 <code>build_data.py</code>、<code>fetch_news.py</code>、<code>fetch_geo.py</code> 并重新发布到 GitHub Pages。</li></ol>
      <p>新闻每日自动抓取（Actions 定时任务）；输电线路等 GIS 图层每周从澳洲地球科学局刷新。详见仓库中的 <code>DEPLOY_GUIDE.md</code> 与 <code>DATA_UPDATE_GUIDE.md</code>。</p>` : `
      <p>This is a static site. Everything shown comes from the newest time-stamped Excel workbook in <code>data/source/</code>. To update:</p>
      <ol><li>Run <code>python scripts/new_version.py</code> — the current workbook is archived to <code>data/archive/</code> and a new time-stamped copy is created.</li>
      <li>Edit the new copy in Excel (add facilities, update MW, extend regulatory steps, change news sources).</li>
      <li><code>git commit</code> + <code>git push</code>. GitHub Actions runs <code>build_data.py</code>, <code>fetch_news.py</code> and <code>fetch_geo.py</code> and redeploys GitHub Pages.</li></ol>
      <p>News is polled daily by the scheduled Action; transmission/GIS layers refresh weekly from Geoscience Australia. See <code>DEPLOY_GUIDE.md</code> and <code>DATA_UPDATE_GUIDE.md</code> in the repository.</p>`;
    $("#methodology").innerHTML = lang === "zh" ? `
      <ul><li><b>容量口径：</b>MW 指 IT（关键）负载；规划文件与 AEMO 通常引用设施/并网功率（约为 IT 负载的 1.2–1.5 倍）。未披露即留空，不作估算。</li>
      <li><b>阶段：</b>在运 = 已建成并投运（含部分投运）；在建 = 已开工；已获批 = 取得规划许可但未开工；规划中 = 已公开但未获批（含 NSW IDA 加速通道项目）。</li>
      <li><b>份额：</b>“在运 IT 负载份额”以本库跟踪的运营商为分母，优先采用运营商披露数（如 NEXTDC 已建成 288 MW、CDC 550 MW 含新西兰），否则以单体披露合计代替；超大规模云商租用容量不重复计入。</li>
      <li><b>管线：</b>含已签约、在建及已公告项目，早期规划项目的落地风险很高（DC Byte 统计 21.6 GW 公告中仅 3.1 GW 已落实）。</li>
      <li><b>坐标：</b>多数为地址地理编码；部分早期项目仅精确到区域中心，标记说明中有注明。</li>
      <li><b>监管：</b>步骤依据 2026 年 9 月的公开规则整理，部分费用/门槛为待落地提案，正文中已作说明。</li></ul>` : `
      <ul><li><b>Capacity basis:</b> MW means IT (critical) load. Planning documents and AEMO usually quote facility / grid connection power (≈1.2–1.5× IT load). Undisclosed values are left blank, never estimated.</li>
      <li><b>Stages:</b> Operational = built and commissioned (at least partly); Under Construction = works started; Approved = planning consent granted, works not started; Planning = publicly announced without consent (including NSW IDA fast-track endorsements).</li>
      <li><b>Share:</b> "share of tracked operational IT load" uses tracked operators as the denominator, preferring operator-reported figures (e.g. NEXTDC built 288 MW; CDC 550 MW includes NZ) and falling back to disclosed per-site sums. Hyperscaler leased capacity is not double-counted.</li>
      <li><b>Pipeline:</b> includes contracted, under-construction and announced projects; early-stage announcements carry high execution risk (DC Byte: 21.6 GW announced, 3.1 GW committed).</li>
      <li><b>Coordinates:</b> mostly geocoded from street addresses; some early-stage projects are placed at a suburb centroid and say so in their notes.</li>
      <li><b>Regulation:</b> steps reflect public rules as at September 2026; several fees/thresholds are proposals awaiting regulations and are flagged in the text.</li></ul>`;
    $("#sourcesList").innerHTML = `<ul>
      <li>Facilities & operators: operator websites, ASX announcements, NSW Planning Portal, Victorian/Queensland planning registers, AFR, Data Center Dynamics, iTnews, W.Media, Capacity Media, Baxtel, Cloudscene, RenewMap — per-row URLs are in the workbook's <code>sources</code> columns.</li>
      <li>Market totals: Data Centres Australia / DC Byte Forecast Report (Apr 2026), AEMO Quarterly Energy Dynamics Q1 2026, Cushman & Wakefield APAC Data Centre Update H1 2026, CommBank economics (Aug 2026).</li>
      <li>Transmission lines, substations, power stations: <a href="https://digital.atlas.gov.au/datasets/digitalatlas::power-lines/about" target="_blank" rel="noopener">Geoscience Australia — Electricity Infrastructure</a> (CC BY 4.0). AEMO publishes no GIS transmission layer; its ISP maps and connection-point lists are referenced in <code>docs/infra_sources.md</code>.</li>
      <li>Fibre: NBN POI list via <a href="https://nbn.rinseout.org/" target="_blank" rel="noopener">nbn.rinseout.org</a> (community geocodes — verify), Geoscience Australia Telephone Exchanges layer, IX Australia and Megaport public location lists, TeleGeography Submarine Cable Map public API (display only).</li>
      <li>Regulation: AEMC, AEMO, AER, National Electricity Rules, Transgrid / Ausgrid / Endeavour / AusNet / VicGrid / Powerlink / Energex / Western Power / ElectraNet / TasNetworks / Power and Water Corporation, state planning departments — URLs per step in <code>Reg_Steps</code>.</li>
      <li>Basemap: © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors, © <a href="https://carto.com/attributions" target="_blank" rel="noopener">CARTO</a>.</li></ul>`;
  }

  // ---------- map
  function initMap() {
    map = L.map("map", { zoomSnap: 0.25, worldCopyJump: false }).setView([D.meta.map_center_lat || -30.5, D.meta.map_center_lng || 141.5], D.meta.map_zoom || 4.4);
    const tiles = (dark) => L.tileLayer(`https://{s}.basemaps.cartocdn.com/${dark ? "dark_all" : "light_all"}/{z}/{x}/{y}{r}.png`, { maxZoom: 19, subdomains: "abcd", attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' });
    let base = tiles(isDark()).addTo(map);
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => { map.removeLayer(base); base = tiles(e.matches).addTo(map); });
    map.createPane("facilities").style.zIndex = 650;   // facilities always sit above infrastructure markers
    facLayer = L.layerGroup().addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
  }
  const radiusFor = (mw) => Math.max(5, Math.min(22, 4 + Math.sqrt(mw || 5) * 0.9));
  function popupHtml(f) {
    return `<b>${esc(f.name)}</b><br>${stageBadge(f.stage)} <span class="muted">${esc(f.type || "")}</span><br>
      ${t("operator")}: <b>${esc(f.operator)}</b><br>${t("it_load")}: ${f.it_load_mw_operational ? fmt(f.it_load_mw_operational) + " " + t("operational") : ""}${f.it_load_mw_operational && f.it_load_mw_planned ? " / " : ""}${f.it_load_mw_planned ? fmt(f.it_load_mw_planned) + " " + t("planned") : ""}${!f.it_load_mw_operational && !f.it_load_mw_planned ? t("not_disclosed") : ""}${f.capacity_basis && f.capacity_basis !== "IT load" ? `<br><i>${esc(t("basis_note"))}: ${esc(f.capacity_basis)}</i>` : ""}`;
  }
  function facilityMarker(f) {
    const m = L.circleMarker([f.lat, f.lng], { pane: "facilities", radius: radiusFor(f.it_load_mw_planned || f.it_load_mw_operational), color: "#fff", weight: 1.5, fillColor: stageColor(f.stage), fillOpacity: 0.85, fac: f });
    m.bindPopup(popupHtml(f));
    m.on("click", () => showDetail(f));
    return m;
  }
  function showDetail(f) {
    if (!f) return;
    const p = $("#detailPanel"); p.dataset.fid = f.facility_id;
    const op = D.operators.find((o) => o.operator_id === f.operator_id);
    p.innerHTML = `<h3>${esc(f.name)}</h3>${stageBadge(f.stage)} <span class="chip">${esc(f.type || "")}</span> <span class="chip">${esc(f.state)}</span>
      <p>${esc(L2(f, "description"))}</p>
      <dl>
        <dt>${t("operator")}</dt><dd>${op ? `<a href="#" data-op="${esc(op.operator_id)}">${esc(f.operator)}</a>` : esc(f.operator)}</dd>
        <dt>${t("owner")}</dt><dd>${esc(f.owner || "—")}</dd>
        <dt>${t("it_load")}${f.capacity_basis && f.capacity_basis !== "IT load" ? ` <span class="chip warn">${esc(f.capacity_basis)}</span>` : ""}</dt><dd>${f.it_load_mw_operational != null ? `${fmt(f.it_load_mw_operational)} ${t("operational")}` : `<span class="muted">${t("operational")}: ${t("not_disclosed")}</span>`}<br>${f.it_load_mw_planned != null ? `${fmt(f.it_load_mw_planned)} ${t("planned")}` : `<span class="muted">${t("planned")}: ${t("not_disclosed")}</span>`}</dd>
        <dt>${t("year")}</dt><dd>${esc(f.year_announced ?? "—")} / ${esc(f.year_commissioned ?? "—")}</dd>
        <dt>${t("tenants")}</dt><dd>${esc(f.key_tenants || "—")}</dd>
        ${f.capex_aud_m ? `<dt>${t("capex")}</dt><dd>A$${fmt(f.capex_aud_m)} m</dd>` : ""}${f.site_area_ha ? `<dt>${t("site_area")}</dt><dd>${fmt(f.site_area_ha, 1)} ha</dd>` : ""}
        <dt>${t("power")}</dt><dd>${esc(f.power_source_notes || "—")}</dd>
        ${f.cooling ? `<dt>${t("cooling")}</dt><dd>${esc(f.cooling)}</dd>` : ""}${f.certifications ? `<dt>${t("certs")}</dt><dd>${esc(f.certifications)}</dd>` : ""}
        <dt>${t("address")}</dt><dd>${esc(f.address || f.city_suburb || "—")}</dd>
        <dt>${t("sources_lbl")}</dt><dd>${linkList(f.sources)}<br><small class="muted">${esc(f.last_verified || "")}</small></dd>
      </dl>`;
  }
  function populateFilters() {
    const keep = (sel, vals, allLabel) => { const cur = sel.value; sel.innerHTML = `<option value="">${allLabel}</option>` + vals.map((v) => `<option ${v === cur ? "selected" : ""}>${esc(v)}</option>`).join(""); };
    keep($("#fState"), JUR_ORDER.filter((s) => s !== "FED" && D.facilities.some((f) => f.state === s)), t("all"));
    keep($("#fOperator"), [...new Set(D.facilities.map((f) => f.operator))].sort(), t("all"));
    keep($("#fType"), [...new Set(D.facilities.map((f) => f.type).filter(Boolean))].sort(), t("all"));
    const st = $("#stageToggles");
    if (!st.children.length) st.innerHTML = STAGES.map((s) => `<label><input type="checkbox" data-stage="${s}" ${DEFAULT_OFF_STAGES.includes(s) ? "" : "checked"}><span class="sw" style="background:${stageColor(s)}"></span><span data-stage-label="${s}"></span></label>`).join("");
    $$("[data-stage-label]", st).forEach((el) => { el.textContent = `${t("stage_" + el.dataset.stageLabel)} (${D.stats.by_stage[el.dataset.stageLabel].count})`; });
  }
  function currentFacilities() {
    const q = $("#fSearch").value.trim().toLowerCase(), st = $("#fState").value, op = $("#fOperator").value, ty = $("#fType").value, mn = parseFloat($("#fMinMw").value) || 0;
    const stages = $$("#stageToggles input").filter((c) => c.checked).map((c) => c.dataset.stage);
    return D.facilities.filter((f) => stages.includes(f.stage) && (!st || f.state === st) && (!op || f.operator === op) && (!ty || f.type === ty) && ((f.it_load_mw_planned || f.it_load_mw_operational || 0) >= mn) &&
      (!q || [f.name, f.operator, f.owner, f.key_tenants, f.city_suburb, f.address, f.description_en, f.description_zh].join(" ").toLowerCase().includes(q)));
  }
  function applyFilters() {
    const list = currentFacilities();
    facLayer.clearLayers();
    list.filter((f) => f.lat != null && f.lng != null).forEach((f) => facLayer.addLayer(facilityMarker(f)));
    renderTable(list);
  }
  const COLS = [["name", "name"], ["it_load_mw_planned", "plan_mw", "num"], ["it_load_mw_operational", "op_mw", "num"], ["stage", "stage"], ["operator", "operator"], ["state", "state"], ["city_suburb", "suburb"], ["type", "type"], ["year_commissioned", "commissioned", "num"], ["key_tenants", "tenants"]];
  function renderTable(list) {
    const { key, asc } = sortState;
    const sorted = [...list].sort((a, b) => { const x = a[key], y = b[key]; if (x == null) return 1; if (y == null) return -1; return (typeof x === "number" ? x - y : String(x).localeCompare(String(y))) * (asc ? 1 : -1); });
    $("#tableCount").textContent = `${sorted.length} / ${D.facilities.length}`;
    $("#facTable thead").innerHTML = "<tr>" + COLS.map(([k, l, n]) => `<th data-key="${k}" class="${n || ""} ${k === key ? "sorted" : ""} ${k === key && asc ? "asc" : ""}">${t(l)}</th>`).join("") + "</tr>";
    $("#facTable tbody").innerHTML = sorted.map((f) => `<tr class="clickable" data-fac="${esc(f.facility_id)}">` + COLS.map(([k, , n]) => `<td class="${n || ""}">${k === "stage" ? stageBadge(f.stage) : k.startsWith("year") ? esc(f[k] ?? "—") : n ? fmt(f[k]) : esc(f[k] ?? "")}</td>`).join("") + "</tr>").join("");
  }
  function exportCsv() {
    const list = currentFacilities();
    const keys = Object.keys(list[0] || {}).filter((k) => k !== "sources");
    const rows = [keys.join(",")].concat(list.map((f) => keys.map((k) => `"${String(f[k] ?? "").replace(/"/g, '""')}"`).join(",")));
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + rows.join("\n")], { type: "text/csv" })); a.download = "au_data_centres.csv"; a.click();
  }
  function renderMapLegend() {
    $("#mapLegend").innerHTML = STAGES.map((s) => `<div class="row"><span class="sw" style="background:${stageColor(s)}"></span>${t("stage_" + s)}</div>`).join("") + `<div class="row muted">${t("stage_legend")}</div>`;
  }
  function renderLayerToggles() {
    const box = $("#layerToggles");
    const state = Object.fromEntries($$("input", box).map((i) => [i.dataset.layer, i.checked]));
    box.innerHTML = INFRA_LAYERS.map((l) => `<label><input type="checkbox" data-layer="${esc(l.key)}" ${state[l.key] ?? !l.off ? "checked" : ""}><span class="sw ${l.shape}" style="background:${cssVar(l.color)}"></span>${esc(l.en.startsWith("tl_") ? t(l.en) : (lang === "zh" ? l.zh : l.en))}</label>`).join("");
    $("#geoHint").textContent = D.geoAvailable ? "" : t("geo_missing");
    INFRA_LAYERS.forEach((l) => toggleInfra(l.key, state[l.key] ?? !l.off));
  }
  function infraPopup(p) {
    return `<b>${esc(p.name)}</b><br><span class="muted">${esc(p.category)}${p.voltage_kv ? ` · ${p.voltage_kv} kV` : ""}${p.operator ? ` · ${esc(p.operator)}` : ""}</span><br>${esc(p.capacity_notes || "")}<br><i>${esc(L2(p, "relevance"))}</i>`;
  }
  async function toggleInfra(key, on) {
    const spec = INFRA_LAYERS.find((l) => l.key === key);
    if (infraGroups[key]) { map.removeLayer(infraGroups[key]); delete infraGroups[key]; }
    if (!on || !spec) return;
    const color = cssVar(spec.color);
    let g;
    if (spec.geo) {
      if (!(key in geoCache)) geoCache[key] = await loadJSON(`geo/${spec.geo}`, true);
      const gj = geoCache[key];
      if (!gj) return;
      const kvColor = (kv) => kv >= 500 ? cssVar("--s8") : kv >= 330 ? cssVar("--s2") : kv >= 220 ? cssVar("--s7") : cssVar("--muted");
      g = L.geoJSON(gj, {
        style: (f) => spec.key === "__cables" ? { color: cssVar("--s4"), weight: 1.5, opacity: 0.7, dashArray: "4 4" } : { color: kvColor(f.properties.capacity_kv), weight: f.properties.capacity_kv >= 330 ? 2 : 1.2, opacity: 0.8 },
        pointToLayer: (f, ll) => L.circleMarker(ll, { radius: spec.key === "__cables" ? 4 : 3, color, weight: 1, fillColor: color, fillOpacity: 0.7 }),
        onEachFeature: (f, layer) => { const p = f.properties || {}; layer.bindPopup(`<b>${esc(p.feature_name || p.name || "")}</b><br>${p.capacity_kv || p.voltage_kv ? `${p.capacity_kv || p.voltage_kv} kV · ` : ""}${esc(p.status || p.kind || "")} ${esc(p.state || "")}${p.rfs_year ? ` · RFS ${p.rfs_year}` : ""}${p.owners ? `<br>${esc(p.owners)}` : ""}`); },
      });
    } else {
      const pts = key === "__nbn_all" ? D.nbn.map((n) => ({ ...n, category: "NBN POI", capacity_notes: n.address })) : D.infra.filter((p) => p.category === key);
      g = L.layerGroup(pts.map((p) => {
        const m = spec.shape === "sq"
          ? L.marker([p.lat, p.lng], { icon: L.divIcon({ className: "", html: `<div style="width:${p.voltage_kv >= 330 ? 12 : 9}px;height:${p.voltage_kv >= 330 ? 12 : 9}px;background:${color};border:1.5px solid #fff;transform:rotate(45deg)"></div>`, iconSize: [12, 12], iconAnchor: [6, 6] }) })
          : L.circleMarker([p.lat, p.lng], { radius: key === "__nbn_all" ? 3.5 : 5, color: "#fff", weight: 1, fillColor: color, fillOpacity: 0.9 });
        return m.bindPopup(infraPopup(p));
      }));
    }
    infraGroups[key] = g.addTo(map);
  }

  // ---------- events
  function bind() {
    $$(".tabs button").forEach((b) => b.addEventListener("click", () => {
      $$(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
      $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + b.dataset.tab));
      if (b.dataset.tab === "map") setTimeout(() => map.invalidateSize(), 50);
      Object.values(charts).forEach((c) => c.resize());
      location.hash = b.dataset.tab;
    }));
    $$(".lang-toggle button").forEach((b) => b.addEventListener("click", () => { lang = b.dataset.lang; localStorage.setItem("adc_lang", lang); applyLang(); }));
    ["#fSearch", "#fState", "#fOperator", "#fType", "#fMinMw"].forEach((s) => $(s).addEventListener("input", applyFilters));
    $("#stageToggles").addEventListener("change", applyFilters);
    $("#layerToggles").addEventListener("change", (e) => { if (e.target.dataset.layer) toggleInfra(e.target.dataset.layer, e.target.checked); });
    $("#btnCsv").addEventListener("click", exportCsv);
    $("#facTable").addEventListener("click", (e) => {
      const th = e.target.closest("th"); if (th) { sortState = { key: th.dataset.key, asc: sortState.key === th.dataset.key ? !sortState.asc : true }; renderTable(currentFacilities()); return; }
      const tr = e.target.closest("tr[data-fac]"); if (tr) focusFacility(tr.dataset.fac);
    });
    $("#jurTabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { curJur = b.dataset.jur; renderRegulation(); } });
    $("#opCategory").addEventListener("change", renderStakeholders);
    $("#opGrid").addEventListener("click", (e) => { const c = e.target.closest(".op-card"); if (c) openOperator(c.dataset.op); });
    document.addEventListener("click", (e) => {
      const a = e.target.closest("a[data-op]"); if (a) { e.preventDefault(); openOperator(a.dataset.op); }
      const f = e.target.closest("a[data-fac]"); if (f) { e.preventDefault(); $("#drawer").hidden = true; focusFacility(f.dataset.fac); }
    });
    $("#drawerClose").addEventListener("click", () => { $("#drawer").hidden = true; });
    $("#drawer").addEventListener("click", (e) => { if (e.target.id === "drawer") $("#drawer").hidden = true; });
    ["#nSearch", "#nState", "#nOperator", "#nLang"].forEach((s) => $(s).addEventListener("input", renderNews));
    if (location.hash) { const b = $(`.tabs button[data-tab="${location.hash.slice(1)}"]`); if (b) b.click(); }
  }
  function focusFacility(id) {
    const f = D.facById[id]; if (!f) return;
    $(`.tabs button[data-tab="map"]`).click();
    showDetail(f);
    if (f.lat != null) { map.setView([f.lat, f.lng], Math.max(map.getZoom(), 11)); facLayer.eachLayer((m) => { if (m.options.fac?.facility_id === id) m.openPopup(); }); }
  }

  // ---------- boot
  async function boot() {
    const [meta, facilities, operators, market, reg, infra, nbn, stats, build, news, lines] = await Promise.all([
      loadJSON("meta.json"), loadJSON("facilities.json"), loadJSON("operators.json"), loadJSON("market.json"), loadJSON("regulations.json"),
      loadJSON("infrastructure.json"), loadJSON("nbn_poi.json"), loadJSON("stats.json"), loadJSON("build_info.json", true), loadJSON("news.json", true),
      fetch("data/geo/transmission_lines.geojson", { method: "HEAD" }).then((r) => r.ok).catch(() => false),
    ]);
    Object.assign(D, { meta, facilities, operators, market, reg, infra, nbn, stats, build, news, geoAvailable: lines });
    D.facById = Object.fromEntries(facilities.map((f) => [f.facility_id, f]));
    initMap(); bind(); applyLang();
  }
  boot().catch((e) => { document.querySelector("main").innerHTML = `<div class="card"><h3>Could not load data</h3><p>${esc(e.message)}</p><p class="small">If you opened index.html directly from disk, serve it instead: <code>python -m http.server -d site 8000</code> then open http://localhost:8000</p></div>`; });
})();
