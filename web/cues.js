/**
 * cues.js — Audio & Haptic feedback system
 * Provides non-intrusive audio chimes and vibrations so walkers keep eyes on paths.
 */

class CueSystem {
  constructor() {
    this.audioCtx = null;
  }

  initAudio() {
    if (!this.audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    }
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  playReadyCue() {
    this.initAudio();
    // Two-tone rising chime (item unlocked)
    if (this.audioCtx) {
      const now = this.audioCtx.currentTime;
      const osc1 = this.audioCtx.createOscillator();
      const osc2 = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(587.33, now); // D5
      osc1.frequency.exponentialRampToValueAtTime(880.00, now + 0.15); // A5

      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);

      osc1.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc1.start(now);
      osc1.stop(now + 0.35);
    }

    // Vibration pattern: [200ms buzz, 100ms pause, 200ms buzz]
    if ('vibrate' in navigator) {
      try {
        navigator.vibrate([200, 100, 200]);
      } catch (e) {
        console.warn('Vibration failed', e);
      }
    }
  }

  playCollectedCue() {
    this.initAudio();
    // Bright major triad chime (item collected)
    if (this.audioCtx) {
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
      const now = this.audioCtx.currentTime;

      notes.forEach((freq, idx) => {
        const osc = this.audioCtx.createOscillator();
        const gain = this.audioCtx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + idx * 0.08);

        gain.gain.setValueAtTime(0.25, now + idx * 0.08);
        gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.08 + 0.25);

        osc.connect(gain);
        gain.connect(this.audioCtx.destination);

        osc.start(now + idx * 0.08);
        osc.stop(now + idx * 0.08 + 0.25);
      });
    }

    if ('vibrate' in navigator) {
      try {
        navigator.vibrate([150, 50, 250]);
      } catch (e) {
        console.warn('Vibration failed', e);
      }
    }
  }
}

export const cues = new CueSystem();
