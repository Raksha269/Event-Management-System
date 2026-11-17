# Gather — Event Management System (EMS)

[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django%20REST%20Framework-3.15+-red.svg)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-134%20Passing-brightgreen.svg)]()
[![Security](https://img.shields.io/badge/Security-TLS%201.2%2B%20%7C%20PCI--DSS%20%7C%20RBAC-success.svg)]()

**Gather** is a full-featured, secure, and robust Event Management System designed to handle event publishing, multi-tier ticketing, high-concurrency attendee registration, mock payment processing with QR e-tickets, comprehensive financial reporting, administrator user governance, and real-time security monitoring.

---

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
3. [Implemented Feature Modules](#implemented-feature-modules)
   - [Authentication & Account Governance](#1-authentication--account-governance)
   - [Event Management Workflows (Issue #4)](#2-event-management-workflows-issue-4)
   - [Ticketing, Payments & Refunds](#3-ticketing-payments--refunds)
   - [Reporting & Analytics (Issue #8)](#4-reporting--analytics-issue-8)
   - [Security & Incident Response (Issue #10)](#5-security--incident-response-issue-10)
4. [Non-Functional Requirements & Operations](#non-functional-requirements--operations)
5. [Software Test Plan & Verification Matrix](#software-test-plan--verification-matrix)
6. [REST API Documentation](#rest-api-documentation)
7. [Getting Started & Local Development](#getting-started--local-development)

---

## Architectural Overview

Gather is built on Django 5.2 and Django REST Framework, adopting a layered architecture:

- **Presentation Layer**: Mobile-responsive Django templates (`base.html`, `organizer_dashboard.html`, `admin_user_list.html`, `admin_alerts.html`, `event_report.html`) paired with RESTful JSON endpoints.
- **Service & Domain Layer**: Dedicated service routines (`events/services.py`, `events/reports.py`, `events/security.py`) handling transactional capacity locks, payment tokenization, cryptographic validation, and velocity anomaly detection.
- **Persistence Layer**: Relational data models (`Event`, `TicketType`, `Registration`, `Payment`, `Refund`, `Ticket`, `UserProfile`, `SecurityAlert`) enforced by database constraints, transaction isolation, and row-level locking.

---

## Role-Based Access Control (RBAC)

The system defines three core roles in `accounts/roles.py`:

| Role | Permissions & Access Scope |
| :--- | :--- |
| **Attendee** | Browse published events, register for tickets, receive QR e-tickets, request refunds, manage personal profile. |
| **Organizer** | Create events (Draft), edit event details before start date, manage multi-tier ticket tiers, publish/unpublish owned events, access real-time attendee rosters and CSV export, view financial analytics. |
| **Administrator** | Access system administration portal, list and search user accounts, toggle user active/deactivated status, reassign user roles, monitor real-time security alerts and resolve incidents. |

*RBAC is strictly enforced on every route and API endpoint using `@role_required` decorators, DRF permission classes (`IsOrganizer`, `IsAdministrator`, `IsEventOwner`), returning `403 Forbidden` for unauthorized attempts.*

---

## Implemented Feature Modules

### 1. Authentication & Account Governance
- **Self-Service Registration (`EMS-F-001`)**: Account creation with email format and password strength validation.
- **Email Verification (`EMS-F-002`)**: Cryptographic URL tokens dispatched on registration; activates account upon verification.
- **Session Management (`EMS-F-003`, `EMS-F-004`)**: Secure login and logout with brute-force lockout safeguards.
- **User Administration (`EMS-F-051`, Issue #8)**:
  - Admin Web UI (`/admin-portal/users/`) and REST API (`/api/v1/admin/users/`).
  - Search by username or email, filter by role.
  - One-click account activation / deactivation (immediate session rejection for deactivated users).
  - Role promotion and reassignment (`attendee`, `organizer`, `administrator`).
  - Self-governance safety checks: Administrators cannot deactivate their own account or change their own role.

### 2. Event Management Workflows (Issue #4)
- **Draft Creation (`EMS-F-010`)**: Organizers create events with title, category, date, venue, capacity, and default ticket price. Events default to `DRAFT` status and remain hidden from attendees.
- **Event Modification (`EMS-F-011`)**: Organizers edit event metadata prior to the start date. Editing is rejected after event commencement. Non-owning organizers are blocked with `403 Forbidden`.
- **Multi-Tier Ticketing (`EMS-F-014`)**: Support for customized tiers (e.g., General Admission, VIP Pass, Early Bird) each with distinct pricing and quantity caps.
- **Event Publication (`EMS-F-012`)**: Organizers publish events to `PUBLISHED` status once details and ticket tiers are ready.
- **Event Unpublishing (`EMS-F-013`)**: Allows organizers to retract events to `UNPUBLISHED` status, immediately hiding them from public browsing.
- **Public Discovery & Search (`EMS-F-015`)**: Full-text search by title, description, venue, and filtering by category. Unpublished/Draft events are strictly excluded.
- **Overselling Prevention (`EMS-F-014`)**: Concurrency-safe registration pipeline using database row-level locking (`select_for_update`) and thread synchronization to guarantee event capacity and ticket-tier limits are never exceeded.

### 3. Ticketing, Payments & Refunds
- **Payment Processing (`EMS-F-016`)**: Mock payment gateway returning opaque UUID tokens (`transaction_id`).
- **QR Code E-Tickets (`EMS-F-017`)**: High-resolution PNG QR codes generated via Pillow/qrcode containing unique verification payloads.
- **Refunds & Cancellations (`EMS-F-020`)**: Registrations can be cancelled and refunded, updating payment status to `REFUNDED` and returning capacity back to the event pool.

### 4. Reporting & Analytics (Issue #8)
- **Attendee Roster & Live Export (`EMS-F-030`)**:
  - Live attendee roster display for owning organizers and administrators.
  - Direct CSV download (`/events/<pk>/report/attendees.csv` and `/api/v1/events/<pk>/reports/attendees.csv`) containing complete attendee registration details, ticket tiers, amounts, and timestamps matching on-screen metrics.
- **Financial & Capacity Analytics (`EMS-F-031`)**:
  - Metrics calculation including Gross Revenue, Completed Refunds, Net Revenue, Confirmed Attendees, and Remaining Capacity.
  - Per-tier breakdown tracking tickets sold, revenue per tier, and capacity fill rate.

### 5. Security & Incident Response (Issue #10)
- **TLS 1.2+ Transport Security (`EMS-SR-001`, `TC-Sec-01`)**:
  - Protocol validator (`verify_tls_version`) strictly enforcing TLS 1.2 and TLS 1.3 while rejecting legacy protocols (`SSLv2`, `SSLv3`, `TLS 1.0`, `TLS 1.1`).
  - Production security headers: `SECURE_BROWSER_XSS_FILTER = True`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = 'DENY'`, `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`.
- **Payment Data Tokenization (`EMS-SR-002`, `TC-Sec-02`)**:
  - PCI-DSS compliant storage auditing (`inspect_payment_data_storage`) verifying zero raw credit card numbers (PAN), CVVs, expiration dates, or magnetic track data exist in the database schema.
  - `Payment` model references opaque UUID tokens.
- **Modern Salted Password Hashing (`EMS-SR-003`, `TC-Sec-03`)**:
  - Django `PASSWORD_HASHERS` configured with PBKDF2 (`pbkdf2_sha256`), Argon2, and BCrypt.
  - Password algorithm prefix verification confirming salted hash storage and rejecting plaintext passwords.
- **RBAC Endpoint Authorization (`EMS-SR-004`, `TC-Sec-04`)**:
  - Uniform `403 Forbidden` responses returned for unauthorized roles or non-owners across all Web views and REST API endpoints.
- **Suspicious Activity Monitoring & Incident Response (`EMS-SR-005`, `TC-Sec-05`)**:
  - **Login Failure Burst Detection**: Alerts triggered on 3+ consecutive failed login attempts.
  - **Account Lockout**: 5 consecutive failed login attempts trigger an immediate 15-minute account lockout and generate an alert of type `ACCOUNT_LOCKOUT` with `HIGH` severity. Locked accounts are rejected even if the correct password is provided. Successful logins reset the failure counter.
  - **Abnormal Registration Velocity Detection**: Alerts triggered when registration velocity spikes (> 5 registrations in under 60 seconds on an event).
  - **Security Alerts Monitoring Panel**: Administrator dashboard (`/admin-portal/alerts/`) and REST API (`/api/v1/admin/alerts/`) with KPI cards (Total, Unresolved, High/Critical, Lockouts), severity/type filters, and resolution actions (`/api/v1/admin/alerts/<id>/resolve/`).

---

## Non-Functional Requirements & Operations

The revised NFR baseline (v1.2) evaluates this academic prototype locally. Hosted-service availability and production operations are outside this scope. Local readiness checks, reproducible search benchmarking, PostgreSQL registration-integrity verification, accessibility review, audit retention behavior, and isolated PostgreSQL backup/restore remain documented. See the [Issue #9 verification report](docs/issue-9-nfr-operations.md) for requirement IDs, implementation, test methods, evidence locations, status and limits.

| Requirement | Implementation and local verification | Status |
| :--- | :--- | :--- |
| `EMS-NF-001` Performance | Indexed event search, bounded pagination and compact paginated responses. Isolated PostgreSQL 16 with synthetic published events: 10/50/100 concurrent read-only clients; 160/160 responses succeeded; p95 0.171/0.359/0.795 s. | **Complete for the documented local benchmark scope.** p95 ≤2 s is an optimization goal; results do not establish hosted or sustained-load performance. |
| `EMS-NF-002` Availability | `/health/ready/` checks local application/database readiness; tests and PostgreSQL restore evidence verify readiness. Scheduled uptime history is tracked separately under [Issue #38](https://github.com/Raksha269/Event-Management-System/issues/38). | **Local readiness verified.** This is not continuous or monthly availability evidence. |
| `EMS-NF-003` Scalability/integrity | PostgreSQL transactions/row locks enforce capacity; a unique idempotency key prevents duplicate registration retries. Two-worker PostgreSQL tests cover last-ticket contention and concurrent retries. | **Complete for deterministic integrity checks.** No 500/10,000-registration stress result is claimed. |
| `EMS-NF-004` Usability/accessibility | Responsive template fixes, labels, error descriptions/focus, local browser/axe checks and user-supplied NVDA reports. | **Accepted for the scoped academic verification**, following the owner’s [#37 verification comment](https://github.com/Raksha269/Event-Management-System/issues/37#issuecomment-6922868953). Not a full WCAG conformance audit. |
| `EMS-NF-005` Audit/recovery | Append-only audit events, admin-only read access, 1,095-day retention boundary test and isolated PostgreSQL dump/restore rehearsal. | **Complete for the local prototype scope.** Three-year elapsed retention and automatic archiving are not claimed. |

The [local PostgreSQL report](docs/staging/report.md) and [runbook](docs/staging/README.md) capture the resource-limited benchmark, synthetic dataset and separate-database restore. Production configuration guidance below is deployment setup documentation, not an Issue #9 requirement or evidence of an actual hosted production environment. Scheduled uptime evidence remains in Issue #38; this section does not duplicate or replace it.

## Final academic-scope acceptance

The repository owner recorded team acceptance in [Issue #9](https://github.com/Raksha269/Event-Management-System/issues/9#issuecomment-6932891735) and [Issue #38](https://github.com/Raksha269/Event-Management-System/issues/38#issuecomment-6932881938). Both issues are closed against the limited academic-project scope. This records the owner's stated team decision; no separate faculty approval is inferred.

[Issue #37](https://github.com/Raksha269/Event-Management-System/issues/37#issuecomment-6922868953) records the owner's completed responsive/keyboard checks for User Administration and Security Alerts at 320, 360, 768 and 1440 px, NVDA form-error/navigation checks, and confirmation that Manage Tickets responsive and remaining contrast checks were checked. These are user-performed results. Additional numerical contrast measurements or independent retests are not invented here. This acceptance is not a full WCAG certification.

Scheduled evidence is accepted with its gaps retained as UNKNOWN. Consistent 15-minute execution, monthly availability, availability percentages and downtime durations remain unverified. Maintenance exclusions require documented approval. Historical test results and limitations below remain unchanged.

See the [freeze preparation record](docs/finalization.md) and [Sprint 2 video guide](docs/sprint-2-demo-guide.md).

### Production configuration reference

Set `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY`, and comma-separated `DJANGO_ALLOWED_HOSTS`. For PostgreSQL set `EMS_DB_ENGINE=postgresql`, `EMS_DB_NAME`, `EMS_DB_USER`, `EMS_DB_PASSWORD`, `EMS_DB_HOST`, and optionally `EMS_DB_PORT`, `EMS_DB_CONN_MAX_AGE`, and `EMS_DB_SSLMODE`. Keep any database on a private network and protect credentials. These settings are reference guidance; no production deployment, backup policy or uptime target is verified by this local prototype work.

### Local verification results

On 2026-11-15, `python manage.py check` reported no issues and the full events suite ran 112 tests: 110 passed and two SQLite concurrency cases were skipped. The separate RBAC suite passed 24/24. The isolated PostgreSQL report records the owner-run environment's 160/160 search responses, restore validation and 95 Django tests plus five script regressions. The current Windows review did not rerun that PostgreSQL container test because Podman/Docker is unavailable here. See the [Issue #9 verification report](docs/issue-9-nfr-operations.md) for exact evidence and remaining work.

---

## Software Test Plan & Verification Matrix

Automated tests map directly to the IEEE Software Test Plan:

| Test Case ID | Requirement | Description | Status |
| :--- | :--- | :--- | :---: |
| **TC-01** | `EMS-F-010` | Organizer creates event; verifies default Draft status and capacity validation | **PASS** |
| **TC-02** | `EMS-F-011` | Organizer edits event before start date; non-owners blocked with 403 Forbidden | **PASS** |
| **TC-03** | `EMS-F-012` | Owning organizer publishes event; unpublished events hidden from public search | **PASS** |
| **TC-04** | `EMS-F-013` | Organizer unpublishes event; returns to Unpublished status and hidden from search | **PASS** |
| **TC-05** | `EMS-F-014` | High-concurrency registration test (multi-threading) ensures zero overselling | **PASS** |
| **TC-06** | `EMS-F-014` | Multi-tier ticket capacity limit and "Sold Out" validation | **PASS** |
| **TC-07** | `EMS-F-015` | Public event discovery, text query, and category filters | **PASS** |
| **TC-08** | `EMS-F-030` | Attendee roster display and CSV export matching on-screen metrics | **PASS** |
| **TC-09** | `EMS-F-031` | Financial analytics reflect ticket sales and deduct refunds from net revenue | **PASS** |
| **TC-10** | `EMS-F-051` | Admin user account management: toggle active status and change user roles | **PASS** |
| **TC-Sec-01**| `EMS-SR-001` | TLS 1.2+ protocol compliance check and security transport headers | **PASS** |
| **TC-Sec-02**| `EMS-SR-002` | PCI-DSS database audit verifies zero raw PAN or CVV storage; UUID tokenization | **PASS** |
| **TC-Sec-03**| `EMS-SR-003` | Database inspection confirms modern salted password hashing; rejects plaintext | **PASS** |
| **TC-Sec-04**| `EMS-SR-004` | RBAC matrix enforcement across roles returns 403 Forbidden on unauthorized endpoints | **PASS** |
| **TC-Sec-05**| `EMS-SR-005` | 5 failed logins trigger 15m lockout, abnormal velocity alert, admin resolve API | **PASS** |
| **TC-NF-01** | `EMS-NF-001` | Reproducible read-only event-search report at 10/50/100 clients with status, latency and environment recorded | **PASS (owner-run local PostgreSQL scope; p95 goal is optimization only)** |
| **TC-NF-02** | `EMS-NF-002` | Local application/database readiness check; scheduled uptime evidence handled separately in Issue #38 | **LOCAL READINESS PASS; cadence tracked separately** |
| **TC-NF-03** | `EMS-NF-003` | PostgreSQL concurrent last-ticket capacity and idempotent retry integrity checks | **PASS for deterministic integrity; no stress-load claim** |
| **TC-NF-04** | `EMS-NF-004` | Responsive and scoped accessibility verification with documented limitations | **ACCEPTED FOR SCOPED USER VERIFICATION; no WCAG certification** |
| **TC-NF-05** | `EMS-NF-005` | Audit access/retention checks and isolated PostgreSQL backup/restore | **PASS for local scope; elapsed 3-year retention not observed** |

### Test Execution Summary
- **Main Test Suite (`events`)**: 112 discovered; 110 passed, 2 skipped on SQLite (`python manage.py test`).
- **RBAC Module (`RBAC`)**: 24/24 passed (`cd RBAC && python manage.py test`).
- **Total**: 134 passing across these two local suites, with 2 SQLite-only concurrency skips. Isolated PostgreSQL results are documented separately in `docs/staging/report.md`.

---

## REST API Documentation

### Event Endpoints
- `GET /api/v1/events/`: Search and browse published events (supports `?q=` and `?category=`).
- Collection endpoints accept optional `?limit=` and `?offset=` parameters (maximum page size 100); omitting them preserves the existing array response shape.
- `POST /api/v1/events/`: Create a new event in Draft status *(Organizer only)*.
- `GET /api/v1/events/{id}/`: Retrieve event details.
- `PUT/PATCH /api/v1/events/{id}/`: Edit event metadata before start date *(Owning Organizer only)*.
- `POST /api/v1/events/{id}/publish/`: Publish event *(Owning Organizer only)*.
- `POST /api/v1/events/{id}/unpublish/`: Unpublish event *(Owning Organizer only)*.
- `GET/POST /api/v1/events/{id}/ticket-types/`: Manage ticket tiers *(Owning Organizer only)*.
- `POST /api/v1/events/{id}/registrations/`: Register attendee for event with ticket tier.
- `GET /api/v1/events/{id}/reports/attendees.csv`: Export attendee CSV report *(Owning Organizer or Admin)*.

### Administration & User Management Endpoints
- `GET /api/v1/admin/users/`: List all users with query and role filters *(Administrator only)*.
- `GET /api/v1/admin/users/{id}/`: Retrieve user details *(Administrator only)*.
- `PATCH /api/v1/admin/users/{id}/`: Update user `is_active` status or `role` *(Administrator only)*.

### Security Monitoring & Alerts Endpoints
- `GET /api/v1/admin/alerts/`: List security alerts with `?severity=`, `?type=`, and `?is_resolved=` filters *(Administrator only)*.
- `POST /api/v1/admin/alerts/{id}/resolve/`: Mark a security alert as resolved *(Administrator only)*.
- `GET /api/v1/admin/audit-events/?limit=50&offset=0`: Read retained audit events *(Administrator only; max 100 rows per page)*.

---

## Getting Started & Local Development

### Prerequisites
- Python 3.10+ (tested on Python 3.12 and 3.14)
- SQLite3

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/rahulb/Event-Management-System.git
cd Event-Management-System

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
python manage.py migrate
```

### 3. Run Automated Tests
```bash
# Run all core event, reporting, and security tests
python manage.py test

# Run isolated RBAC unit tests
cd RBAC && python manage.py test
```

### 4. Start Local Development Server
```bash
python manage.py runserver
```
Visit `http://localhost:8000/` in your browser to access the Gather portal.

## Sprint demonstration videos and finalization

- [Sprint 1 working-product video](docs/videos/sprint-1-demo.mp4): supplied recording, 98.7 seconds. The owner accepts the supplied duration.
- Sprint 2 working-product video: supplied but awaiting a transferable copy under 32 MiB; not yet included.
- [Finalization and freeze checklist](docs/finalization.md): records the baseline, accepted scope and outstanding handoff items. No final freeze is declared by this PR.
