/**
 * map.js — Leaflet dark-styled map controller
 */

export class MapController {
  constructor(elementId = 'map') {
    this.elementId = elementId;
    this.map = null;
    this.userMarker = null;
    this.accuracyCircle = null;
    this.itemMarker = null;
    this.hasCentered = false;
  }

  init(defaultLat = 13.0827, defaultLon = 80.2707) {
    if (this.map) return;

    this.map = L.map(this.elementId, {
      zoomControl: false,
      attributionControl: false
    }).setView([defaultLat, defaultLon], 16);

    // CartoDB Dark Matter tiles (clean, high contrast for night/outdoor readability)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
    }).addTo(this.map);

    // Add minimal attribution
    L.control.attribution({ position: 'bottomright', prefix: false })
      .addAttribution('&copy; <a href="https://openstreetmap.org" target="_blank">OSM</a>')
      .addTo(this.map);
  }

  updateUserPosition(lat, lon, accuracy_m = 5.0) {
    if (!this.map) this.init(lat, lon);

    if (!this.userMarker) {
      const userIcon = L.divIcon({
        className: 'user-location-marker-container',
        html: '<div class="user-location-marker"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9]
      });

      this.userMarker = L.marker([lat, lon], { icon: userIcon }).addTo(this.map);
      this.accuracyCircle = L.circle([lat, lon], {
        radius: accuracy_m,
        color: '#3b82f6',
        fillColor: '#3b82f6',
        fillOpacity: 0.15,
        weight: 1
      }).addTo(this.map);
    } else {
      this.userMarker.setLatLng([lat, lon]);
      this.accuracyCircle.setLatLng([lat, lon]);
      this.accuracyCircle.setRadius(accuracy_m);
    }

    if (!this.hasCentered) {
      this.map.setView([lat, lon], 17);
      this.hasCentered = true;
    }
  }

  updateItemDrop(item, userLat, userLon, onMarkerClick) {
    if (!this.map) return;

    if (!item || item.status !== 'AVAILABLE' || !item.lat || !item.lon) {
      if (this.itemMarker) {
        this.map.removeLayer(this.itemMarker);
        this.itemMarker = null;
      }
      return;
    }

    const itemIcon = L.divIcon({
      className: 'drop-marker-container',
      html: `<div class="drop-marker-available">✦</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    if (!this.itemMarker) {
      this.itemMarker = L.marker([item.lat, item.lon], { icon: itemIcon }).addTo(this.map);
      if (onMarkerClick) {
        this.itemMarker.on('click', onMarkerClick);
      }
    } else {
      this.itemMarker.setLatLng([item.lat, item.lon]);
    }
  }

  centerOnUser() {
    if (this.userMarker && this.map) {
      this.map.panTo(this.userMarker.getLatLng());
    }
  }
}
