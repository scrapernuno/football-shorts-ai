(() => {
  'use strict';
  const DATA_URL = 'data/controlled_render_result_intake.json';
  const $ = (id) => document.getElementById(id);
  const video = $('renderVideo');

  function validate(payload) {
    if (!payload || payload.schema !== 'football-shorts-ai.render-result-intake.v1') {
      throw new Error('Schema de intake inválido.');
    }
    if (payload.review_state !== 'ready_for_review') {
      throw new Error('Resultado ainda não está pronto para revisão.');
    }
    if (payload.publication_allowed !== false || payload.auto_publish !== false || payload.network_enabled !== false) {
      throw new Error('Capacidade proibida detetada.');
    }
    if (!payload.output_uri || !payload.output_sha256) throw new Error('Resultado incompleto.');
    return payload;
  }

  function browserUri(value) {
    const uri = String(value || '');
    return uri.startsWith('dashboard/') ? uri.slice('dashboard/'.length) : uri;
  }

  function render(payload) {
    const item = validate(payload);
    $('reviewState').textContent = item.review_state.toUpperCase();
    $('duration').textContent = `${Number(item.duration_seconds).toFixed(1)}s`;
    $('format').textContent = `${item.width}×${item.height}`;
    $('digest').textContent = `${item.output_sha256.slice(0, 12)}…`;
    $('executionId').textContent = item.execution_id;
    $('packageId').textContent = item.render_package_id;
    $('reviewer').textContent = item.reviewer;
    $('codecs').textContent = `${item.video_codec} / ${item.audio_codec}`;
    video.src = browserUri(item.output_uri);
    $('message').textContent = 'MP4 controlado disponível para revisão. Nenhuma publicação foi autorizada.';
  }

  fetch(DATA_URL, {cache: 'no-store'})
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(render)
    .catch((error) => {
      $('reviewState').textContent = 'BLOCKED';
      $('message').textContent = `Resultado indisponível: ${error.message}`;
      video.removeAttribute('src');
    });
})();
