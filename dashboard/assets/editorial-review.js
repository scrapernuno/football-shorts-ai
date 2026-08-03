(() => {
  "use strict";

  const PACKAGE_URL = "data/editorial_review_package.json";
  const REVIEW_KEY = "football-shorts-ai.editorial-review.v1";
  const TIMELINE_KEY = "football-shorts-ai.automatic-timeline.v1";

  const state = {
    package: null,
    selectedScenes: new Map(),
  };

  const el = (id) => document.getElementById(id);
  const clamp = (value) => Math.max(0, Math.min(1, Number(value) || 0));
  const percent = (value) => `${Math.round(clamp(value) * 100)}%`;

  function packageTimeline(payload) {
    return payload?.timeline || payload?.automatic_timeline || payload;
  }

  function packageScore(payload) {
    return payload?.scorecard || payload?.editorial_quality || payload?.score || {};
  }

  function timelineScenes(payload) {
    const timeline = packageTimeline(payload);
    return Array.isArray(timeline?.scenes) ? timeline.scenes : [];
  }

  function alternativesFor(payload, scene) {
    const alternatives = payload?.alternatives_by_beat || payload?.alternatives || {};
    const byBeat = alternatives[scene.beat_id] || alternatives[scene.beat_role] || [];
    const normalized = Array.isArray(byBeat) ? byBeat : [];
    const current = {
      scene_id: scene.scene_id,
      match_score: scene.match_score,
      render_allowed: scene.render_allowed,
      label: "Seleção automática",
    };
    return [current, ...normalized.filter((item) => item?.scene_id && item.scene_id !== scene.scene_id)];
  }

  function blockers(payload) {
    const timeline = packageTimeline(payload);
    const score = packageScore(payload);
    return [...new Set([
      ...(Array.isArray(payload?.blockers) ? payload.blockers : []),
      ...(Array.isArray(timeline?.blockers) ? timeline.blockers : []),
      ...(Array.isArray(score?.blockers) ? score.blockers : []),
      ...timelineScenes(payload).flatMap((scene) => Array.isArray(scene.blockers) ? scene.blockers : []),
    ])].sort();
  }

  function isReady(payload) {
    const timeline = packageTimeline(payload);
    const score = packageScore(payload);
    const scenes = timelineScenes(payload);
    return Boolean(
      scenes.length
      && blockers(payload).length === 0
      && scenes.every((scene) => scene.render_allowed === true)
      && timeline.timeline_state !== "blocked"
      && score.score_state !== "blocked"
    );
  }

  function selectedScene(scene) {
    return state.selectedScenes.get(scene.beat_id) || scene.scene_id;
  }

  function renderSummary(payload) {
    const score = packageScore(payload);
    el("quality-score").textContent = percent(score.editorial_quality_score);
    el("quality-band").textContent = score.quality_band || "Sem banda";
    el("viral-score").textContent = percent(score.viral_potential_score);
    el("retention-score").textContent = percent(score.retention_potential_score);
    el("rights-score").textContent = percent(score.rights_readiness_score);
    el("rights-state").textContent = score.rights_readiness_score === 1 ? "Pronto" : "Bloqueado";
    el("rights-state").className = score.rights_readiness_score === 1 ? "rights-ok" : "rights-blocked";
    const status = isReady(payload) ? "READY_FOR_REVIEW" : "BLOCKED";
    el("review-state").textContent = status;
    el("review-state").className = `status ${status === "READY_FOR_REVIEW" ? "ok" : "danger"}`;
  }

  function renderBlockers(payload) {
    const target = el("blockers");
    const values = blockers(payload);
    target.innerHTML = values.length
      ? values.map((value) => `<div class="blocker">${escapeHtml(value)}</div>`).join("")
      : '<div class="rights-ok">Sem bloqueadores editoriais ou de direitos.</div>';
  }

  function sceneMarkup(scene, index, payload) {
    const alternatives = alternativesFor(payload, scene);
    const selected = selectedScene(scene);
    return `
      <article class="scene-card" data-beat-id="${escapeHtml(scene.beat_id)}">
        <div class="scene-head">
          <div class="scene-order">${String(index + 1).padStart(2, "0")}</div>
          <div class="scene-title">
            <h3>${escapeHtml(String(scene.beat_role || "scene").toUpperCase())}</h3>
            <p>${escapeHtml(scene.beat_text || "Sem texto editorial")}</p>
          </div>
          <div class="scene-score"><span>Match</span><strong>${percent(scene.match_score)}</strong></div>
        </div>
        <div class="scene-body">
          <div class="meta-grid">
            <div class="meta-item"><span>CENA</span>${escapeHtml(selected)}</div>
            <div class="meta-item"><span>ORIGEM</span>${Number(scene.source_start_seconds || 0).toFixed(1)}–${Number(scene.source_end_seconds || 0).toFixed(1)} s</div>
            <div class="meta-item"><span>TIMELINE</span>${Number(scene.timeline_start_seconds || 0).toFixed(1)}–${Number(scene.timeline_end_seconds || 0).toFixed(1)} s</div>
            <div class="meta-item"><span>TRANSIÇÃO</span>${escapeHtml(scene.transition || "cut")}</div>
            <div class="meta-item"><span>DIREITOS</span><span class="${scene.render_allowed ? "rights-ok" : "rights-blocked"}">${scene.render_allowed ? "Render permitido" : "Bloqueado"}</span></div>
            <div class="meta-item"><span>PROVIDER</span>${escapeHtml(scene.provider || "unknown")}</div>
          </div>
          <div>
            <strong>Alternativas</strong>
            <div class="alternatives">
              ${alternatives.map((item) => `
                <button type="button" class="alt-button ${selected === item.scene_id ? "selected" : ""}"
                  data-beat-id="${escapeHtml(scene.beat_id)}" data-scene-id="${escapeHtml(item.scene_id)}"
                  ${item.render_allowed === false ? 'title="Cena sem direitos de renderização"' : ""}>
                  <span>${escapeHtml(item.label || item.scene_id)}</span>
                  <span>${percent(item.match_score)}</span>
                </button>`).join("")}
            </div>
          </div>
        </div>
      </article>`;
  }

  function renderScenes(payload) {
    const scenes = timelineScenes(payload);
    const target = el("scene-list");
    el("scene-count").textContent = `${scenes.length} ${scenes.length === 1 ? "cena" : "cenas"}`;
    if (!scenes.length) {
      target.replaceChildren(el("empty-template").content.cloneNode(true));
      return;
    }
    target.innerHTML = scenes.map((scene, index) => sceneMarkup(scene, index, payload)).join("");
    target.querySelectorAll(".alt-button").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedScenes.set(button.dataset.beatId, button.dataset.sceneId);
        renderScenes(state.package);
        refreshApproval();
      });
    });
  }

  function refreshApproval() {
    const decision = el("decision").value;
    el("approve-factory").disabled = !(state.package && isReady(state.package) && decision === "approved");
  }

  function render(payload, message = "Pacote editorial carregado.") {
    state.package = payload;
    state.selectedScenes.clear();
    timelineScenes(payload).forEach((scene) => state.selectedScenes.set(scene.beat_id, scene.scene_id));
    renderSummary(payload);
    renderScenes(payload);
    renderBlockers(payload);
    el("load-message").textContent = message;
    refreshApproval();
  }

  async function loadDashboardData() {
    try {
      const response = await fetch(PACKAGE_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json(), `Carregado de ${PACKAGE_URL}.`);
      return;
    } catch (error) {
      const cached = localStorage.getItem(TIMELINE_KEY);
      if (cached) {
        render(JSON.parse(cached), "Ficheiro público indisponível; carregada evidência local.");
        return;
      }
      el("load-message").textContent = `Não foi possível carregar a proposta: ${error.message}`;
    }
  }

  function reviewEvidence() {
    if (!state.package) throw new Error("Nenhuma proposta editorial carregada.");
    return {
      schema: "football-shorts-ai.editorial-review.v1",
      reviewed_at: new Date().toISOString(),
      automatic_timeline_id: packageTimeline(state.package)?.timeline_id || packageTimeline(state.package)?.automatic_timeline_id || null,
      editorial_score_id: packageScore(state.package)?.score_id || null,
      decision: el("decision").value,
      notes: el("review-notes").value.trim(),
      selected_scenes: timelineScenes(state.package).map((scene) => ({
        beat_id: scene.beat_id,
        original_scene_id: scene.scene_id,
        selected_scene_id: selectedScene(scene),
      })),
      blockers: blockers(state.package),
      ready_for_factory_preparation: isReady(state.package) && el("decision").value === "approved",
      acquisition_enabled: false,
      render_enabled: false,
      auto_render: false,
      auto_publish: false,
    };
  }

  function saveReview() {
    try {
      localStorage.setItem(REVIEW_KEY, JSON.stringify(reviewEvidence()));
      el("load-message").textContent = "Revisão guardada localmente.";
    } catch (error) {
      el("load-message").textContent = error.message;
    }
  }

  function exportReview() {
    try {
      const blob = new Blob([`${JSON.stringify(reviewEvidence(), null, 2)}\n`], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "editorial_review_evidence.json";
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (error) {
      el("load-message").textContent = error.message;
    }
  }

  function resetReview() {
    state.package = null;
    state.selectedScenes.clear();
    localStorage.removeItem(REVIEW_KEY);
    el("decision").value = "pending";
    el("review-notes").value = "";
    ["quality-score", "viral-score", "retention-score", "rights-score"].forEach((id) => el(id).textContent = "—");
    el("review-state").textContent = "NOT_LOADED";
    el("review-state").className = "status warning";
    el("scene-count").textContent = "0 cenas";
    el("scene-list").replaceChildren(el("empty-template").content.cloneNode(true));
    el("blockers").innerHTML = "";
    el("load-message").textContent = "Revisão limpa.";
    refreshApproval();
  }

  function importJson(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try { render(JSON.parse(reader.result), `Importado: ${file.name}`); }
      catch (error) { el("load-message").textContent = `JSON inválido: ${error.message}`; }
    };
    reader.readAsText(file);
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }

  el("load-dashboard-data").addEventListener("click", loadDashboardData);
  el("import-json").addEventListener("change", (event) => event.target.files[0] && importJson(event.target.files[0]));
  el("reset-review").addEventListener("click", resetReview);
  el("decision").addEventListener("change", refreshApproval);
  el("save-review").addEventListener("click", saveReview);
  el("export-review").addEventListener("click", exportReview);
  el("approve-factory").addEventListener("click", () => {
    saveReview();
    el("load-message").textContent = "Handover editorial aprovado e guardado. Nenhuma renderização foi iniciada.";
  });

  resetReview();
})();
