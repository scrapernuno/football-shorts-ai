"use strict";

const CLIP_STORAGE_KEY = "football-shorts-ai.clip-proposals.v1";
const PROJECT_STORAGE_KEY = "football-shorts-ai.timeline-project.v1";
const MAX_TIMELINE_SECONDS = 90;
const MIN_TIMELINE_SECONDS = 3;
const MAX_CLIPS = 30;

const state = {
  clips: loadClips(),
  draggedId: null,
};

function byId(id) { return document.getElementById(id); }
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function loadClips() {
  try {
    const savedProject = JSON.parse(localStorage.getItem(PROJECT_STORAGE_KEY) || "null");
    if (savedProject && Array.isArray(savedProject.clips)) return normalizeClips(savedProject.clips);
    const proposals = JSON.parse(localStorage.getItem(CLIP_STORAGE_KEY) || "[]");
    return normalizeClips(Array.isArray(proposals) ? proposals : []);
  } catch (_) {
    return [];
  }
}

function normalizeClips(clips) {
  return clips.slice(0, MAX_CLIPS).map((clip, index) => ({
    ...clip,
    proposal_id: String(clip.proposal_id || clip.clip_id || `CLIP-${index + 1}`),
    duration_seconds: Number(clip.duration_seconds || 0),
    transition: index === 0 ? "none" : String(clip.transition || "cut"),
  }));
}

function totalDuration() {
  return state.clips.reduce((total, clip) => total + (Number.isFinite(clip.duration_seconds) ? clip.duration_seconds : 0), 0);
}

function blockers() {
  const result = [];
  const duration = totalDuration();
  if (!state.clips.length) result.push("A timeline não contém clips.");
  if (state.clips.length > MAX_CLIPS) result.push(`A timeline excede ${MAX_CLIPS} clips.`);
  if (duration < MIN_TIMELINE_SECONDS) result.push(`A duração total deve ter pelo menos ${MIN_TIMELINE_SECONDS} segundos.`);
  if (duration > MAX_TIMELINE_SECONDS) result.push(`A duração total não pode exceder ${MAX_TIMELINE_SECONDS} segundos.`);
  if (state.clips.some(clip => clip.render_allowed !== true)) result.push("Existem clips reference_only ou sem autorização de renderização.");
  if (state.clips.some((clip, index) => index === 0 ? clip.transition !== "none" : !["cut", "fade", "crossfade", "zoom", "none"].includes(clip.transition))) {
    result.push("A configuração das transições é inválida.");
  }
  return result;
}

function readiness() { return blockers().length === 0; }

function render() {
  byId("clip-count").textContent = String(state.clips.length);
  byId("total-duration").textContent = `${totalDuration().toFixed(1)} s`;
  const status = byId("factory-status");
  status.textContent = readiness() ? "READY" : "BLOCKED";
  status.className = `status ${readiness() ? "ready" : "warning"}`;
  byId("prepare-factory").disabled = !readiness();
  renderBlockers();
  renderTimeline();
}

function renderBlockers() {
  const items = blockers();
  byId("blockers").innerHTML = items.length
    ? items.map(item => `<div class="blocker">${escapeHtml(item)}</div>`).join("")
    : '<div class="badge ready">Composição elegível para preparação da Factory</div>';
}

function renderTimeline() {
  const list = byId("timeline-list");
  if (!state.clips.length) {
    list.innerHTML = byId("empty-template").innerHTML;
    return;
  }

  list.innerHTML = state.clips.map((clip, index) => `
    <article class="timeline-card" draggable="true" data-id="${escapeHtml(clip.proposal_id)}">
      <div class="timeline-index">${index + 1}</div>
      <div class="timeline-copy">
        <span class="badge ${clip.render_allowed ? "ready" : "reference"}">${clip.render_allowed ? "RENDERABLE" : "REFERENCE ONLY"}</span>
        <h3>${escapeHtml(clip.title || clip.asset_id || "Clip")}</h3>
        <p>${Number(clip.start_seconds || 0).toFixed(1)}s → ${Number(clip.end_seconds || 0).toFixed(1)}s · ${Number(clip.duration_seconds || 0).toFixed(1)}s</p>
        <small>${escapeHtml(clip.provider || "provider")} · ${escapeHtml(clip.editorial_intent || "reference")}</small>
      </div>
      <div class="timeline-actions">
        <select class="transition-select" data-id="${escapeHtml(clip.proposal_id)}" aria-label="Transição">
          ${transitionOptions(clip.transition, index)}
        </select>
        <button type="button" class="secondary move-up" data-id="${escapeHtml(clip.proposal_id)}" ${index === 0 ? "disabled" : ""}>↑</button>
        <button type="button" class="secondary move-down" data-id="${escapeHtml(clip.proposal_id)}" ${index === state.clips.length - 1 ? "disabled" : ""}>↓</button>
        <button type="button" class="danger remove" data-id="${escapeHtml(clip.proposal_id)}">Remover</button>
      </div>
    </article>
  `).join("");
}

