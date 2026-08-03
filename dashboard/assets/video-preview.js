(() => {
  'use strict';

  const DATA_URL = 'data/video_factory_preview_manifest.json';
  const state = { manifest: null, segments: [], index: 0, playing: false };
  const $ = (id) => document.getElementById(id);
  const video = $('previewVideo');

  function safeArray(value) { return Array.isArray(value) ? value : []; }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }

  function validateManifest(payload) {
    if (!payload || typeof payload !== 'object') throw new Error('Manifesto inválido.');
    if (payload.schema !== 'football-shorts-ai.video-factory-preview.v1') throw new Error('Schema não suportado.');
    if (payload.preview_state !== 'preview_ready') throw new Error('Preview não autorizado.');
    const segments = safeArray(payload.segments);
    if (!segments.length) throw new Error('Sem segmentos para reproduzir.');
    for (const segment of segments) {
      if (segment.preview_allowed !== true) throw new Error('Segmento sem autorização de preview.');
      if (segment.rights_status === 'reference_only') throw new Error('Conteúdo reference_only bloqueado.');
      if (!segment.source_uri) throw new Error('Fonte do segmento em falta.');
      if (!(Number(segment.source_end_seconds) > Number(segment.source_start_seconds))) throw new Error('Intervalo inválido.');
    }
    return payload;
  }

  function current() { return state.segments[state.index] || null; }

  function sourceToBrowserUri(value) {
    const uri = String(value || '');
    if (uri.startsWith('dashboard/')) return uri.slice('dashboard/'.length);
    if (uri.startsWith('./')) return uri.slice(2);
    return uri;
  }

  function render() {
    const segment = current();
    $('previewState').textContent = String(state.manifest?.preview_state || 'NOT_LOADED').toUpperCase();
    $('segmentPosition').textContent = segment ? `${state.index + 1} / ${state.segments.length}` : '0 / 0';
    $('currentRole').textContent = segment?.editorial_role || '—';
    $('totalDuration').textContent = `${Number(state.manifest?.total_duration_seconds || 0).toFixed(1)}s`;
    $('beatTitle').textContent = segment?.editorial_role || 'Sem preview';
    $('scriptText').textContent = segment?.script_text || 'Sem texto associado.';
    $('clipId').textContent = segment?.clip_id || '—';
    $('sourceUri').textContent = segment?.source_uri || '—';
    $('sourceRange').textContent = segment ? `${segment.source_start_seconds}s → ${segment.source_end_seconds}s` : '—';
    $('transition').textContent = segment?.transition || 'cut';
    $('timeline').innerHTML = state.segments.map((item, index) => `
      <button class="timeline-item ${index === state.index ? 'active' : ''}" data-index="${index}" type="button">
        <strong>${escapeHtml(item.editorial_role || 'segment')}</strong>
        <span>${escapeHtml(item.timeline_start_seconds ?? 0)}s–${escapeHtml(item.timeline_end_seconds ?? 0)}s</span>
      </button>`).join('');
    document.querySelectorAll('[data-index]').forEach((node) => node.addEventListener('click', () => loadSegment(Number(node.dataset.index), state.playing)));
    updateProgress();
  }

  function loadSegment(index, autoplay = false) {
    if (!state.segments.length) return;
    state.index = Math.max(0, Math.min(index, state.segments.length - 1));
    const segment = current();
    state.playing = Boolean(autoplay);
    const nextSource = sourceToBrowserUri(segment.source_uri);
    if (video.getAttribute('src') !== nextSource) video.src = nextSource;
    video.playbackRate = Number(segment.playback_rate || 1);
    const seek = () => {
      video.currentTime = Number(segment.source_start_seconds);
      if (autoplay) video.play().catch((error) => { $('message').textContent = `Reprodução bloqueada: ${error.message}`; });
      render();
    };
    if (video.readyState >= 1) seek(); else video.addEventListener('loadedmetadata', seek, {once: true});
  }

  function updateProgress() {
    const segment = current();
    if (!segment) { $('progressValue').style.width = '0%'; return; }
    const start = Number(segment.source_start_seconds);
    const end = Number(segment.source_end_seconds);
    const ratio = Math.max(0, Math.min(1, (video.currentTime - start) / Math.max(end - start, 0.001)));
    $('progressValue').style.width = `${ratio * 100}%`;
  }

  function onTimeUpdate() {
    const segment = current();
    if (!segment) return;
    updateProgress();
    if (video.currentTime < Number(segment.source_end_seconds) - 0.03) return;
    if ($('loopSegment').checked) return loadSegment(state.index, true);
    if (state.index < state.segments.length - 1) return loadSegment(state.index + 1, true);
    video.pause(); state.playing = false; $('playButton').textContent = '▶ Reproduzir';
  }

  function applyManifest(payload) {
    state.manifest = validateManifest(payload);
    state.segments = safeArray(payload.segments);
    state.index = 0;
    state.playing = false;
    $('message').textContent = 'Manifesto autorizado. Nenhum ficheiro é descarregado, extraído, renderizado ou publicado.';
    loadSegment(0, false);
  }

  async function loadDefault() {
    try {
      const response = await fetch(DATA_URL, {cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      applyManifest(await response.json());
    } catch (error) {
      $('message').textContent = `Preview indisponível: ${error.message}`;
    }
  }

  $('playButton').addEventListener('click', () => {
    if (!current()) return;
    if (video.paused) {
      state.playing = true;
      if (video.currentTime < Number(current().source_start_seconds) || video.currentTime >= Number(current().source_end_seconds)) {
        video.currentTime = Number(current().source_start_seconds);
      }
      video.play().catch((error) => { $('message').textContent = `Reprodução bloqueada: ${error.message}`; });
    } else { video.pause(); state.playing = false; }
  });
  $('previousButton').addEventListener('click', () => loadSegment(state.index - 1, state.playing));
  $('nextButton').addEventListener('click', () => loadSegment(state.index + 1, state.playing));
  $('importButton').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try { applyManifest(JSON.parse(await file.text())); }
    catch (error) { $('message').textContent = `Importação falhou: ${error.message}`; }
  });
  video.addEventListener('timeupdate', onTimeUpdate);
  video.addEventListener('play', () => { state.playing = true; $('playButton').textContent = '⏸ Pausar'; });
  video.addEventListener('pause', () => { state.playing = false; $('playButton').textContent = '▶ Reproduzir'; });
  video.addEventListener('error', () => { $('message').textContent = 'O ficheiro autorizado não está acessível ao navegador.'; });

  loadDefault();
})();
