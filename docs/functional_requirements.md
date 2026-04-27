# FleetManager Functional Requirements

## 1. Product Vision
- Provide an end-to-end logistics and fleet operations platform for Indian trucking companies, brokers, transporters, and finance teams.
- Deliver a single source of truth for entities (organizations, vehicles, drivers), shipment execution, financial settlement, and maintenance compliance.
- Offer extensible REST APIs that mirror the Django admin domain model for partner integrations and future mobile apps.

## 2. Solution Scope
- Web-based management console powered by Django and Django REST Framework.
- Multi-tenant data segregation anchored on `Organization` records so different brokers, transporters, owners, and shippers can co-exist.
- Public REST APIs (`/api/v1/...`) for CRUD operations, analytics views, and downstream integrations.
- Postgres-backed persistence with document storage for regulatory artefacts.

## 3. User Personas & Responsibilities
- **System Administrator** – provisions tenants, seeds configuration choices, manages staff users.
- **Operations Manager** – orchestrates consignments, shipment planning, driver and vehicle assignments.
- **Broker / Transporter Coordinators** – maintain partner rosters, route preferences, vehicle capability data.
- **Owner & Driver App Users** – maintain personal data, upload compliance documents, review advances and expenses.
- **Finance Team** – reconciles advances, captures shipment expenses, issues invoices, allocates bank transfers, posts office expenses.
- **Maintenance Supervisor** – records maintenance jobs, tyre lifecycle events, and compliance due dates.

## 4. End-to-End Workflow Overview
- Register or import tenant organizations, their banking routes, and configuration master data.
- Onboard owners, drivers, vehicles, transporters, and brokers with validation and document evidence.
- Capture consignments, group them into dispatch batches, and create shipments with assigned assets and crew.
- Track shipment lifecycle with status updates, odometer readings, and planned vs. actual route metadata.
- Record operational finances: shipment expenses, driver advances, office expenses, and resulting transactions.
- Raise invoices for consignment groups or shipments, accept payments, and execute bank transfers.
- Maintain fleet compliance through maintenance records, tyre transactions, and document expiry monitoring.

## 5. Functional Modules & Detailed Requirements

### 5.1 Tenant & Organization Administration
- Create and update organizations with address autofill driven by Indian pincodes (`Organization.auto_populate_from_pincode`).
- Categorize organizations as broker, transporter, consignor/consignee, or owner and filter by type.
- Store PAN, GST, and TDS declaration artefacts; ensure PAN formats pass `pan_validator` and GST uses `gst_validator`.
- Associate organizations to operating routes (`configuration.Route`) for logistics planning.

### 5.2 Master Data & Configuration
- Manage reusable choice dictionaries via `configuration.Choice` for titles, genders, vehicle specs, maintenance types, payment modes, etc.
- Maintain geo routing master data (`Route`, `Location`) via authenticated API endpoints.
- Store banking coordinates (`BankingDetail`) with IFSC and account validation to support payments and bank transfers.
- Import India postal directory (`PostalInfo`) and expose lookup for address enrichment.

### 5.3 Entity Lifecycle Management
- Owners, brokers, transporters, and drivers inherit common mixins (address, contact, documents) and must adhere to validators for Aadhaar, phone, email, etc.
- Drivers must belong to an owner organization (`Driver.owner`), supply license details, family contact info, and maintain compliance expiry tracking.
- Vehicles require unique registration and chassis numbers, categorical specifications, ownership links, and compliance due date tracking.
- Support driver and vehicle document libraries (`DriverDocument`, `VehicleDocument`) with typed uploads and expiry metadata.

### 5.4 Logistics Operations
- Create consignments capturing consignor/consignee organizations, goods metadata, weight/volume, packaging, and freight pricing mode.
- Prevent consignor = consignee and auto-compute total freight based on rate, weight, and selected freight mode.
- Manage consignment groups that batch consignments for a dispatch slot; auto-generate group IDs; compute aggregate totals.
- Create shipments from consignment groups with assigned vehicle, driver, co-driver, transporter, broker, planned/actual timings, odometer readings, and route.
- Derive shipment IDs, calculate distance from odometer readings, and maintain total freight from linked consignments.
- Track shipment status progression with document uploads (e.g., POD, invoices) and audit fields.

### 5.5 Operational Finance
- Record shipment expenses with typed categories (`EXPENSE_TYPES`), receipts, and attribution to drivers or owners via generic relations.
- Manage driver advances with payer attribution (owner or shipment), enforce app-label validation, and carry forward unsettled balances.
- Provide driver advance summaries, per-shipment breakdowns, and settlement endpoints (`settle_and_carry_forward`).

