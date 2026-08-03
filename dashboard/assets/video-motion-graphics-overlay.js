(() => {
  'use strict';

  const TRACK_URL = 'data/video_factory_motion_graphics_track.json';
  const video = document.getElementById('previewVideo');
  const host = document.querySelector('.player-panel');
  if (!video || !host) return;

  host.style.position = host.style.position || 'relative';

  const layer = document.createElement('div');
  layer.id = 'motionGraphicsLayer';
  layer.setAttribute('aria-live', 'polite');
  Object.assign(layer.style, {
    position: 'absolute', inset: '0', pointerEvents: 'none', overflow: 'hidden',
    display: 'block', zIndex: '6'
  });
  host.appendChild(layer);

  const badge = document.createElement('div');
  badge.id = 'motionGraphicsStatus';
  badge.className = 'motion-graphics-status';
  badge.textContent = 'Motion graphics: NOT_LOADED';
  host.appendChild(badge);

  let track = null;
  let activeSignature = '';

  function safeArray(value) { return Array.isArray(value) ? value : []; }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }
  function validate(payload) {
    if (!payload || payload.schema !== 'football-shorts-ai.motion-graphics-track.v1') {
      throw new Error('Motion graphics schema inválido.');
    }
    if (!Array.isArray(payload.cues)) throw new Error('Motion graphics cues em falta.');
    return payload;
  }
  function timelineTime() {
    const segment = window.videoFactoryPreviewState?.currentSegment;
    if (!segment) return 0;
    const sourceStart = Number(segment.source_start_seconds || 0);
    const timelineStart = Number(segment.timeline_start_seconds || 0);
    const playbackRate = Number(segment.playback_rate || video.playbackRate || 1);
    return timelineStart + Math.max(0, video.currentTime - sourceStart) / playbackRate;
  }
  function positionStyle(position) {
    const map = {
      top_left: 'top:6%;left:5%;', top_center: 'top:6%;left:50%;transform:translateX(-50%);',
      top_right: 'top:6%;right:5%;', center: 'top:50%;left:50%;transform:translate(-50%,-50%);',
      bottom_left: 'bottom:9%;left:5%;', bottom_center: 'bottom:9%;left:50%;transform:translateX(-50%);',
      bottom_right: 'bottom:9%;right:5%;'
    };
    return map[position] || map.bottom_center;
  }
  function animationClass(value) { return `gfx-${String(value || 'none').replace(/[^a-z_]/g, '')}`; }
  function render() {
    if (!track || track.graphics_state !== 'composed') {
      layer.innerHTML = '';
      return;
    }
    const time = timelineTime();
    const active = safeArray(track.cues).filter((cue) => cue.overlay_allowed === true && time >= Number(cue.timeline_start_seconds) && time < Number(cue.timeline_end_seconds));
    const signature = active.map((cue) => cue.cue_id).join('|');
    if (signature === activeSignature) return;
    activeSignature = signature;
    layer.innerHTML = active.map((cue) => `
      <div class="motion-graphic ${escapeHtml(cue.kind)} ${animationClass(cue.animation_in)}" style="position:absolute;${positionStyle(cue.position)}">
        <strong>${escapeHtml(cue.primary_text)}</strong>
        ${cue.secondary_text ? `<span>${escapeHtml(cue.secondary_text)}</span>` : ''}
      </div>`).join('');
  }
  async function load() {
    try {
      const response = await fetch(TRACK_URL, {cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      track = validate(await response.json());
      badge.textContent = `Motion graphics: ${String(track.graphics_state).toUpperCase()}`;
      badge.dataset.state = track.graphics_state;
      render();
    } catch (error) {
      badge.textContent = `Motion graphics: BLOCKED (${error.message})`;
      badge.dataset.state = 'blocked';
      layer.innerHTML = '';
    }
  }

  video.addEventListener('timeupdate', render);
  video.addEventListener('seeking', render);
  video.addEventListener('loadedmetadata', render);
  window.videoFactoryMotionGraphics = { get track() { return track; }, render };
  load();
})();
