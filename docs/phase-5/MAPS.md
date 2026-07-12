# Maps and Geospatial Routing

## Goal
Integrate an interactive mapping engine using Leaflet.js and OpenStreetMap (OSRM) to visualize routes, geocode location inputs, and calculate trip distances automatically on the trip creation screen.

## Scope
- Embedding Leaflet.js interactive maps on the trip creation page.
- Asynchronous routing line rendering on coordinates selection.
- Automatic OSRM distance calculation and input injection.
- Dashboard maps displaying active vehicle markers using GeoJSON datasets.

## Responsibilities
- **Dispatcher / Fleet Manager**: Select source and destination points on the map to auto-fill routing fields.
- **Frontend Developer**: Set up Leaflet.js CDNs, manage map state hooks, and parse OSRM JSON payloads.

## Django App(s)
`trips` and `dashboard`

## Files to Create / Modify
```
trips/
  templates/
    trips/
      trip_form.html  # Modify to inject Leaflet container and scripts
dashboard/
  templates/
    dashboard/
      index.html      # Add map container for vehicle tracking
```

## Dependencies
- Phase 2 `trips` models and CRUD views.
- Leaflet.js CDN links and Leaflet Routing Machine CSS/JS packages.
- Public OpenStreetMap OSRM routing endpoint accessibility.

## Business Rules
1. **Distance Automation**: The "Planned Distance" input must not rely solely on manual entry. Selecting or updating coordinates for Source and Destination must trigger automatic OSRM distance queries.
2. **Measurement Normalization**: Distance parameters returned by OSRM (provided in meters) must be converted into kilometers (`meters / 1000`) and rounded to two decimal places before input injection.
3. **No Database GIS Requirement**: To avoid complex database engine setups (like PostGIS), store coordinate points as standard float columns (`latitude`, `longitude`) in the models, compiling them to GeoJSON format at query time.
4. **Fallback Handling**: If OSRM server queries fail (e.g., due to network timeouts), the distance input must unlock, allowing manual distance input fallback.

## Implementation Steps

### Step 1 — Import Leaflet CDNs in trip form
```html
<!-- trips/templates/trips/trip_form.html -->
{% extends "base.html" %}

{% block extra_head %}
<!-- Leaflet Styles -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.css" />
{% endblock %}

{% block content %}
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
  <!-- Form Container -->
  <div class="bg-white dark:bg-gray-800 p-6 rounded-lg shadow">
    <form id="trip-form" method="POST">
      {% csrf_token %}
      {{ form.as_p }}
      <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-md">Save Trip</button>
    </form>
  </div>

  <!-- Map Container -->
  <div class="rounded-lg shadow overflow-hidden h-[500px]">
    <div id="map" class="w-full h-full"></div>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet-routing-machine@3.2.12/dist/leaflet-routing-machine.js"></script>
<script>
  document.addEventListener("DOMContentLoaded", function() {
    // Initial map setup centered on default location
    const map = L.map('map').setView([28.6139, 77.2090], 13); // Default (New Delhi)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }).addTo(map);

    let routingControl = null;

    function calculateRoute(startLatLng, endLatLng) {
      if (routingControl) {
        map.removeControl(routingControl);
      }

      routingControl = L.Routing.control({
        waypoints: [
          L.latLng(startLatLng[0], startLatLng[1]),
          L.latLng(endLatLng[0], endLatLng[1])
        ],
        router: L.Routing.osrmv1({
          serviceUrl: 'https://router.project-osrm.org/route/v1'
        }),
        routeWhileDragging: false,
        show: false
      }).on('routesfound', function(e) {
        const routes = e.routes;
        const summary = routes[0].summary;
        // OSRM returns distance in meters. Convert to km.
        const distanceKm = (summary.totalDistance / 1000).toFixed(2);
        
        // Inject value into form field
        const distanceInput = document.querySelector('input[name="planned_distance"]');
        if (distanceInput) {
            distanceInput.value = distanceKm;
        }
      }).addTo(map);
    }

    // Dummy trigger points for demo. Wire actual input listeners here.
    calculateRoute([28.6139, 77.2090], [28.5355, 77.3910]);
  });
</script>
{% endblock %}
```

## Success Scenario
1. Dispatcher creates a new trip by opening the `/trips/create/` route.
2. The user inputs start and end address fields.
3. The routing engine plots the path lines on the map.
4. The Planned Distance input automatically updates to "12.80" km.

## Definition of Done
- [ ] Leaflet map initializes and displays tiles correctly.
- [ ] Coordinates selection feeds into the OSRM backend API.
- [ ] Response distance values are converted to kilometers and injected into the target form fields.
- [ ] User can manually override distance values if API requests fail.
- [ ] Route lines scale to fit maps bounds automatically.

## AI Instructions
- Ensure you set a static height/width on Leaflet map target divs; otherwise, maps will render with a size of zero pixels.
- Use passive event listeners or debounced input observers on coordinate fields to avoid dispatching repeated routing requests while users are typing.
- Always load Leaflet scripts securely using standard HTTPS links.
