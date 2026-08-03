(() => {
  'use strict';

  const DATA_URL = 'data/video_factory_thumbnail_composition.json';
  const state = { package: null, selectedCandidateId: null };
  const $ = (id) => document.getElementById(id);

  function safeArray(value) { return Array.isArray(value) ? value : []; }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }
  function browserUri(value) {
    const uri = String(value || '');
    return uri.startsWith('dashboard/') ? uri.slice('dashboard/'.length) : uri.replace(/^\.\//, '');
  }
  function validate(payload) {
    if (!payload || payload.schema !== 'football-shorts-ai.thumbnail-composition.v1') {
      throw new Error('Thumbnail schema inválido.');
    }
    if (!Array.isArray(payload.candidates)) throw new Error('Candidatos em falta.');
    return payload;
  }
  function render(payload) {
    state.package = validate(payload);
    state.selectedCandidateId = payload.selected_candidate_id || null;
    $('compositionState').textContent = String(payload.composition_state || 'blocked').toUpperCase();
    $('candidateCount').textContent = String(payload.candidates.length);
    $('selectedCandidate').textContent = state.selectedCandidateId || '—';
    $('thumbnailGrid').innerHTML = safeArray(payload.candidates).map((candidate) => {
      const allowed = candidate.preview_allowed === true && candidate.rights_status !== 'reference_only' && candidate.source_uri;
      return `
        <button class="thumbnail-card ${candidate.candidate_id === state.selectedCandidateId ? 'selected' : ''}"
                data-candidate-id="${escapeHtml(candidate.candidate_id)}" type="button" ${allowed ? '' : 'disabled'}>
          <div class="thumbnail-stage">
            ${allowed ? `<img src="${escapeHtml(browserUri(candidate.source_uri))}" alt="">` : ''}
            <div class="thumbnail-copy">
              <strong>${escapeHtml(candidate.headline || '')}</strong>
              <span>${escapeHtml(candidate.subheadline || '')}</span>
            </div>
          </div>
          <div class="thumbnail-meta">
            <strong>${escapeHtml(candidate.emotion || 'neutral')}</strong>
            <span>CTR score: ${Math.round(Number(candidate.click_potential_score || 0) * 100)}</span>
            <span>Legibilidade: ${Math.round(Number(candidate.text_readability_score || 0) * 100)}</span>
            <span>Direitos: ${escapeHtml(candidate.rights_status || 'unknown')}</span>
            ${allowed ? '' : `<span>BLOCKED: ${escapeHtml(safeArray(candidate.blockers).join(', ') || 'preview not allowed')}</span>`}
          </div>
        </button>`;
    }).join('') || '<p>Sem candidatos autorizados.</p>';

    document.querySelectorAll('[data-candidate-id]:not([disabled])').forEach((node) => {
      node.addEventListener('click', () => {
        state.selectedCandidateId = node.dataset.candidateId;
        render({...state.package, selected_candidate_id: state.selectedCandidateId});
      });
    });
    $('message').textContent = payload.composition_state === 'composed'
      ? 'Composição pronta para revisão. Nenhuma imagem é gerada ou publicada automaticamente.'
      : `Thumbnail bloqueada: ${safeArray(payload.blockers).join(', ') || 'evidência insuficiente'}.`;
  }
  async function loadDefault() {
    try {
      const response = await fetch(DATA_URL, {cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (error) {
      $('message').textContent = `Thumbnail indisponível: ${error.message}`;
    }
  }

  $('importButton').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try { render(JSON.parse(await file.text())); }
    catch (error) { $('message').textContent = `Importação falhou: ${error.message}`; }
  });
  loadDefault();
})();
