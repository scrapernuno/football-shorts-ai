(() => {
  "use strict";

  const PACKAGE_URL = "data/editorial_review_package.json";

  const percent = (value) => `${Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100)}%`;
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[char]));

  function ensureNavigationLink() {
    const navigation = document.querySelector(".navigation");
    if (!navigation || navigation.querySelector('[href="#editorial-intelligence"]')) return;
    const link = document.createElement("a");
    link.href = "#editorial-intelligence";
    link.textContent = "Editorial Review";
    navigation.insertBefore(link, navigation.querySelector('[href="#publishing"]'));
  }

  function ensurePanel() {
    if (document.getElementById("editorial-intelligence")) return;
    const dashboard = document.querySelector("main.dashboard");
    const publishing = document.getElementById("publishing");
    if (!dashboard) return;

    const section = document.createElement("section");
    section.id = "editorial-intelligence";
    section.className = "panel editorial-intelligence-panel";
    section.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">STORY ↔ SCENES</p>
          <h2>Editorial Intelligence</h2>
        </div>
        <a href="editorial-review.html" class="count-badge editorial-review-link">Abrir Review Studio ↗</a>
      </div>
      <div class="editorial-intelligence-grid">
        <article class="metric-card"><p class="metric-label">Qualidade</p><strong id="ei-quality">—</strong><span id="ei-band">Sem evidência</span></article>
        <article class="metric-card"><p class="metric-label">Potencial viral</p><strong id="ei-viral">—</strong><span>Estimativa editorial</span></article>
        <article class="metric-card"><p class="metric-label">Retenção</p><strong id="ei-retention">—</strong><span>Potencial previsto</span></article>
        <article class="metric-card"><p class="metric-label">Direitos</p><strong id="ei-rights">—</strong><span id="ei-rights-state">Fail-closed</span></article>
      </div>
      <div class="editorial-intelligence-summary">
        <div><span class="metric-label">Estado</span><strong id="ei-state">EVIDENCE_MISSING</strong></div>
        <div><span class="metric-label">Hook</span><strong id="ei-hook">Sem proposta editorial</strong></div>
        <div><span class="metric-label">Cenas</span><strong id="ei-scenes">0</strong></div>
        <div><span class="metric-label">Bloqueadores</span><strong id="ei-blockers">—</strong></div>
      </div>
      <p class="editorial-intelligence-note">A revisão humana é obrigatória. Esta área não adquire media, não renderiza e não publica.</p>`;

    if (publishing) dashboard.insertBefore(section, publishing);
    else dashboard.appendChild(section);
  }

  function injectStyles() {
    if (document.getElementById("editorial-intelligence-styles")) return;
    const style = document.createElement("style");
    style.id = "editorial-intelligence-styles";
    style.textContent = `
      .editorial-review-link{text-decoration:none}.editorial-intelligence-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem;margin:1rem 0}.editorial-intelligence-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem;padding:1rem;border:1px solid rgba(255,255,255,.1);border-radius:14px;background:rgba(4,13,26,.45)}.editorial-intelligence-summary div{display:flex;flex-direction:column;gap:.35rem}.editorial-intelligence-note{margin:1rem 0 0;color:var(--muted-color,#9aa7b8)}.ei-ok{color:#55d98a}.ei-blocked{color:#ffb454}@media(max-width:900px){.editorial-intelligence-grid,.editorial-intelligence-summary{grid-template-columns:1fr 1fr}}@media(max-width:560px){.editorial-intelligence-grid,.editorial-intelligence-summary{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function setText(id, value) {
    const target = document.getElementById(id);
    if (target) target.textContent = value;
  }

  async function loadEditorialPackage() {
    try {
      const response = await fetch(PACKAGE_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const timeline = payload.timeline || payload.automatic_timeline || {};
      const score = payload.scorecard || payload.editorial_quality || payload.score || {};
      const scenes = Array.isArray(timeline.scenes) ? timeline.scenes : [];
      const blockers = [...new Set([
        ...(Array.isArray(payload.blockers) ? payload.blockers : []),
        ...(Array.isArray(timeline.blockers) ? timeline.blockers : []),
        ...(Array.isArray(score.blockers) ? score.blockers : []),
      ])].sort();
      const ready = scenes.length > 0
        && blockers.length === 0
        && scenes.every((scene) => scene.render_allowed === true)
        && timeline.timeline_state !== "blocked"
        && score.score_state !== "blocked";

      setText("ei-quality", percent(score.editorial_quality_score));
      setText("ei-band", score.quality_band || "Sem banda");
      setText("ei-viral", percent(score.viral_potential_score));
      setText("ei-retention", percent(score.retention_potential_score));
      setText("ei-rights", percent(score.rights_readiness_score));
      setText("ei-rights-state", ready ? "Pronto para revisão" : "Bloqueado");
      setText("ei-state", ready ? "READY_FOR_REVIEW" : "BLOCKED");
      setText("ei-hook", scenes.find((scene) => scene.beat_role === "hook")?.beat_text || "Sem hook disponível");
      setText("ei-scenes", String(scenes.length));
      setText("ei-blockers", blockers.length ? blockers.join(" · ") : "Sem bloqueadores");

      const state = document.getElementById("ei-state");
      if (state) state.className = ready ? "ei-ok" : "ei-blocked";
    } catch (error) {
      setText("ei-state", "EVIDENCE_MISSING");
      setText("ei-blockers", `Não foi possível carregar ${PACKAGE_URL}`);
      const state = document.getElementById("ei-state");
      if (state) state.className = "ei-blocked";
    }
  }

  function initialize() {
    injectStyles();
    ensureNavigationLink();
    ensurePanel();
    loadEditorialPackage();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
