(() => {
  'use strict';

  const TRACK_URL = 'data/video_factory_voiceover_track.json';
  const PREVIEW_URL = 'data/video_factory_preview_manifest.json';
  const video = document.getElementById('previewVideo');
  const host = document.querySelector('.player-panel');
  if (!video || !host) return;

  const audio = document.createElement('audio');
  audio.id = 'voiceoverAudio';
  audio.preload = 'metadata';
  audio.hidden = true;
  host.appendChild(audio);

  const badge = document.createElement('div');
  badge.id = 'voiceoverStatus';
  badge.className = 'voiceover-status';
  badge.textContent = 'Voiceover: NOT_LOADED';
  host.appendChild(badge);

  let track = null;
  let preview = null;
  let activeCueId = null;

  function safeArray(value) { return Array.isArray(value) ? value : []; }

  function validateTrack(payload) {
    if (!payload || payload.schema !== 'football-shorts-ai.voiceover-track.v1') {
      throw new Error('Voiceover schema inválido.');
    }
    if (!Array.isArray(payload.cues)) throw new Error('Voiceover cues em falta.');
    return payload;
  }

  function browserUri(value) {
    const uri = String(value || '');
    if (uri.startsWith('dashboard/')) return uri.slice('dashboard/'.length);
    if (uri.startsWith('./')) return uri.slice(2);
    return uri;
  }

  function currentSegment() {
    const src = video.getAttribute('src') || '';
    return safeArray(preview?.segments).find((segment) => {
      const sameSource = browserUri(segment.source_uri) === src;
      const start = Number(segment.source_start_seconds || 0);
      const end = Number(segment.source_end_seconds || 0);
      return sameSource && video.currentTime >= start - 0.1 && video.currentTime <= end + 0.1;
    }) || null;
  }

  function timelineTime() {
    const segment = currentSegment();
    if (!segment) return 0;
    const sourceStart = Number(segment.source_start_seconds || 0);
    const timelineStart = Number(segment.timeline_start_seconds || 0);
    const playbackRate = Number(segment.playback_rate || video.playbackRate || 1);
    return timelineStart + Math.max(0, video.currentTime - sourceStart) / playbackRate;
  }

  function activeCue(time) {
    return safeArray(track?.cues).find((cue) =>
      cue.audio_allowed === true &&
      time >= Number(cue.timeline_start_seconds) &&
      time < Number(cue.timeline_end_seconds)
    );
  }

  async function sync() {
    if (!track || track.synchronization_state !== 'synchronized') return;
    const now = timelineTime();
    const cue = activeCue(now);
    if (!cue) {
      audio.pause();
      activeCueId = null;
      return;
    }

    const desired = Number(cue.audio_start_seconds || 0) +
      Math.max(0, now - Number(cue.timeline_start_seconds || 0)) * Number(cue.playback_rate || 1);

    if (activeCueId !== cue.cue_id) {
      activeCueId = cue.cue_id;
      audio.src = browserUri(cue.audio_uri);
      audio.playbackRate = Number(cue.playback_rate || 1);
      audio.volume = Math.max(0, Math.min(1, Math.pow(10, Number(cue.gain_db || 0) / 20)));
      audio.currentTime = Math.max(0, desired);
    } else if (Math.abs(audio.currentTime - desired) > 0.25) {
      audio.currentTime = Math.max(0, desired);
    }

    if (!video.paused && audio.paused) {
      try { await audio.play(); } catch (_) { /* browser gesture policy */ }
    }
    if (video.paused && !audio.paused) audio.pause();
  }

  async function load() {
    try {
      const [trackResponse, previewResponse] = await Promise.all([
        fetch(TRACK_URL, { cache: 'no-store' }),
        fetch(PREVIEW_URL, { cache: 'no-store' }),
      ]);
      if (!trackResponse.ok) throw new Error(`voiceover HTTP ${trackResponse.status}`);
      if (!previewResponse.ok) throw new Error(`preview HTTP ${previewResponse.status}`);
      track = validateTrack(await trackResponse.json());
      preview = await previewResponse.json();
      badge.textContent = `Voiceover: ${String(track.synchronization_state).toUpperCase()}`;
      badge.dataset.state = track.synchronization_state;
    } catch (error) {
      badge.textContent = `Voiceover: BLOCKED (${error.message})`;
      badge.dataset.state = 'blocked';
    }
  }

  video.addEventListener('timeupdate', sync);
  video.addEventListener('play', sync);
  video.addEventListener('pause', () => audio.pause());
  video.addEventListener('seeking', sync);
  video.addEventListener('ended', () => audio.pause());

  window.videoFactoryVoiceover = {
    get track() { return track; },
    sync,
    mute() { audio.muted = true; },
    unmute() { audio.muted = false; },
  };

  load();
})();