### 5.6 Financial Accounting
- Auto-create invoices for shipments or consignment groups, calculating total freight, advances, expenses, dues, and payment status.
- Maintain payments with method, status, bank charges, cheque lifecycle, and bidirectional banking details.
- Record financial transactions tying together shipment expenses, advances, maintenance records, tyre costs, payments, and office expenses.
- Track office expenses with category mapping and associated drivers where applicable.
- Execute and log detailed bank transfers including mode (IMPS/NEFT/RTGS/UPI), status transitions, and beneficiary metadata.

### 5.7 Maintenance & Fleet Compliance
- Capture maintenance records with service types, vendors, cost breakdown (rate, quantity, GST), and documents.
- Enforce tyre-selection rules when service type is tyre; reset tyre linkage when not required.
- Maintain tyre inventory with brand, model, size, purchase details, invoices, and age calculations.
- Record tyre transactions (install, replace, rotate, remove, service) tied to vehicles and track cost & technician details.

### 5.8 Document & Media Management
- Store and organize uploaded files under deterministic paths (e.g., `drivers/<driver>/documents/`, `vehicles/<reg>/documents/`).
- Support document-type metadata, issue/expiry dates, notes, and retrieval of latest documents per type.
- Enforce file validation via `document_file_validator` and accept PDF/image formats aligned with validator rules.

### 5.9 Security, Users & Access Control
- Authenticate via Django `CustomUser` supporting 2FA toggles, password expiry, account lockout, and audit fields.
- Assign roles (`Role`) with granular permissions, maintain user-role associations per tenant or per driver, and enforce with RBAC permission checks (`utils.rbac`).
- Configure approval workflows (`ApprovalWorkflow`, `ApprovalStep`, `ApprovalRequest`) for expenses, advances, and invoices, capturing step actions and comments.
- Log security events (login, lockout, permission denial) with severity classification and IP/user agent context.
- Track audit history for CRUD operations via `AuditLog`, storing before/after payloads and request metadata.
- Enforce rate limiting using `RateLimitTracker` & login attempt logging for brute-force protection.

### 5.10 API & Integration Services
- Expose RESTful endpoints for all major entities via module-specific API views (`api/v1/entity`, `api/v1/operations`, etc.) supporting search, filtering, and pagination.
- Provide summary endpoints (driver advance summary, consignment group route summary) for UI dashboards.
- Standardize API responses and exception handling with `success_response`, `error_response`, and `custom_exception_handler`.
- Generate schema/documentation through `drf-spectacular` for consumer onboarding.

### 5.11 Reporting & Insights
- Aggregate totals per consignment group, shipments, driver advances, and financial transactions for operational dashboards.
- Expose helper methods (e.g., `Vehicle.get_vehicle_summary`, `Driver.driver_advance_summary`, `Invoice.financial_summary`) for analytics screens.
- Provide monthly financial summaries and category breakdowns using `Transaction` class methods.

### 5.12 Operational Assurances
- Ensure every critical model maintains created/updated timestamps and created_by/updated_by links where applicable.
- Guard critical numeric fields with database check constraints (positive weight, non-negative amounts, valid odometer ranges).
- Auto-generate human-readable identifiers for consignment groups, consignments, shipments, invoices, and transactions using date-based prefixes.

## 6. Data & Validation Requirements
- Enforce Indian regulatory formats (PAN, GST, Aadhaar, IFSC, phone, pincode) using centralized validators in `utils.validators`.
- Maintain uniqueness constraints (vehicle registration & chassis, driver license number, maintenance invoice no.).
- Default to India as country for address mixins while allowing override.
- Ensure freight and amount fields use Decimal with appropriate precision for accounting accuracy.

## 7. Assumptions & Dependencies
- PostgreSQL is the primary database; Redis optional for rate limiting or caching if enabled.
- Static and media files served via Nginx/Whitenoise; documents stored on local or mounted volume.
- Deployment target uses Gunicorn behind Nginx as documented in the project README.
- Authentication tokens (JWT, OAuth toolkit) available via listed dependencies even if some endpoints are currently disabled.

## 8. Out of Scope / Future Enhancements
- Mobile client experiences (Android/iOS) to consume the API.
- Real-time GPS/telematics data ingestion beyond odometer snapshots.
- Automated notification dispatch (SMS/email/WhatsApp) for shipment milestones.
- Advanced analytics dashboards or BI exports beyond existing summaries.

