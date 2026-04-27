# Model & Admin API Overview

This document summarises the new `api/v1/models` model registry endpoints and the matching `api/v1/admin/models` management APIs.

## Model Registry (`/api/v1/models/…`)

- `GET /api/v1/models/`
  - Lists all exposed Django models (excluding `users`, `rbac`, banking details, and bank transfers).
  - Each entry includes app label, model name, verbose labels, field counts, and relation counts.

- `GET /api/v1/models/<app_label>/<model_name>/`
  - Returns detailed metadata including db_table, field descriptors, and relationship targets.

- `POST /api/v1/models/<app_label>/<model_name>/execute/`
  - Executes a read-only query (“inference”) using optional `filters`, `order_by`, and `limit` attributes in the request body.
  - Feature flag: `MODEL_API_FEATURE_FLAGS['model_inference']` (defaults to enabled).

- `GET /api/v1/models/<app_label>/<model_name>/versions/`
  - Lists migration files for the model's Django app to provide lightweight version tracking and change timestamps.

## Admin APIs (`/api/v1/admin/models/…`)

- Authenticated staff-only endpoints for CRUD operations on any exposed model.
- Feature flags:
  - `MODEL_API_FEATURE_FLAGS['model_admin_write']` (create/update)
  - `MODEL_API_FEATURE_FLAGS['model_admin_delete']` (delete)

### Routes

- `GET /api/v1/admin/models/<app>/<model>/`
  - Query and list instances. Accepts the same filter semantics as the inference endpoint plus a `limit` query parameter.

- `POST /api/v1/admin/models/<app>/<model>/`
  - Create a new instance. Payload is validated via `full_clean()` before persistence.

- `GET /api/v1/admin/models/<app>/<model>/<pk>/`
  - Retrieve a single instance for inspection.

- `PATCH|PUT /api/v1/admin/models/<app>/<model>/<pk>/`
  - Update an instance. Partial updates supported; cleaned via `full_clean()` before saving.

- `DELETE /api/v1/admin/models/<app>/<model>/<pk>/`
  - Remove an instance when delete feature flag is enabled.

### Logging & Monitoring

- All admin operations emit structured log entries (`model_admin_api` logger) containing user, action, payload, and path for downstream monitoring.

## Client Roadmap Highlights

1. **Discovery UI** – build a web dashboard that consumes the model registry list + metadata endpoints for interactive schema browsing.
2. **Data Browser** – leverage the admin endpoints to provide secured CRUD screens for internal operators (respect feature toggles per environment).
3. **Mobile/API Client** – encapsulate inference endpoints in a service SDK; reuse filters for mobile offline sync.
4. **Version Insights** – surface migration/version data within DevOps tooling to highlight schema change timelines and release notes.

