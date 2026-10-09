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

    // Free Open-Source Tile Providers (No API Key Required)
    this.tileProviders = {
      dark: {
        name: 'Dark Matter',
        url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abcd',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OSM</a> &copy; <a href="https://carto.com" target="_blank">CARTO</a>'
        }
      },
      osm: {
        name: 'OpenStreetMap',
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OpenStreetMap</a> contributors'
        }
      },
      voyager: {
        name: 'Outdoor Voyager',
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        options: {
          maxZoom: 19,
          subdomains: 'abcd',
          attribution: '&copy; <a href="https://openstreetmap.org" target="_blank">OSM</a> &copy; <a href="https://carto.com" target="_blank">CARTO</a>'
        }
      },
      topo: {
        name: 'OpenTopoMap',
        url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        options: {
          maxZoom: 17,
          subdomains: 'abc',
          attribution: '&copy; <a href="https://opentopomap.org" target="_blank">OpenTopoMap</a> &copy; <a href="https://openstreetmap.org" target="_blank">OSM</a>'
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

      // Set initial tile layer (Carto Dark Matter by default)
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
    const provider = this.tileProviders[styleKey] || this.tileProviders.osm;
    this.currentStyle = styleKey;

    if (this.currentTileLayer) {
      this.map.removeLayer(this.currentTileLayer);
    }

    this.currentTileLayer = L.tileLayer(provider.url, provider.options);
    
    // Automatic fallback to OpenStreetMap standard if tile fails
    this.currentTileLayer.on('tileerror', () => {
      if (this.currentStyle !== 'osm') {
        console.warn(`Tile provider '${this.currentStyle}' error, falling back to OpenStreetMap`);
        this.setTileProvider('osm');
      }
    });

    this.currentTileLayer.addTo(this.map);
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
