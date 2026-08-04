(() => {
  const $ = (id) => document.getElementById(id);
  const render = (data) => {
    $("state").textContent = data.intake_state || "BLOCKED";
    $("processing").textContent = data.processing_status || "—";
    $("privacy").textContent = data.privacy_status || "—";
    $("channel").textContent = data.youtube_channel_id || "—";
    $("videoId").textContent = data.youtube_video_id || "Sem vídeo";
    $("uploadId").textContent = data.upload_id || "—";
    $("embeddable").textContent = data.embeddable ? "Sim" : "Não";
    $("blockers").textContent = (data.blockers || []).join(", ") || "Nenhum";
    const thumb = $("thumbnail");
    if (data.thumbnail_url) { thumb.src = data.thumbnail_url; thumb.style.display = "block"; }
    const link = $("watchLink");
    if (data.watch_url) { link.href = data.watch_url; link.hidden = false; }
    const host = $("youtubePlayer");
    if (data.intake_state === "processed" && data.embeddable && data.youtube_video_id) {
      host.innerHTML = `<iframe title="YouTube video" width="100%" height="100%" src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(data.youtube_video_id)}" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
    }
  };
  fetch("data/youtube_upload_result_intake.json", {cache:"no-store"}).then((r) => r.json()).then(render).catch(() => {});
  $("importButton").addEventListener("click", () => $("fileInput").click());
  $("fileInput").addEventListener("change", async (event) => {
    const file = event.target.files[0]; if (!file) return;
    render(JSON.parse(await file.text()));
  });
})();