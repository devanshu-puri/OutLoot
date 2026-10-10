/**
 * sim.js — Desk simulator mode & dynamic random walk for TG Trails / OutLoot
 * Replays realistic GPS coordinates through the exact same client movement queue.
 * Seamlessly steers towards discoverable loot drops and wanders outdoor trails.
 */

export class SimulatorController {
  constructor(onSampleGenerated) {
    this.onSampleGenerated = onSampleGenerated;
    this.isRunning = false;
    this.intervalId = null;
    this.speedMultiplier = 1;

    // Current position state
    this.currentLat = 13.0827;
    this.currentLon = 80.2707;
    this.targetLat = null;
    this.targetLon = null;
    this.currentHeading = Math.random() * 360; // degrees
    this.stepSizeMeters = 3.8; // ~1.27 m/s at 3s interval (healthy walking pace)
  }

  setOrigin(lat, lon) {
    if (lat != null && lon != null) {
      this.currentLat = lat;
      this.currentLon = lon;
    }
  }

  setTarget(lat, lon) {
    this.targetLat = lat;
    this.targetLon = lon;
  }

  start(initialLat, initialLon, targetLat, targetLon) {
    if (initialLat != null && initialLon != null) {
      this.currentLat = initialLat;
      this.currentLon = initialLon;
    }
    if (targetLat != null && targetLon != null) {
      this.targetLat = targetLat;
      this.targetLon = targetLon;
    }
    this.isRunning = true;
    this.scheduleNextTick();
  }

  scheduleNextTick() {
    if (!this.isRunning) return;

    const now = Date.now() / 1000.0;
    this.step();

    if (this.onSampleGenerated) {
      this.onSampleGenerated({
        t: now,
        lat: this.currentLat,
        lon: this.currentLon,
        accuracy_m: 3.5 + Math.random() * 1.5,
        speed_mps: 1.25 + (Math.random() - 0.5) * 0.3
      });
    }

    const delay = 2500 / this.speedMultiplier;
    this.intervalId = setTimeout(() => this.scheduleNextTick(), delay);
  }

  step() {
    // If we have a target drop, orient towards it
    if (this.targetLat != null && this.targetLon != null) {
      const dLat = this.targetLat - this.currentLat;
      const dLon = this.targetLon - this.currentLon;
      const distDeg = Math.sqrt(dLat * dLat + dLon * dLon);

      // If we are extremely close (within ~10m ~ 0.00009 deg), clear target
      if (distDeg < 0.0001) {
        this.targetLat = null;
        this.targetLon = null;
      } else {
        // Target bearing with minor natural wander jitter (+/- 15 deg)
        let targetAngle = Math.atan2(dLon, dLat) * (180 / Math.PI);
        targetAngle += (Math.random() - 0.5) * 20;
        this.currentHeading = targetAngle;
      }
    } else {
      // Natural wandering walk: smoothly curve heading
      this.currentHeading += (Math.random() - 0.5) * 35;
    }

    // Convert heading & step distance to lat/lon delta
    const rad = (this.currentHeading * Math.PI) / 180;
    // 1 meter lat ≈ 0.000009 deg; 1 meter lon ≈ 0.000009 / cos(lat) deg
    const meters = this.stepSizeMeters + (Math.random() - 0.5) * 0.8;
    const deltaLat = (meters * Math.cos(rad)) / 111320;
    const deltaLon = (meters * Math.sin(rad)) / (111320 * Math.cos((this.currentLat * Math.PI) / 180));

    this.currentLat += deltaLat;
    this.currentLon += deltaLon;
  }

  stop() {
    this.isRunning = false;
    if (this.intervalId) {
      clearTimeout(this.intervalId);
      this.intervalId = null;
    }
  }

  toggle(currentLat, currentLon, targetLat, targetLon) {
    if (this.isRunning) {
      this.stop();
      return false;
    } else {
      this.start(currentLat, currentLon, targetLat, targetLon);
      return true;
    }
  }
}
