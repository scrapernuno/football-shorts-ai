(() => {
  'use strict';

  const TRACK_URL = 'data/video_factory_audio_mix_track.json';
  const video = document.getElementById('previewVideo');
  const host = document.querySelector('.player-panel');
  if (!video || !host) return;

  const badge = document.createElement('div');
  badge.id = 'audioMixStatus';
  badge.className = 'audio-mix-status';
  badge.textContent = 'Audio mix: NOT_LOADED';
  host.appendChild(badge);

  let track = null;
  const players = new Map();

  function safeArray(value) { return Array.isArray(value) ? value : []; }

  function validate(payload) {
    if (!payload || payload.schema !== 'football-shorts-ai.audio-mix-track.v1') {
      throw new Error('Audio mix schema inválido.');
    }
    if (!Array.isArray(payload.cues)) throw new Error('Audio mix cues em falta.');
    return payload;
  }

  function timelineTime() {
    const segment = window.videoFactoryPreviewState?.currentSegment;
    if (!segment) return 0;
    const sourceStart = Number(segment.source_start_seconds || 0);
    const timelineStart = Number(segment.timeline_start_seconds || 0);
    const rate = Number(segment.playback_rate || video.playbackRate || 1);
    return timelineStart + Math.max(0, video.currentTime - sourceStart) / rate;
  }

  function volumeFor(cue) {
    const baseDb = Number(cue.gain_db || 0);
    const voice = window.videoFactoryVoiceover?.track;
    const voiceActive = voice?.synchronization_state === 'synchronized' && !video.paused;
    const duckDb = voiceActive ? Number(cue.duck_under_voiceover_db || 0) : 0;
    return Math.max(0, Math.min(1, Math.pow(10, (baseDb + duckDb) / 20)));
  }

  function getPlayer(cue) {
    let audio = players.get(cue.cue_id);
    if (!audio) {
      audio = document.createElement('audio');
      audio.preload = 'metadata';
      audio.hidden = true;
      audio.src = cue.audio_uri;
      host.appendChild(audio);
      players.set(cue.cue_id, audio);
    }
    return audio;
  }

  async function sync() {
    if (!track || track.mix_state !== 'mixed') return;
    const time = timelineTime();
    const activeIds = new Set();

    for (const cue of safeArray(track.cues)) {
      const active = cue.audio_allowed === true &&
        time >= Number(cue.timeline_start_seconds) &&
        time < Number(cue.timeline_end_seconds);
      const audio = getPlayer(cue);
      if (!active) {
        if (!audio.paused) audio.pause();
        continue;
      }

      activeIds.add(cue.cue_id);
      const elapsed = Math.max(0, time - Number(cue.timeline_start_seconds));
      const desired = Number(cue.audio_start_seconds || 0) + elapsed;
      const cueDuration = Math.max(0.001, Number(cue.timeline_end_seconds) - Number(cue.timeline_start_seconds));
      const fadeIn = Math.min(1, elapsed / Math.max(Number(cue.fade_in_seconds || 0), 0.001));
      const remaining = Math.max(0, Number(cue.timeline_end_seconds) - time);
      const fadeOut = Math.min(1, remaining / Math.max(Number(cue.fade_out_seconds || 0), 0.001));
      audio.volume = volumeFor(cue) * Math.min(fadeIn, fadeOut);
      audio.loop = Boolean(cue.loop);
      if (Math.abs(audio.currentTime - desired) > 0.3) audio.currentTime = desired;
      if (!video.paused && audio.paused) {
        try { await audio.play(); } catch (_) { /* browser gesture policy */ }
      }
      if (video.paused && !audio.paused) audio.pause();
    }

    for (const [id, audio] of players) {
      if (!activeIds.has(id) && !audio.paused) audio.pause();
    }
  }

  function pauseAll() {
    for (const audio of players.values()) audio.pause();
  }

  async function load() {
    try {
      const response = await fetch(TRACK_URL, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      track = validate(await response.json());
      badge.textContent = `Audio mix: ${String(track.mix_state).toUpperCase()}`;
      badge.dataset.state = track.mix_state;
    } catch (error) {
      badge.textContent = `Audio mix: BLOCKED (${error.message})`;
      badge.dataset.state = 'blocked';
    }
  }

  video.addEventListener('timeupdate', sync);
  video.addEventListener('play', sync);
  video.addEventListener('pause', pauseAll);
  video.addEventListener('seeking', sync);
  video.addEventListener('ended', pauseAll);

  window.videoFactoryAudioMix = {
    get track() { return track; },
    sync,
    mute() { for (const audio of players.values()) audio.muted = true; },
    unmute() { for (const audio of players.values()) audio.muted = false; },
  };

  load();
})();
