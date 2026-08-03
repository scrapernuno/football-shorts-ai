(() => {
  'use strict';

  const DATA_URL = 'data/ai_director_review_package.json';
  const state = { package: null, selectedVariantId: null, decision: null };
  const $ = (id) => document.getElementById(id);

  function safeArray(value) { return Array.isArray(value) ? value : []; }
  function score(value) { return Number.isFinite(Number(value)) ? `${Math.round(Number(value) * (Number(value) <= 1 ? 100 : 1))}` : '—'; }
  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  }

  function validatePackage(payload) {
    if (!payload || typeof payload !== 'object') throw new Error('Pacote inválido.');
    if (payload.schema !== 'football-shorts-ai.ai-director-review.v1') throw new Error('Schema não suportado.');
    if (!Array.isArray(payload.variants)) throw new Error('Variantes em falta.');
    return payload;
  }

  function render(payload) {
    state.package = validatePackage(payload);
    state.selectedVariantId = payload.recommended_variant_id || payload.variants[0]?.variant_id || null;
    $('directorState').textContent = String(payload.director_state || 'NOT_LOADED').toUpperCase();
    $('recommendedVariant').textContent = state.selectedVariantId || '—';
    $('handoverState').textContent = String(payload.handover_state || 'BLOCKED').toUpperCase();
    const recommended = payload.variants.find((item) => item.variant_id === state.selectedVariantId);
    $('viralScore').textContent = score(recommended?.viral_potential_score);
    renderVariants();
    renderTimeline();
    updateReviewControls();
  }

  function renderVariants() {
    $('variantGrid').innerHTML = safeArray(state.package?.variants).map((variant) => `
      <article class="variant ${variant.variant_id === state.selectedVariantId ? 'selected' : ''}" data-variant-id="${escapeHtml(variant.variant_id)}">
        <p class="eyebrow">${escapeHtml(variant.strategy || 'variant')}</p>
        <h3>${escapeHtml(variant.title || variant.variant_id)}</h3>
        <div class="metric"><span>Hook</span><strong>${score(variant.hook_score)}</strong></div>
        <div class="metric"><span>Retenção</span><strong>${score(variant.retention_score)}</strong></div>
        <div class="metric"><span>Viral</span><strong>${score(variant.viral_potential_score)}</strong></div>
        <div class="metric"><span>Duração</span><strong>${escapeHtml(variant.duration_seconds ?? '—')}s</strong></div>
      </article>`).join('') || '<p>Sem variantes disponíveis.</p>';

    document.querySelectorAll('[data-variant-id]').forEach((node) => {
      node.addEventListener('click', () => {
        state.selectedVariantId = node.dataset.variantId;
        state.decision = null;
        renderVariants();
        renderTimeline();
        updateReviewControls();
      });
    });
  }

  function renderTimeline() {
    const variant = safeArray(state.package?.variants).find((item) => item.variant_id === state.selectedVariantId);
    $('timeline').innerHTML = safeArray(variant?.beats).map((beat) => `
      <article class="beat">
        <strong>${escapeHtml(beat.role || 'beat')}</strong>
        <div><p>${escapeHtml(beat.script_text || '')}</p><small>${escapeHtml(beat.clip_id || '')}</small></div>
        <small>${escapeHtml(beat.timeline_start_seconds ?? 0)}s → ${escapeHtml(beat.timeline_end_seconds ?? 0)}s<br>${escapeHtml(beat.transition || 'cut')}</small>
      </article>`).join('') || '<p>Sem timeline para esta variante.</p>';
  }

  function updateReviewControls() {
    const reviewer = $('reviewer').value.trim();
    const valid = Boolean(state.package && state.selectedVariantId && reviewer);
    $('exportButton').disabled = !(valid && state.decision);
    $('reviewMessage').textContent = state.decision
      ? `Decisão preparada: ${state.decision}. A exportação não renderiza nem publica.`
      : 'Selecione uma variante, indique o revisor e registe a decisão.';
  }

  function makeEvidence() {
    return {
      schema: 'football-shorts-ai.ai-director-human-review.v1',
      source_package_id: state.package.package_id || null,
      selected_variant_id: state.selectedVariantId,
      reviewer: $('reviewer').value.trim(),
      decision: state.decision,
      notes: $('notes').value.trim(),
      factory_handover_requested: state.decision === 'approved',
      extraction_enabled: false,
      render_enabled: false,
      auto_publish: false
    };
  }

  function exportEvidence() {
    const blob = new Blob([JSON.stringify(makeEvidence(), null, 2)], {type: 'application/json'});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'ai_director_review_evidence.json';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function loadDefault() {
    try {
      const response = await fetch(DATA_URL, {cache: 'no-store'});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (error) {
      $('reviewMessage').textContent = `Pacote não carregado: ${error.message}`;
    }
  }

  $('importButton').addEventListener('click', () => $('fileInput').click());
  $('fileInput').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try { render(JSON.parse(await file.text())); }
    catch (error) { $('reviewMessage').textContent = `Importação falhou: ${error.message}`; }
  });
  $('reviewer').addEventListener('input', updateReviewControls);
  document.querySelectorAll('[data-decision]').forEach((button) => button.addEventListener('click', () => {
    state.decision = button.dataset.decision;
    updateReviewControls();
  }));
  $('exportButton').addEventListener('click', exportEvidence);

  loadDefault();
})();
