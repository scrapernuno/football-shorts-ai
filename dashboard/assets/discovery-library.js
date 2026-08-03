"use strict";

const DATA_URL = "data/football_library.json";
let assets = [];

function byId(id) { return document.getElementById(id); }
function text(value, fallback = "—") { return typeof value === "string" && value.trim() ? value.trim() : fallback; }
function number(value) { return typeof value === "number" && Number.isFinite(value) ? value : 0; }
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
function formatInteger(value) { return new Intl.NumberFormat("pt-PT", { notation: "compact", maximumFractionDigits: 1 }).format(number(value)); }
function normalize(value) { return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-PT"); }

function extractLibrary(payload) {
  const library = payload && typeof payload === "object" && payload.library ? payload.library : payload;
  if (!library || typeof library !== "object" || !Array.isArray(library.assets)) {
    throw new Error("football_library.json não contém uma biblioteca válida.");
  }
  return library;
}

function uniqueValues(key) {
  return [...new Set(assets.map((asset) => asset[key]).filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), "pt-PT"));
}

function fillSelect(id, values) {
  const select = byId(id);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = String(value).replaceAll("_", " ");
    select.append(option);
  }
}

function renderSummary(library) {
  const summary = library.summary || {};
  byId("summary-total").textContent = String(library.asset_count ?? assets.length);
  byId("summary-preview").textContent = String(summary.previewable ?? assets.filter((a) => a.preview_allowed).length);
  byId("summary-renderable").textContent = String(summary.renderable ?? assets.filter((a) => a.render_allowed).length);
  byId("summary-providers").textContent = String(Object.keys(summary.providers || {}).length || uniqueValues("provider").length);
}

function matches(asset) {
  const query = normalize(byId("search-input").value);
  const provider = byId("provider-filter").value;
  const rights = byId("rights-filter").value;
  const state = byId("state-filter").value;
  const previewOnly = byId("preview-filter").checked;

  if (provider && asset.provider !== provider) return false;
  if (rights && asset.rights_status !== rights) return false;
  if (state && asset.library_state !== state) return false;
  if (previewOnly && !asset.preview_allowed) return false;
  if (!query) return true;

  const haystack = normalize([
    asset.title,
    asset.description,
    asset.channel_name,
    asset.competition,
    ...(asset.teams || []),
    ...(asset.players || []),
    ...(asset.tags || []),
  ].join(" "));
  return query.split(/\s+/).filter(Boolean).every((term) => haystack.includes(term));
}

function sortAssets(items) {
  const sort = byId("sort-filter").value;
  return [...items].sort((a, b) => {
    if (sort === "views") return number(b.views) - number(a.views) || number(b.score) - number(a.score);
    if (sort === "recent") return String(b.published_at || b.discovered_at || "").localeCompare(String(a.published_at || a.discovered_at || ""));
    if (sort === "title") return text(a.title).localeCompare(text(b.title), "pt-PT");
    return number(b.score) - number(a.score) || number(b.views) - number(a.views);
  });
}

function card(asset) {
  const thumbnail = asset.thumbnail_url
    ? `<img src="${escapeHtml(asset.thumbnail_url)}" alt="" loading="lazy" referrerpolicy="no-referrer">`
    : `<div class="thumbnail-fallback">SEM THUMBNAIL</div>`;
  const tags = [asset.rights_status, asset.library_state]
    .filter(Boolean)
    .map((value) => `<span class="pill ${value === "reference_only" ? "pill-reference" : "pill-rights"}">${escapeHtml(String(value).replaceAll("_", " "))}</span>`)
    .join("");
  const renderPill = asset.render_allowed ? `<span class="pill pill-render">render permitido</span>` : "";
  const previewDisabled = !asset.preview_allowed || !asset.embed_url;

  return `
    <article class="video-card" data-asset-id="${escapeHtml(asset.asset_id)}">
      <div class="video-thumbnail">
        ${thumbnail}
        <span class="provider-badge">${escapeHtml(asset.provider)}</span>
        <span class="score-badge">${Math.round(number(asset.score))}</span>
      </div>
      <div class="video-card-body">
        <h3 class="video-title">${escapeHtml(text(asset.title, "Sem título"))}</h3>
        <div class="video-channel">${escapeHtml(text(asset.channel_name, "Canal desconhecido"))}</div>
        <div class="video-meta">
          <span>${formatInteger(asset.views)} views</span>
          <span>${number(asset.duration_seconds) ? `${number(asset.duration_seconds).toFixed(1)}s` : "duração —"}</span>
          <span>${escapeHtml(text(asset.competition, "competição —"))}</span>
        </div>
        <div class="video-tags">${tags}${renderPill}</div>
        <div class="video-actions">
          <button class="primary preview-button" data-asset-id="${escapeHtml(asset.asset_id)}" ${previewDisabled ? "disabled" : ""}>▶ Preview</button>
          <a href="${escapeHtml(asset.provider_url)}" target="_blank" rel="noopener noreferrer">Abrir origem ↗</a>
        </div>
      </div>
    </article>`;
}

function renderGrid() {
  const visible = sortAssets(assets.filter(matches));
  byId("result-count").textContent = `${visible.length} ${visible.length === 1 ? "resultado" : "resultados"}`;
  byId("library-status").textContent = visible.length ? "" : "Nenhum vídeo corresponde aos filtros selecionados.";
  byId("video-grid").innerHTML = visible.length ? visible.map(card).join("") : `<div class="empty-card">A biblioteca ainda não contém resultados para esta pesquisa.</div>`;
  document.querySelectorAll(".preview-button").forEach((button) => button.addEventListener("click", () => openPreview(button.dataset.assetId)));
}

function openPreview(assetId) {
  const asset = assets.find((item) => item.asset_id === assetId);
  if (!asset || !asset.embed_url || !asset.preview_allowed) return;
  byId("preview-content").innerHTML = `
    <iframe class="preview-frame" src="${escapeHtml(asset.embed_url)}" title="${escapeHtml(text(asset.title))}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
    <div class="preview-details">
      <h2>${escapeHtml(text(asset.title))}</h2>
      <p>${escapeHtml(text(asset.description, "Sem descrição disponível."))}</p>
      <p>${escapeHtml(asset.provider)} · ${escapeHtml(text(asset.channel_name))} · ${escapeHtml(String(asset.rights_status).replaceAll("_", " "))}</p>
    </div>`;
  byId("preview-dialog").showModal();
}

async function initialize() {
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const library = extractLibrary(payload);
    assets = library.assets.filter((asset) => asset && typeof asset === "object");
    renderSummary(library);
    fillSelect("provider-filter", uniqueValues("provider"));
    fillSelect("rights-filter", uniqueValues("rights_status"));
    fillSelect("state-filter", uniqueValues("library_state"));
    byId("library-filters").addEventListener("input", renderGrid);
    byId("library-filters").addEventListener("change", renderGrid);
    renderGrid();
  } catch (error) {
    byId("library-status").textContent = `Não foi possível carregar a biblioteca: ${error.message}`;
    byId("video-grid").innerHTML = `<div class="empty-card">Execute a exportação 0054C para gerar dashboard/data/football_library.json.</div>`;
  }
}

document.addEventListener("DOMContentLoaded", initialize);