function transitionOptions(current, index) {
  const values = index === 0 ? ["none"] : ["cut", "fade", "crossfade", "zoom", "none"];
  return values.map(value => `<option value="${value}" ${value === current ? "selected" : ""}>${value}</option>`).join("");
}

function move(id, delta) {
  const index = state.clips.findIndex(item => item.proposal_id === id);
  const next = index + delta;
  if (index < 0 || next < 0 || next >= state.clips.length) return;
  [state.clips[index], state.clips[next]] = [state.clips[next], state.clips[index]];
  normalizeTransitions();
  persist();
  render();
}

function normalizeTransitions() {
  state.clips = state.clips.map((clip, index) => ({ ...clip, transition: index === 0 ? "none" : (clip.transition === "none" ? "cut" : clip.transition) }));
}

function removeClip(id) {
  state.clips = state.clips.filter(item => item.proposal_id !== id);
  normalizeTransitions();
  persist();
  render();
}

function projectPayload() {
  const unsigned = {
    schema: "football-shorts-ai.dashboard-timeline-project.v1",
    project_title: byId("project-title").value.trim() || "Football Short",
    format: "9:16",
    resolution: "1080x1920",
    fps: Number(byId("fps").value),
    duration_seconds: Number(totalDuration().toFixed(3)),
    clips: state.clips.map((clip, index) => ({ ...clip, order: index + 1, transition: index === 0 ? "none" : clip.transition })),
    tracks: {
      voiceover: byId("voiceover-state").value,
      music: byId("music-state").value,
      captions: byId("captions-state").value,
    },
    blockers: blockers(),
    status: readiness() ? "READY_FOR_FACTORY_PREPARATION" : "BLOCKED",
    render_enabled: false,
    auto_acquire: false,
    auto_render: false,
    auto_publish: false,
  };
  return unsigned;
}

function persist() {
  localStorage.setItem(PROJECT_STORAGE_KEY, JSON.stringify(projectPayload()));
}

function downloadProject() {
  const blob = new Blob([JSON.stringify(projectPayload(), null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "timeline_project.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

function prepareFactory() {
  if (!readiness()) return;
  persist();
  window.alert("Composição guardada como READY_FOR_FACTORY_PREPARATION. Nenhum render foi iniciado.");
}

byId("timeline-list").addEventListener("click", event => {
  const target = event.target.closest("button");
  if (!target) return;
  const id = target.dataset.id;
  if (target.classList.contains("move-up")) move(id, -1);
  if (target.classList.contains("move-down")) move(id, 1);
  if (target.classList.contains("remove")) removeClip(id);
});

byId("timeline-list").addEventListener("change", event => {
  const select = event.target.closest(".transition-select");
  if (!select) return;
  const clip = state.clips.find(item => item.proposal_id === select.dataset.id);
  if (clip) clip.transition = select.value;
  persist();
  render();
});

byId("timeline-list").addEventListener("dragstart", event => {
  const card = event.target.closest(".timeline-card");
  if (!card) return;
  state.draggedId = card.dataset.id;
  card.classList.add("dragging");
});
byId("timeline-list").addEventListener("dragend", event => {
  event.target.closest(".timeline-card")?.classList.remove("dragging");
  state.draggedId = null;
});
byId("timeline-list").addEventListener("dragover", event => event.preventDefault());
byId("timeline-list").addEventListener("drop", event => {
  event.preventDefault();
  const target = event.target.closest(".timeline-card");
  if (!target || !state.draggedId || target.dataset.id === state.draggedId) return;
  const from = state.clips.findIndex(item => item.proposal_id === state.draggedId);
  const to = state.clips.findIndex(item => item.proposal_id === target.dataset.id);
  const [clip] = state.clips.splice(from, 1);
  state.clips.splice(to, 0, clip);
  normalizeTransitions();
  persist();
  render();
});

["project-title", "fps", "voiceover-state", "music-state", "captions-state"].forEach(id => {
  byId(id).addEventListener("change", persist);
  byId(id).addEventListener("input", persist);
});
byId("clear-timeline").addEventListener("click", () => { state.clips = []; persist(); render(); });
byId("save-project").addEventListener("click", () => { persist(); window.alert("Composição guardada localmente."); });
byId("export-project").addEventListener("click", downloadProject);
byId("prepare-factory").addEventListener("click", prepareFactory);

render();
