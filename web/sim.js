/**
 * sim.js — Desk simulator mode for TG Trails
 * Replays realistic GPS coordinates through the exact same client movement queue
 */

export class SimulatorController {
  constructor(onSampleGenerated) {
    this.onSampleGenerated = onSampleGenerated;
    this.samples = [];
    this.currentIndex = 0;
    this.intervalId = null;
    this.isRunning = false;
    this.speedMultiplier = 1;
  }

  async loadSamples() {
    try {
      const resp = await fetch('/scripts/sample_walk.json');
      if (resp.ok) {
        this.samples = await resp.json();
      } else {
        this.samples = this.getFallbackSamples();
      }
    } catch (e) {
      this.samples = this.getFallbackSamples();
    }
  }

  getFallbackSamples() {
    const baseLat = 13.0827;
    const baseLon = 80.2707;
    const list = [];
    for (let i = 0; i < 20; i++) {
      list.push({
        lat: baseLat + i * 0.00008,
        lon: baseLon + i * 0.00008,
        accuracy_m: 4.0
      });
    }
    return list;
  }

  async start() {
    if (this.samples.length === 0) {
      await this.loadSamples();
    }
    this.isRunning = true;
    this.currentIndex = 0;
    this.scheduleNextTick();
  }

  scheduleNextTick() {
    if (!this.isRunning) return;

    if (this.currentIndex >= this.samples.length) {
      this.currentIndex = 0; // Loop or finish
    }

    const current = this.samples[this.currentIndex];
    const now = Date.now() / 1000.0;

    if (this.onSampleGenerated) {
      this.onSampleGenerated({
        t: now,
        lat: current.lat,
        lon: current.lon,
        accuracy_m: current.accuracy_m || 4.5
      });
    }

    this.currentIndex++;
    const delay = 3000 / this.speedMultiplier;
    this.intervalId = setTimeout(() => this.scheduleNextTick(), delay);
  }

  stop() {
    this.isRunning = false;
    clearTimeout(this.intervalId);
  }

  toggle() {
    if (this.isRunning) {
      this.stop();
      return false;
    } else {
      this.start();
      return true;
    }
  }
}
