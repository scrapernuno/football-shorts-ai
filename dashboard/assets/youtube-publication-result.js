(() => {
  "use strict";
  const DATA_URL = "data/youtube_publication_result.json";
  const byId = (id) => document.getElementById(id);
  const text = (id, value) => { byId(id).textContent = value || "—"; };

  function render(payload) {
    text("state", payload.intake_state);
    text("videoId", payload.youtube_video_id);
    text("previous", payload.previous_visibility);
    text("verified", payload.verified_visibility);
    text("execution", payload.execution_id);

    const blockers = byId("blockers");
    blockers.replaceChildren();
    (payload.blockers || []).forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      blockers.appendChild(li);
    });
    if (!(payload.blockers || []).length) {
      const li = document.createElement("li");
      li.textContent = "Sem bloqueadores";
      blockers.appendChild(li);
    }

    const media = byId("media");
    const link = byId("openYouTube");
    media.replaceChildren();
    const confirmed = payload.intake_state === "confirmed" &&
      payload.publication_confirmed === true && payload.youtube_video_id;
    if (!confirmed) {
      const blocked = document.createElement("div");
      blocked.className = "blocked";
      blocked.textContent = "A publicação ainda não foi confirmada por uma execução 0062B válida.";
      media.appendChild(blocked);
      link.hidden = true;
      return;
    }

    const iframe = document.createElement("iframe");
    iframe.className = "player";
    iframe.title = "YouTube publication result";
    iframe.loading = "lazy";
    iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
    iframe.allowFullscreen = true;
    iframe.src = `https://www.youtube-nocookie.com/embed/${encodeURIComponent(payload.youtube_video_id)}`;
    media.appendChild(iframe);
    link.href = payload.publication_url || `https://www.youtube.com/watch?v=${encodeURIComponent(payload.youtube_video_id)}`;
    link.hidden = false;
  }

  async function load() {
    try {
      const response = await fetch(`${DATA_URL}?t=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (error) {
      render({ intake_state: "blocked", blockers: [`PUBLICATION_RESULT_LOAD_FAILED: ${error.message}`] });
    }
  }

  byId("reload").addEventListener("click", load);
  load();
})();
