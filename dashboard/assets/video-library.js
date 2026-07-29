"use strict";

const VIDEO_LIBRARY_URL = "data/video_library.json";

const state = {
    library: null,
    selectedVideoId: null,
    search: "",
    status: "all",
};

function byId(id) {
    return document.getElementById(id);
}

function safeText(value, fallback = "—") {
    return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return safeText(value, "Data indisponível");
    }
    return new Intl.DateTimeFormat("pt-PT", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "Europe/Lisbon",
    }).format(date);
}

function formatDuration(value) {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds <= 0) {
        return "—";
    }
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return minutes > 0
        ? `${minutes}:${String(remainder).padStart(2, "0")}`
        : `${remainder}s`;
}

function statusClass(status) {
    if (status === "ready" || status === "published") {
        return "status-success";
    }
    if (status === "draft" || status === "rendering") {
        return "status-warning";
    }
    if (status === "failed") {
        return "status-danger";
    }
    return "status-neutral";
}

function validateLibrary(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
        throw new Error("A biblioteca não contém um objeto JSON válido.");
    }
    if (payload.schema_version !== "1.0") {
        throw new Error("Versão do contrato de biblioteca não suportada.");
    }
    if (!Array.isArray(payload.videos)) {
        throw new Error("O campo videos deve ser uma lista.");
    }
    const ids = new Set();
    for (const video of payload.videos) {
        if (!video || typeof video !== "object" || Array.isArray(video)) {
            throw new Error("A biblioteca contém um vídeo inválido.");
        }
        if (typeof video.video_id !== "string" || !video.video_id.trim()) {
            throw new Error("Todos os vídeos necessitam de video_id.");
        }
        if (ids.has(video.video_id)) {
            throw new Error(`video_id duplicado: ${video.video_id}`);
        }
        ids.add(video.video_id);
    }
    return payload;
}

async function loadLibrary() {
    const response = await fetch(VIDEO_LIBRARY_URL, { cache: "no-store" });
    if (!response.ok) {
        throw new Error(`video_library.json: HTTP ${response.status}`);
    }
    return validateLibrary(await response.json());
}

function filteredVideos() {
    const videos = state.library?.videos ?? [];
    const query = state.search.trim().toLocaleLowerCase("pt-PT");
    return videos.filter((video) => {
        const matchesStatus = state.status === "all" || video.status === state.status;
        const haystack = [video.video_id, video.title, video.topic, video.platform]
            .map((value) => safeText(value, "").toLocaleLowerCase("pt-PT"))
            .join(" ");
        return matchesStatus && (!query || haystack.includes(query));
    });
}

function thumbnailMarkup(video) {
    if (typeof video.thumbnail_path === "string" && video.thumbnail_path.trim()) {
        return `<img src="${escapeHtml(video.thumbnail_path)}" alt="Thumbnail de ${escapeHtml(video.title)}" loading="lazy">`;
    }
    return "🎬";
}

function renderList() {
    const list = byId("video-list");
    const videos = filteredVideos();
    byId("video-count").textContent = `${videos.length} ${videos.length === 1 ? "vídeo" : "vídeos"}`;

    if (videos.length === 0) {
        list.innerHTML = '<p class="empty-state">Nenhum vídeo corresponde aos filtros selecionados.</p>';
        return;
    }

    list.innerHTML = videos.map((video) => `
        <button
            type="button"
            class="video-card"
            data-video-id="${escapeHtml(video.video_id)}"
            aria-current="${video.video_id === state.selectedVideoId ? "true" : "false"}"
        >
            <span class="video-thumbnail">${thumbnailMarkup(video)}</span>
            <span class="video-copy">
                <strong>${escapeHtml(safeText(video.title, "Sem título"))}</strong>
                <span>${escapeHtml(safeText(video.topic, "Tema não definido"))}</span>
                <span>${escapeHtml(video.video_id)} · ${escapeHtml(safeText(video.platform, "Plataforma não definida"))}</span>
            </span>
            <span class="video-meta">
                <span class="status-badge ${statusClass(video.status)}">${escapeHtml(safeText(video.status, "unknown").toUpperCase())}</span>
                <span>${escapeHtml(formatDuration(video.duration_seconds))}</span>
            </span>
        </button>
    `).join("");

    for (const card of list.querySelectorAll("[data-video-id]")) {
        card.addEventListener("click", () => selectVideo(card.dataset.videoId));
    }
}

function setDetail(id, value) {
    byId(id).textContent = safeText(value);
}

function resetPlayer() {
    const player = byId("video-player");
    player.pause();
    player.removeAttribute("src");
    player.innerHTML = "";
    player.load();
    player.hidden = true;
    byId("player-placeholder").hidden = false;
}

function selectVideo(videoId) {
    const video = state.library.videos.find((item) => item.video_id === videoId);
    if (!video) {
        return;
    }

    state.selectedVideoId = videoId;
    renderList();

    const badge = byId("player-status");
    badge.textContent = safeText(video.status, "unknown").toUpperCase();
    badge.className = `status-badge ${statusClass(video.status)}`;

    setDetail("detail-id", video.video_id);
    setDetail("detail-title", video.title);
    setDetail("detail-topic", video.topic);
    setDetail("detail-platform", video.platform);
    setDetail("detail-duration", formatDuration(video.duration_seconds));
    setDetail("detail-format", `${video.width}×${video.height} · ${safeText(video.orientation)}`);
    setDetail("detail-render-engine", video.render_engine);

    resetPlayer();

    const file = video.video_file;
    if (file && typeof file.path === "string" && file.path.trim()) {
        const player = byId("video-player");
        const source = document.createElement("source");
        source.src = file.path;
        source.type = safeText(file.mime_type, "video/mp4");
        player.appendChild(source);

        if (typeof video.subtitles_path === "string" && video.subtitles_path.trim()) {
            const track = document.createElement("track");
            track.kind = "subtitles";
            track.label = "Português";
            track.srclang = "pt";
            track.src = video.subtitles_path;
            track.default = true;
            player.appendChild(track);
        }

        player.hidden = false;
        byId("player-placeholder").hidden = true;
        player.load();
        byId("player-message").textContent = "Ficheiro governado carregado no player HTML5.";
        return;
    }

    const messages = {
        draft: "Vídeo em draft: o ficheiro final ainda não foi associado.",
        rendering: "Renderização em curso: o player será ativado quando o ficheiro estiver ready.",
        failed: safeText(video.failure_reason, "A renderização deste vídeo falhou."),
    };
    byId("player-message").textContent = messages[video.status] ?? "O vídeo ainda não possui ficheiro reproduzível.";
}

function bindFilters() {
    byId("video-search").addEventListener("input", (event) => {
        state.search = event.target.value;
        renderList();
    });
    byId("video-status-filter").addEventListener("change", (event) => {
        state.status = event.target.value;
        renderList();
    });
}

function showError(error) {
    byId("video-library-error-message").textContent = error instanceof Error ? error.message : String(error);
    byId("video-library-error").hidden = false;
    byId("video-list").innerHTML = '<p class="empty-state">Biblioteca indisponível.</p>';
}

async function initialize() {
    try {
        state.library = await loadLibrary();
        byId("library-generated-at").textContent = formatDate(state.library.generated_at);
        bindFilters();
        renderList();
        if (state.library.videos.length > 0) {
            selectVideo(state.library.videos[0].video_id);
        }
    } catch (error) {
        showError(error);
    }
}

document.addEventListener("DOMContentLoaded", initialize);
