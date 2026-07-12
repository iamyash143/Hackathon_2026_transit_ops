# Phase 5 — Advanced Features and Enhancements

## Objective
Integrate advanced capabilities into the TransitOps platform to elevate it to a production-ready standard. This includes document upload capabilities for fleet registry items, automated omnichannel notifications for credential compliance, leaflet-based mapping with routing integration, and a consistent system-wide dark mode configuration.

## Features Included
- **Document Management**: File storage for vehicle registrations and driver licenses, complete with validity check flags.
- **Email & SMS Notifications**: Omnichannel reminder notifications powered by django-anymail and Twilio helper APIs.
- **Geospatial Maps & Routing**: Dynamic mapping engine utilizing Leaflet.js and OpenStreetMap (OSRM) for visual route generation and distance calculation.
- **Tailwind Dark Mode**: Seamless theme switching with local storage persistence using Tailwind CSS v4 directives.

## Dependencies
- **Phase 1 (Foundation)**: Tailwind v4 stylesheet structure, HTML layouts, and base views.
- **Phase 2 (Core Modules)**: Models and fields for vehicles, drivers, and trips.
- **Phase 3 (Business Logic)**: Status transition automation, signals, and database triggers.
- **Phase 4 (Dashboard & Reports)**: Centralized view structures and user controls.

## Deliverables
- `docs/phase-5/README.md` (This file)
- `docs/phase-5/DOCUMENTS.md` (Document management, file fields, validation, and storage)
- `docs/phase-5/EMAILS.md` (Omnichannel Anymail and Twilio notification configurations)
- `docs/phase-5/MAPS.md` (Leaflet.js map display and distance injection logic)
- `docs/phase-5/DARK_MODE.md` (Persistent styling settings and theme switches)

## Success Criteria
- Files upload successfully to standard storage paths with clean validation rules.
- Drivers receive warning emails and SMS alerts before their license expires (warning triggers at 30, 15, and 5 days).
- Dispatchers view optimal routing lines on Leaflet maps, and planned distances automatically update.
- System layout updates color schemes immediately upon dark mode selection.

## Merge Target
`main` (or `develop`) after verifying integration of third-party libraries and testing the assets pipeline.
