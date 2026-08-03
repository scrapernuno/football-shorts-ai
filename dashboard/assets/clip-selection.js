"use strict";

const LIBRARY_URL = "data/football_library.json";
const STORAGE_KEY = "football-shorts-ai.clip-proposals.v1";
const MAX_CLIP_SECONDS = 15;
const MIN_CLIP_SECONDS = 0.5;

const state = {
  assets: [],
  selected: null,
  proposals: loadProposals(),
};

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return new Intl.NumberFormat("pt-PT", { notation: "compact", maximumFractionDigits: 1 }).format(numeric);
}

function loadProposals() {
  try {
    const payload = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(payload) ? payload : [];
  } catch (_) {
    return [];
  }
}

function persistProposals() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.proposals));
}

function getAssets(payload) {
  if (!payload || typeof payload !== "object") return [];
  if (payload.library && Array.isArray(payload.library.assets)) return payload.library.assets;
  if (Array.isArray(payload.assets)) return payload.assets;
  return [];
}

async function loadLibrary() {
  const response = await fetch(LIBRARY_URL, { cache: "no-store" });
  if (!response.ok) throw new Error(`Football Library HTTP ${response.status}`);
  const payload = await response.json();
  state.assets = getAssets(payload).filter(asset => asset && asset.preview_allowed === true);
  renderAssetOptions();
  selectInitialAsset();
}

function renderAssetOptions() {
  const select = byId("asset-select");
  select.innerHTML = [
    '<option value="">Selecione um vídeo…</option>',
    ...state.assets.map(asset => `<option value="${escapeHtml(asset.asset_id)}">${escapeHtml(asset.provider.toUpperCase())} · ${escapeHtml(asset.title)}</option>`),
  ].join("");
}

function selectInitialAsset() {
  const params = new URLSearchParams(window.location.search);
  const assetId = params.get("asset");
  if (assetId && state.assets.some(asset => asset.asset_id === assetId)) {
    byId("asset-select").value = assetId;
    selectAsset(assetId);
  } else if (state.assets.length) {
    byId("asset-select").value = state.assets[0].asset_id;
    selectAsset(state.assets[0].asset_id);
  }
}

function selectAsset(assetId) {
  state.selected = state.assets.find(asset => asset.asset_id === assetId) || null;
  renderSelectedAsset();
}

function renderSelectedAsset() {
  const asset = state.selected;
  const shell = byId("player-shell");
  if (!asset) {
    byId("asset-title").textContent = "Selecione um vídeo";
    shell.innerHTML = "<p>Selecione um vídeo da biblioteca.</p>";
    return;
  }

  byId("asset-title").textContent = asset.title;
  const rights = byId("rights-badge");
  rights.textContent = asset.rights_status;
  rights.className = `badge ${asset.render_allowed ? "success" : "warning"}`;

  if (asset.embed_url) {
    shell.innerHTML = `<iframe src="${escapeHtml(asset.embed_url)}" title="${escapeHtml(asset.title)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen loading="lazy"></iframe>`;
  } else {
    shell.innerHTML = `<div class="fallback-preview">${asset.thumbnail_url ? `<img src="${escapeHtml(asset.thumbnail_url)}" alt="">` : ""}<a href="${escapeHtml(asset.provider_url)}" target="_blank" rel="noopener noreferrer">Abrir no provider ↗</a></div>`;
  }

  byId("source-meta").innerHTML = [
    ["Provider", asset.provider],
    ["Canal", asset.channel_name],
    ["Views", formatNumber(asset.views)],
    ["Duração", asset.duration_seconds ? `${asset.duration_seconds}s` : "—"],
  ].map(([label, value]) => `<span><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></span>`).join("");

  const end = byId("clip-end");
  const maximum = Number(asset.duration_seconds);
  end.max = Number.isFinite(maximum) ? String(maximum) : "";
  end.value = String(Math.min(5, Number.isFinite(maximum) ? maximum : 5));
  byId("clip-start").value = "0";

  const intent = byId("editorial-intent");
  const productionOption = intent.querySelector('option[value="production_source"]');
  productionOption.disabled = !asset.render_allowed;
  if (!asset.render_allowed && intent.value === "production_source") intent.value = "reference";

  const notice = byId("rights-message");
  if (asset.render_allowed) {
    notice.className = "notice success";
    notice.textContent = "Este asset pode ser usado como fonte de produção segundo o estado de direitos registado.";
  } else {
    notice.className = "notice warning";
    notice.textContent = "Reference only: pode guardar timestamps e intenção editorial, mas o excerto não entra na Render Factory.";
  }
  updateDuration();
}

