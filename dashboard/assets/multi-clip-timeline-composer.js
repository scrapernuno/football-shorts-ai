(() => {
  'use strict';
  const DATA_URL = 'data/video_factory_preview_manifest.json';
  const host = document.getElementById('multiClipComposer');
  if (!host) return;

  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const num = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;

  function compose(payload) {
    const segments = Array.isArray(payload?.segments) ? payload.segments : [];
    let cursor = 0;
    return segments.map((item, index) => {
      const sourceStart = num(item.source_start_seconds ?? item.start_seconds);
      const sourceEnd = num(item.source_end_seconds ?? item.end_seconds);
      const rate = Math.max(.25, num(item.playback_rate) || 1);
      const duration = Math.max(0, (sourceEnd - sourceStart) / rate);
      const result = {...item, index, sourceStart, sourceEnd, rate, timelineStart: cursor, timelineEnd: cursor + duration, duration};
      cursor += duration;
      return result;
    });
  }

  function render(payload) {
    const clips = compose(payload);
    const total = clips.length ? clips[clips.length - 1].timelineEnd : 0;
    host.innerHTML = `
      <div class="section-heading"><div><p class="eyebrow">0060C · MULTI-CLIP COMPOSER</p><h2>Montagem contínua</h2></div><span class="count-badge">${clips.length} clips · ${total.toFixed(1)}s</span></div>
      <div style="display:flex;min-height:74px;border:1px solid rgba(148,163,184,.25);border-radius:12px;overflow:hidden;background:#07111f">
        ${clips.map((clip) => {
          const width = total > 0 ? Math.max(8, clip.duration / total * 100) : 100;
          const blocked = clip.preview_allowed !== true || (Array.isArray(clip.blockers) && clip.blockers.length);
          return `<button type="button" data-composer-index="${clip.index}" title="${esc(clip.clip_id)}" style="width:${width}%;border:0;border-right:1px solid rgba(148,163,184,.25);padding:.65rem;text-align:left;background:${blocked ? '#321722' : '#11243a'};color:#e5edf7;cursor:pointer">
            <strong style="display:block;text-transform:uppercase;font-size:.72rem">${esc(clip.role || 'clip')}</strong>
            <span style="display:block;font-size:.72rem;opacity:.75">${clip.timelineStart.toFixed(1)}–${clip.timelineEnd.toFixed(1)}s</span>
          </button>`;
        }).join('') || '<p style="padding:1rem">Sem clips compostos.</p>'}
      </div>
      <div style="display:flex;justify-content:space-between;margin-top:.5rem;font-size:.75rem;opacity:.7"><span>00:00</span><span>${total.toFixed(1)}s</span></div>`;

    host.querySelectorAll('[data-composer-index]').forEach((button) => button.addEventListener('click', () => {
      const timelineButtons = document.querySelectorAll('#timeline [data-index], #timeline button, #timeline article');
      const target = timelineButtons[Number(button.dataset.composerIndex)];
      if (target instanceof HTMLElement) target.click();
    }));
  }

  fetch(DATA_URL, {cache: 'no-store'})
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then(render)
    .catch((error) => { host.innerHTML = `<p class="message">Compositor indisponível: ${esc(error.message)}</p>`; });
})();
