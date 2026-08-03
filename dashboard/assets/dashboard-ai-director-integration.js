/*
 * FOOTBALL-SHORTS-AI-0058H
 * AI Director Dashboard Main Navigation and Live Package Integration
 *
 * Read-only UI integration. No acquisition, extraction, rendering or publication.
 */

(() => {
  "use strict";

  const PACKAGE_URL = "data/ai_director_review_package.json";
  const REVIEW_URL = "ai-director-review.html";

  const text = (value, fallback = "—") => {
    if (value === null || value === undefined || value === "") return fallback;
    return String(value);
  };

  const percent = (value) => {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return `${Math.round(number <= 1 ? number * 100 : number)}%`;
  };

  function addNavigationEntry() {
    const navigation = document.querySelector(".navigation");
    if (!navigation || navigation.querySelector('[data-ai-director-link="true"]')) return;

    const link = document.createElement("a");
    link.href = REVIEW_URL;
    link.dataset.aiDirectorLink = "true";
    link.textContent = "AI Director";
    navigation.appendChild(link);
  }

  function createPanel() {
    if (document.getElementById("ai-director-intelligence")) {
      return document.getElementById("ai-director-intelligence");
    }

    const main = document.querySelector("main.dashboard");
    if (!main) return null;

    const panel = document.createElement("section");
    panel.id = "ai-director-intelligence";
    panel.className = "panel";
    panel.innerHTML = `
      <div class="section-heading">
        <div>
          <p class="eyebrow">AI DIRECTOR</p>
          <h2>Variant Intelligence</h2>
        </div>
        <a href="${REVIEW_URL}" class="count-badge" style="text-decoration:none">
          Abrir Review Studio ↗
        </a>
      </div>
      <div class="metric-grid" style="margin-bottom:1rem">
        <article class="metric-card">
          <p class="metric-label">Estado</p>
          <strong id="ai-director-state">EVIDENCE_MISSING</strong>
          <span id="ai-director-handover">Factory bloqueada</span>
        </article>
        <article class="metric-card">
          <p class="metric-label">Variante recomendada</p>
          <strong id="ai-director-variant">—</strong>
          <span id="ai-director-variant-title">Sem recomendação</span>
        </article>
        <article class="metric-card">
          <p class="metric-label">Viral prediction</p>
          <strong id="ai-director-viral">—</strong>
          <span>Previsão governada</span>
        </article>
        <article class="metric-card">
          <p class="metric-label">Retenção prevista</p>
          <strong id="ai-director-retention">—</strong>
          <span id="ai-director-duration">Duração indisponível</span>
        </article>
      </div>
      <div class="two-column-grid">
        <article>
          <p class="metric-label">Decisão humana</p>
          <strong id="ai-director-decision">PENDING</strong>
          <p id="ai-director-reviewer" class="empty-state" style="margin-top:.5rem">Revisor não definido.</p>
        </article>
        <article>
          <p class="metric-label">Bloqueadores</p>
          <div id="ai-director-blockers" class="readiness-list">
            <p class="empty-state">AI_DIRECTOR_EVIDENCE_MISSING</p>
          </div>
        </article>
      </div>
    `;

    const editorial = document.getElementById("editorial-intelligence");
    if (editorial && editorial.parentNode) {
      editorial.insertAdjacentElement("afterend", panel);
    } else {
      const ranking = document.getElementById("ranking");
      if (ranking) ranking.insertAdjacentElement("beforebegin", panel);
      else main.prepend(panel);
    }
    return panel;
  }

  function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function renderBlockers(values) {
    const container = document.getElementById("ai-director-blockers");
    if (!container) return;
    const blockers = Array.isArray(values) ? values.filter(Boolean) : [];
    if (!blockers.length) {
      container.innerHTML = '<div class="readiness-item"><span>Director readiness</span><strong class="status-success">READY</strong></div>';
      return;
    }
    container.innerHTML = blockers.map((item) => `
      <div class="readiness-item">
        <span>${text(item)}</span>
        <strong class="status-warning">BLOCKED</strong>
      </div>
    `).join("");
  }

  function renderPackage(payload) {
    const director = payload.director_report || payload.director || {};
    const ranking = payload.performance_ranking || payload.ranking || {};
    const approval = payload.approval || {};
    const handover = payload.factory_handover || payload.handover || {};
    const variants = Array.isArray(payload.variants) ? payload.variants : Array.isArray(director.variants) ? director.variants : [];

    const recommendedId = ranking.recommended_variant_id || director.recommended_variant_id || null;
    const recommended = variants.find((item) => item.variant_id === recommendedId) || {};
    const state = handover.handover_state || approval.approval_state || director.director_state || "evidence_missing";
    const blockers = [
      ...(Array.isArray(director.blockers) ? director.blockers : []),
      ...(Array.isArray(ranking.blockers) ? ranking.blockers : []),
      ...(Array.isArray(approval.blockers) ? approval.blockers : []),
      ...(Array.isArray(handover.blockers) ? handover.blockers : []),
      ...(Array.isArray(payload.blockers) ? payload.blockers : []),
    ];

    setValue("ai-director-state", text(state).toUpperCase());
    setValue("ai-director-handover", handover.handover_state === "ready_for_factory" ? "Factory handover READY" : "Factory bloqueada");
    setValue("ai-director-variant", text(recommended.strategy || recommended.variant_type || recommendedId));
    setValue("ai-director-variant-title", text(recommended.title, "Sem recomendação"));
    setValue("ai-director-viral", percent(recommended.viral_score ?? recommended.viral_prediction ?? ranking.recommended_viral_score));
    setValue("ai-director-retention", percent(recommended.predicted_retention ?? recommended.retention_score));
    setValue("ai-director-duration", Number.isFinite(Number(recommended.total_duration_seconds)) ? `${Number(recommended.total_duration_seconds).toFixed(1)} s` : "Duração indisponível");
    setValue("ai-director-decision", text(approval.decision || approval.approval_state, "PENDING").toUpperCase());
    setValue("ai-director-reviewer", approval.reviewer ? `Revisor: ${approval.reviewer}` : "Revisor não definido.");
    renderBlockers([...new Set(blockers)].sort());
  }

  async function loadPackage() {
    try {
      const response = await fetch(PACKAGE_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      renderPackage(payload);
    } catch (error) {
      renderPackage({ blockers: ["AI_DIRECTOR_EVIDENCE_MISSING"] });
      console.warn("AI Director package unavailable:", error);
    }
  }

  function initialize() {
    addNavigationEntry();
    createPanel();
    loadPackage();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
