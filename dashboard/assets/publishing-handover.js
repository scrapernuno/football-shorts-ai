(() => {
  'use strict';
  const DATA_URL = 'data/controlled_render_result_intake.json';
  const state = { intake: null, decision: null };
  const $ = (id) => document.getElementById(id);

  function validate(payload) {
    if (!payload || payload.schema !== 'football-shorts-ai.render-result-intake.v1') throw new Error('Intake inválido.');
    return payload;
  }

  function update() {
    $('decisionState').textContent = state.decision ? state.decision.toUpperCase() : '—';
    const valid = Boolean(state.intake && state.intake.review_state === 'ready_for_review' && $('reviewer').value.trim() && $('note').value.trim() && state.decision);
    const approvedMetadata = state.decision !== 'approved' || ($('title').value.trim() && $('description').value.trim());
    $('exportButton').disabled = !(valid && approvedMetadata);
  }

  function evidence() {
    return {
      schema: 'football-shorts-ai.human-render-review-handover-request.v1',
      intake_id: state.intake?.intake_id || null,
      render_package_id: state.intake?.render_package_id || null,
      output_uri: state.intake?.output_uri || null,
      output_sha256: state.intake?.output_sha256 || null,
      reviewer: $('reviewer').value.trim(),
      decision: state.decision,
      review_note: $('note').value.trim(),
      title: $('title').value.trim(),
      description: $('description').value.trim(),
      tags: $('tags').value.split(',').map((x) => x.trim()).filter(Boolean).sort(),
      privacy_status: $('privacy').value,
      network_enabled: false,
      upload_enabled: false,
      publish_enabled: false,
      auto_publish: false
    };
  }

  function exportEvidence() {
    const blob = new Blob([JSON.stringify(evidence(), null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'human_render_review_handover.json';
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function load() {
    try {
      const response = await fetch(DATA_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.intake = validate(await response.json());
      $('handoverState').textContent = state.intake.review_state === 'ready_for_review' ? 'AWAITING DECISION' : 'BLOCKED';
      $('privacyState').textContent = $('privacy').value.toUpperCase();
      if (state.intake.review_state === 'ready_for_review' && state.intake.output_uri) {
        $('finalVideo').src = state.intake.output_uri.replace(/^dashboard\//, '');
        $('message').textContent = 'MP4 disponível para decisão humana. Upload e publicação continuam desativados.';
      } else {
        $('message').textContent = 'Resultado controlado ainda não disponível para revisão.';
      }
    } catch (error) {
      $('message').textContent = `Handover indisponível: ${error.message}`;
    }
    update();
  }

  document.querySelectorAll('[data-decision]').forEach((button) => button.addEventListener('click', () => {
    state.decision = button.dataset.decision;
    update();
  }));
  ['reviewer', 'title', 'description', 'tags', 'note'].forEach((id) => $(id).addEventListener('input', update));
  $('privacy').addEventListener('change', () => { $('privacyState').textContent = $('privacy').value.toUpperCase(); update(); });
  $('exportButton').addEventListener('click', exportEvidence);
  load();
})();
