/**
 * map.js — Leaflet Open-Source Map Controller with Multi-Provider Support
 * 100% Free Open-Source tiles: OpenStreetMap, Carto Dark Matter, Carto Voyager, OpenTopoMap.
 * Zero API keys required.
 */

export class MapController {
  constructor(elementId = 'map') {
    this.elementId = elementId;
    this.map = null;
    this.userMarker = null;
    this.accuracyCircle = null;
    this.itemMarker = null;
    this.currentTileLayer = null;
    this.currentStyle = 'dark';
    this.hasCentered = false;

    // 100% Free Public Open-Source Map Providers — NO API KEY EVER REQUIRED & NO WATERMARKS
    this.tileProviders = {
      dark: {
        name: 'Dark (OSM)',
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>'
        }
      },
      osm: {
        name: 'OpenStreetMap Standard',
        url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>'
        }
      },
      voyager: {
        name: 'Nature & Walking Trails',
        url: 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a> | CyclOSM'
        }
      }
    };
  }

  init(defaultLat = 13.0827, defaultLon = 80.2707) {
    if (this.map) {
      this.map.invalidateSize();
      return;
    }

    const container = document.getElementById(this.elementId);
    if (!container) return;

    try {
      this.map = L.map(this.elementId, {
        zoomControl: false,
        attributionControl: false
      }).setView([defaultLat, defaultLon], 16);

      // Add Zoom Control at bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(this.map);

      // Set initial tile layer (Watermark-free Dark OSM by default)
      this.setTileProvider(this.currentStyle);

      // Minimal attribution control
      L.control.attribution({ position: 'bottomleft', prefix: false })
        .addAttribution('&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a>')
        .addTo(this.map);

      // Recompute size on window resize
      window.addEventListener('resize', () => {
        if (this.map) this.map.invalidateSize();
      });

      // Quick timeout to ensure container dimensions are resolved
      setTimeout(() => {
        if (this.map) this.map.invalidateSize();
      }, 150);
    } catch (e) {
      console.error('Failed to initialize Leaflet map:', e);
    }
  }

  setTileProvider(styleKey) {
    if (!this.map) return;
    const provider = this.tileProviders[styleKey] || this.tileProviders.dark;
    this.currentStyle = styleKey;

    const mapContainer = document.getElementById(this.elementId);
    if (mapContainer) {
      if (styleKey === 'dark') {
        mapContainer.classList.add('map-dark-tiles');
      } else {
        mapContainer.classList.remove('map-dark-tiles');
      }
    }

    if (this.currentTileLayer) {
      this.map.removeLayer(this.currentTileLayer);
    }

    this.currentTileLayer = L.tileLayer(provider.url, provider.options);
    this.currentTileLayer.addTo(this.map);
  }

  toggleTheme() {
    const nextStyle = this.currentStyle === 'dark' ? 'osm' : 'dark';
    this.setTileProvider(nextStyle);
    return nextStyle;
  }

  updateUserPosition(lat, lon, accuracy_m = 5.0) {
    if (!this.map) this.init(lat, lon);

    if (!this.userMarker) {
      const userIcon = L.divIcon({
        className: 'user-location-marker-container',
        html: '<div class="user-location-marker"></div>',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });

      this.userMarker = L.marker([lat, lon], { icon: userIcon }).addTo(this.map);
      this.accuracyCircle = L.circle([lat, lon], {
        radius: accuracy_m,
        color: '#10b981',
        fillColor: '#10b981',
        fillOpacity: 0.15,
        weight: 1.5
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
      html: `<div class="drop-marker-available" title="${item.name || 'Drop Relic'}">✦</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18]
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
      this.map.setZoom(17);
    } else if (navigator.geolocation && this.map) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          this.updateUserPosition(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy || 10);
          this.map.setView([pos.coords.latitude, pos.coords.longitude], 17);
        },
        (err) => console.warn('Could not locate user:', err)
      );
    }
  }
}
