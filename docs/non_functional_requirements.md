# FleetManager Non-Functional Requirements

## 1. Architectural Constraints
- **Technology stack:** Django 5.x, Django REST Framework, Postgres, Gunicorn, Nginx, Redis (optional), Python 3.12 virtual environment.
- **Deployment model:** Linux-based VM (e.g., Ubuntu 22.04) with systemd-managed Gunicorn workers and Nginx reverse proxy, as detailed in the project README.
- **API style:** RESTful endpoints with JSON payloads, schema described via `drf-spectacular`.
- **Multi-tenancy:** Logical isolation driven by `Organization` foreign keys; all domain models must preserve tenant context.

## 2. Performance & Scalability
- Support at least a few hundred concurrent API requests with <500 ms average response for CRUD operations under normal load.
- Paginate large datasets (default page size 20, up to 100) to bound query cost (`StandardResultsSetPagination`).
- Ensure ORM queries leverage indexes on frequently filtered columns (e.g., `organization_type`, `shipment_id`, `payment_date`).
- Permit horizontal scaling by adding Gunicorn workers/processes; application must remain stateless between requests.
- Background jobs (e.g., invoice recalculation) should be idempotent and safe to re-run if retried.

## 3. Availability & Reliability
- Target ≥99.5 % uptime for the API tier; downtime limited to scheduled maintenance windows.
- All auto-generated business identifiers (e.g., `shipment_id`, `invoice_id`) must be deterministic and collision-free even after restarts.
- Database migrations must provide forward compatibility, ensuring zero data loss through transactional schema changes.
- Enforce referential and check constraints at the database level to prevent corrupt states (e.g., positive weights, non-negative amounts, valid odometer ranges).

## 4. Security Requirements
- Enforce authentication for all APIs except explicit public endpoints; rely on `CustomUser` features such as account lockout, two-factor toggle, password expiry, and audit timestamps.
- Apply role-based access control (`Role`, `Permission`, `UserRole`) and guard API endpoints with RBAC checks from `utils.rbac`.
- Record security-sensitive events (login attempts, permission denials, account locks) using `SecurityEvent` with severity levels and IP/user agent metadata.
- Implement request throttling and brute-force prevention via `RateLimitTracker`, `LoginAttempt`, and optional `django-ratelimit`/`django-defender` integrations.
- Validate all regulated identifiers (PAN, GST, Aadhaar, IFSC, banking details) and sanitize file uploads to mitigate injection or malware risks.
- Support HTTPS termination at Nginx; disable insecure protocols and enforce modern TLS ciphers.

## 5. Data Protection & Privacy
- Store personally identifiable information (PII) only as required for logistics operations; restrict access by role and tenant.
- Securely store document uploads with controlled filesystem permissions; consider scanning for malware before persistence.
- Ensure data exports and backups are encrypted in transit and at rest; redact or mask sensitive fields in support logs.
- Provide mechanisms to purge or anonymize driver/owner data on request to satisfy data protection regulations.

## 6. Maintainability & Extensibility
- Maintain clear app boundaries (`entity`, `operations`, `financial`, `maintenance`, `users`, `configuration`) to localize domain logic.
- Use Django model mixins and validators to centralize reusable behaviors (address, contact, document storage, ID validation).
- Keep serializers and API views thin, deferring calculations to model service methods (e.g., `Invoice.calculate_totals`, `DriverAdvance.settle_and_carry_forward`).
- Ensure code remains type-annotation friendly and compatible with static analysis tools (mypy, pylint) for future automation.
- Document new endpoints via DRF Spectacular annotations to keep API docs accurate.

## 7. Observability & Logging
- Capture application logs (info, warning, error) with timestamps and correlation identifiers where feasible.
- Persist audit logs (`AuditLog`) for CRUD operations, including before/after snapshots, IP address, and session metadata.
- Provide structured responses for errors via `custom_exception_handler` to aid client debugging and centralized monitoring.
- Retain security logs for a minimum of 90 days to support forensic analysis.

## 8. Operational Management
- Package environment variables via `.env`/`python-decouple` to support multi-environment deployment (dev, UAT, prod).
- Use `collectstatic` and `whitenoise` for efficient static asset delivery; separate volume for media uploads.
- Monitor Gunicorn workers and queue lengths; configure systemd service for automatic restart on failure.
- Configure database connection pooling and health checks; integrate with PgBouncer if concurrency demands increase.
- Schedule cron or Celery tasks (future) for daily backups, invoice recalculations, and data cleanup.

## 9. Data Management & Integrity
- Enforce transactional consistency when updating financial aggregates (e.g., invoice totals, shipment totals) to prevent partial writes.
- Use Decimal arithmetic for all financial computations; prohibit floating-point rounding errors.
- Maintain deterministic document storage paths (e.g., per driver/vehicle) to avoid orphaned files during updates.
- Provide export utilities (CSV/Excel using `pandas`/`openpyxl`) for finance teams while honoring RBAC constraints.

## 10. Compliance & Governance
- Support auditability for financial records, including traceable links between invoices, payments, advances, and transactions.
- Retain financial and logistical records for at least 8 years to comply with Indian GST and accounting regulations.
- Ensure banking integrations capture UTR/reference numbers for statutory reconciliation and support RBI reporting when applicable.
- Maintain tyre and vehicle maintenance history to satisfy regional transport authority inspections.

## 11. Backup & Disaster Recovery
- Implement automated daily PostgreSQL backups (`pg_dump`) with retention and off-site replication as noted in README.
- Backup uploaded documents, static files, and configuration metadata alongside database dumps.
- Validate recovery objectives: RPO ≤ 24 h, RTO ≤ 4 h for production environments.
- Test restoration procedures quarterly to guarantee data integrity and playbook accuracy.

## 12. Testing & Quality Assurance
- Maintain unit and integration tests per Django app, especially for business-critical flows (freight calculation, driver advance settlement, invoice totals).
- Execute regression test suites before every deployment; integrate with CI pipelines.
- Use staging environments mirroring production configurations for acceptance testing.
- Validate schema migrations on staging before production rollout; include rollback plans.

## 13. Usability & Accessibility
- Provide consistent API contracts and descriptive error messages for client usability.
- Ensure admin or future UI surfaces expose human-readable IDs and calculated summaries for quick triage.
- Support CSV/Excel import/export flows to reduce manual data entry (future enhancement).
- Follow responsive design and accessibility guidelines if/when a public-facing UI is introduced.

## 14. Dependencies & Third-Party Services
- Core dependencies listed in `requirements.txt` must stay patched for security (Django, DRF, SimpleJWT, OAuth Toolkit, Redis).
- Monitor CVEs for cryptography libraries (`cryptography`, `PyJWT`) and apply updates promptly.
- Evaluate Redis deployment for rate limiting or caching; ensure persistence and failover when used in production.

## 15. Risk Management & Mitigation
- **Data quality risk:** mitigate through validators, database constraints, and admin review workflows.
- **Security breach risk:** address via RBAC, audit logging, 2FA, rate limiting, and TLS everywhere.
- **Operational downtime:** mitigate through redundant services, monitored systemd units, and documented recovery steps.
- **Regulatory non-compliance:** enforce document retention, traceable financial linkage, and audit capabilities.

