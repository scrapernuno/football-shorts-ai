(() => {
  'use strict';

  const TRACK_URL = 'data/video_factory_subtitle_track.json';
  const MANIFEST_URL = 'data/video_factory_preview_manifest.json';
  const video = document.getElementById('previewVideo');
  if (!video) return;

  const frame = video.parentElement;
  const overlay = document.createElement('div');
  overlay.id = 'subtitleOverlay';
  overlay.className = 'subtitle-overlay';
  overlay.setAttribute('aria-live', 'polite');
  frame.style.position = 'relative';
  frame.appendChild(overlay);

  const style = document.createElement('style');
  style.textContent = `
    .subtitle-overlay{position:absolute;left:7%;right:7%;bottom:5.5rem;text-align:center;
      font:800 clamp(1rem,2.4vw,1.65rem)/1.18 system-ui,sans-serif;color:#fff;
      text-shadow:0 2px 4px #000,0 0 12px #000;pointer-events:none;z-index:4}
    .subtitle-overlay span{display:inline;padding:.18em .42em;background:rgba(0,0,0,.58);
      box-decoration-break:clone;-webkit-box-decoration-break:clone;border-radius:.25rem}
    .subtitle-overlay:empty{display:none}`;
  document.head.appendChild(style);

  let track = null;
  let manifest = null;

  const safeArray = (value) => Array.isArray(value) ? value : [];
  const normalize = (value) => String(value || '').split('/').pop();

  function timelineTime() {
    const source = normalize(video.currentSrc || video.getAttribute('src'));
    const segment = safeArray(manifest?.segments).find((item) => normalize(item.source_uri) === source);
    if (!segment) return null;
    const local = Math.max(0, Number(video.currentTime) - Number(segment.source_start_seconds || 0));
    const rate = Number(segment.playback_rate || 1);
    return Number(segment.timeline_start_seconds || 0) + local / rate;
  }

  function update() {
    if (track?.subtitle_state !== 'generated') {
      overlay.textContent = '';
      return;
    }
    const time = timelineTime();
    const cue = time === null ? null : safeArray(track.cues).find((item) =>
      time >= Number(item.start_seconds) && time < Number(item.end_seconds));
    overlay.innerHTML = cue ? `<span>${escapeHtml(cue.text)}</span>` : '';
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[char]));
  }

  Promise.all([
    fetch(TRACK_URL, {cache:'no-store'}).then((response) => response.ok ? response.json() : null),
    fetch(MANIFEST_URL, {cache:'no-store'}).then((response) => response.ok ? response.json() : null)
  ]).then(([loadedTrack, loadedManifest]) => {
    track = loadedTrack;
    manifest = loadedManifest;
    update();
  }).catch(() => { overlay.textContent = ''; });

  video.addEventListener('timeupdate', update);
  video.addEventListener('loadedmetadata', update);
  video.addEventListener('seeked', update);
})();