function currentDuration() {
  return Number(byId("clip-end").value) - Number(byId("clip-start").value);
}

function updateDuration() {
  const duration = currentDuration();
  byId("duration-badge").textContent = Number.isFinite(duration) ? `${Math.max(0, duration).toFixed(1)} s` : "—";
}

function validateSelection() {
  if (!state.selected) throw new Error("Selecione primeiro um vídeo.");
  const start = Number(byId("clip-start").value);
  const end = Number(byId("clip-end").value);
  const duration = end - start;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end <= start) {
    throw new Error("Os timestamps são inválidos.");
  }
  if (duration < MIN_CLIP_SECONDS || duration > MAX_CLIP_SECONDS) {
    throw new Error(`A duração deve estar entre ${MIN_CLIP_SECONDS} e ${MAX_CLIP_SECONDS} segundos.`);
  }
  if (state.selected.duration_seconds && end > Number(state.selected.duration_seconds)) {
    throw new Error("O fim do excerto ultrapassa a duração do vídeo.");
  }
  const intent = byId("editorial-intent").value;
  if (intent === "production_source" && !state.selected.render_allowed) {
    throw new Error("Um asset reference_only não pode ser fonte de produção.");
  }
  return { start, end, duration, intent };
}

function saveClip() {
  try {
    const selection = validateSelection();
    const asset = state.selected;
    const proposal = {
      schema: "football-shorts-ai.dashboard-clip-proposal.v1",
      proposal_id: `LOCAL-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      asset_id: asset.asset_id,
      provider: asset.provider,
      title: asset.title,
      start_seconds: Number(selection.start.toFixed(3)),
      end_seconds: Number(selection.end.toFixed(3)),
      duration_seconds: Number(selection.duration.toFixed(3)),
      editorial_intent: selection.intent,
      note: byId("clip-note").value.trim(),
      rights_status: asset.rights_status,
      render_allowed: Boolean(asset.render_allowed),
      status: asset.render_allowed ? "proposed" : "reference_only",
      auto_acquire: false,
      auto_render: false,
      auto_publish: false,
    };
    state.proposals.unshift(proposal);
    persistProposals();
    renderProposals();
    byId("clip-note").value = "";
  } catch (error) {
    window.alert(error.message);
  }
}

function renderProposals() {
  byId("proposal-count").textContent = String(state.proposals.length);
  const list = byId("proposal-list");
  if (!state.proposals.length) {
    list.innerHTML = '<p class="empty-state">Ainda não existem propostas.</p>';
    return;
  }
  list.innerHTML = state.proposals.map(item => `
    <article class="proposal-card">
      <div>
        <span class="badge ${item.render_allowed ? "success" : "warning"}">${escapeHtml(item.status)}</span>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${item.start_seconds.toFixed(1)}s → ${item.end_seconds.toFixed(1)}s · ${item.duration_seconds.toFixed(1)}s · ${escapeHtml(item.editorial_intent)}</p>
        ${item.note ? `<small>${escapeHtml(item.note)}</small>` : ""}
      </div>
      <button type="button" class="remove-proposal" data-id="${escapeHtml(item.proposal_id)}">Remover</button>
    </article>
  `).join("");
}

function clearProposals() {
  state.proposals = [];
  persistProposals();
  renderProposals();
}

byId("asset-select").addEventListener("change", event => selectAsset(event.target.value));
byId("clip-start").addEventListener("input", updateDuration);
byId("clip-end").addEventListener("input", updateDuration);
byId("save-clip").addEventListener("click", saveClip);
byId("clear-clips").addEventListener("click", clearProposals);
byId("proposal-list").addEventListener("click", event => {
  const button = event.target.closest(".remove-proposal");
  if (!button) return;
  state.proposals = state.proposals.filter(item => item.proposal_id !== button.dataset.id);
  persistProposals();
  renderProposals();
});

renderProposals();
loadLibrary().catch(error => {
  byId("asset-select").innerHTML = '<option value="">Biblioteca indisponível</option>';
  byId("player-shell").innerHTML = `<p>${escapeHtml(error.message)}</p>`;
});
